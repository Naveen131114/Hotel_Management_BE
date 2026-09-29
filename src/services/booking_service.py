"""Booking business logic shared by every channel (walk-in, phone, offline, online).

`create_booking()` re-checks availability on the server (with a room row lock)
immediately before insert, so the frontend check is never trusted and two
simultaneous requests cannot book the same room for overlapping dates.
"""
import re
from datetime import datetime, date
from uuid import uuid4

from src import db
from src.models.rooms import Room
from src.models.room_records import RoomRecord
from src.models.users import User
from src.models.payments import Payment
from src.models.businesses import Business
from src.services import availability_service
from src.utils.constants import (
    BOOKING_CHECKED_IN, BOOKING_CHECKED_OUT, BOOKING_CANCELLED, BOOKING_CONFIRMED,
    BOOKING_PENDING, BOOKING_NO_SHOW, BOOKING_STATUSES, PAYMENT_STATUS_PAID,
    PAYMENT_STATUS_PARTIAL, PAYMENT_STATUS_PENDING, PAYMENT_STATUS_REFUNDED,
    PAYMENT_TYPE_ADVANCE, PAYMENT_TYPE_FINAL, PAYMENT_METHODS, ROOM_AVAILABLE,
    ROOM_OCCUPIED, ROLE_GUEST, SOURCE_ONLINE,
)


def _now():
    return datetime.utcnow()


def _name_of(user):
    if user is None:
        return 'System'
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def find_or_create_guest(business_id, name, phone=None, email=None):
    """Resolve a guest account for walk-in / phone / online bookings"""
    phone_digits = re.sub(r'\D', '', phone or '')
    guest = None
    if phone_digits:
        guest = User.query.filter(User.phone == phone).first() if phone else None
        if guest is None:
            guest = User.query.filter(User.business_id == business_id, User.phone == phone).first()
    if guest is None and email:
        guest = User.query.filter_by(email=email).first()

    if guest is not None:
        # Refresh contact details on the existing guest record
        if phone and not guest.phone:
            guest.phone = phone
        return guest

    parts = (name or 'Walk-in Guest').split()
    email_value = email or (
        f"{phone_digits}@guest.local" if phone_digits else f"guest-{uuid4().hex[:8]}@guest.local"
    )
    if User.query.filter_by(email=email_value).first():
        email_value = f"guest-{uuid4().hex[:8]}@guest.local"

    guest = User(
        first_name=parts[0] if parts else 'Walk-in',
        last_name=' '.join(parts[1:]) if len(parts) > 1 else 'Guest',
        email=email_value,
        phone=phone,
        business_id=business_id,
        role=ROLE_GUEST,
        is_active=True
    )
    db.session.add(guest)
    db.session.flush()
    return guest


def calculate_charges(room, check_in, check_out, extra_charges=0, discount_amount=0,
                      tax_percent=None, business=None):
    """Room charges + additional charges - discount + tax -> grand total"""
    nights = availability_service.nights_between(check_in, check_out)
    rate = _to_float(room.base_price)
    if not rate and room.room_type is not None:
        rate = _to_float(room.room_type.base_price)
    if tax_percent is None:
        tax_percent = _to_float(business.tax_percent) if business else 0.0

    room_charges = round(rate * nights, 2)
    extra_charges = round(_to_float(extra_charges), 2)
    discount_amount = round(_to_float(discount_amount), 2)
    subtotal = round(room_charges + extra_charges, 2)
    taxable = max(round(subtotal - discount_amount, 2), 0.0)
    tax_amount = round(taxable * _to_float(tax_percent) / 100.0, 2)
    total_amount = round(taxable + tax_amount, 2)

    return {
        'rate': rate,
        'nights': nights,
        'room_charges': room_charges,
        'extra_charges': extra_charges,
        'discount_amount': discount_amount,
        'subtotal': subtotal,
        'tax_percent': round(_to_float(tax_percent), 2),
        'tax_amount': tax_amount,
        'total_amount': total_amount
    }



def sync_payment_state(booking, commit=True):
    """Recompute received/advance/balance amounts and the payment status"""
    received = 0.0
    advance = 0.0
    for payment in booking.payments:
        if payment.status != 'completed':
            continue
        amount = _to_float(payment.amount)
        if payment.payment_type == 'refund':
            received -= amount
        else:
            received += amount
            if payment.payment_type == PAYMENT_TYPE_ADVANCE:
                advance += amount

    total = _to_float(booking.total_amount or booking.total_price)
    booking.received_amount = round(received, 2)
    booking.advance_amount = round(advance, 2)
    booking.amount_paid = round(received, 2)          # legacy field kept in sync
    booking.balance_amount = round(total - received, 2)
    if received <= 0:
        booking.payment_status = PAYMENT_STATUS_PENDING
    elif booking.balance_amount > 0.01:
        booking.payment_status = PAYMENT_STATUS_PARTIAL
    else:
        booking.payment_status = PAYMENT_STATUS_PAID
    if commit:
        db.session.commit()
    return booking


def add_payment(booking, amount, method='cash', actor=None, payment_type=PAYMENT_TYPE_ADVANCE,
                bank_account_id=None, upi_account_id=None, transaction_ref=None, notes=None,
                commit=True):
    """Record a payment against a booking (bank/UPI account selectable)"""
    amount = round(_to_float(amount), 2)
    if amount <= 0:
        return None, 'Payment amount must be greater than zero'
    if method and method not in PAYMENT_METHODS:
        return None, f'Unsupported payment method: {method}'

    payment = Payment(
        room_record_id=booking.id,
        amount=amount,
        method=method or 'cash',
        status='completed',
        transaction_ref=transaction_ref,
        notes=notes,
        business_id=booking.business_id,
        branch_id=booking.branch_id,
        bank_account_id=bank_account_id,
        upi_account_id=upi_account_id,
        payment_type=payment_type or PAYMENT_TYPE_ADVANCE,
        received_by=actor.id if actor else None,
        received_by_name=_name_of(actor) if actor else None
    )
    db.session.add(payment)
    db.session.flush()
    sync_payment_state(booking, commit=False)
    if commit:
        db.session.commit()
    return payment, None


def build_bill(booking):
    """Bill payload shared by the thermal (58/80mm) and A4 print layouts"""
    business = booking.business
    branch = booking.branch
    room = booking.room
    payments = [payment for payment in booking.payments if payment.status == 'completed']

    return {
        'bill_number': booking.bill_number or booking.booking_number,
        'booking_number': booking.booking_number,
        'booking_source': booking.booking_source,
        'booking_status': booking.booking_status,
        'business': {
            'name': business.name if business else None,
            'address': business.address if business else None,
            'city': business.city if business else None,
            'phone': business.phone if business else None,
            'email': business.email if business else None,
            'gst_number': business.gst_number if business else None,
            'logo_url': business.logo_url if business else None,
            'tax_percent': _to_float(business.tax_percent) if business else 0.0
        },
        'branch': {
            'id': branch.id if branch else None,
            'name': branch.name if branch else None,
            'address': branch.address if branch else None,
            'phone': branch.phone if branch else None,
            'gst_number': branch.gst_number if branch else None
        },
        'guest': {
            'name': booking.guest_name,
            'phone': booking.guest_phone,
            'email': booking.guest_email
        },
        'stay': {
            'check_in_date': booking.check_in_date.isoformat() if booking.check_in_date else None,
            'check_out_date': booking.check_out_date.isoformat() if booking.check_out_date else None,
            'actual_check_in': booking.actual_check_in.isoformat() if booking.actual_check_in else None,
            'actual_check_out': booking.actual_check_out.isoformat() if booking.actual_check_out else None,
            'nights': booking.nights(),
            'adults': booking.adults,
            'children': booking.children
        },
        'room': {
            'room_number': room.room_number if room else None,
            'room_type_name': room.room_type.name if room and room.room_type else None,
            'floor': room.floor if room else None
        },
        'charges': {
            'room_charges': _to_float(booking.room_charges),
            'extra_charges': _to_float(booking.extra_charges),
            'discount_amount': _to_float(booking.discount_amount),
            'tax_percent': _to_float(booking.tax_percent),
            'tax_amount': _to_float(booking.tax_amount),
            'total_amount': _to_float(booking.total_amount or booking.total_price)
        },
        'payment': {
            'advance_amount': _to_float(booking.advance_amount),
            'received_amount': _to_float(booking.received_amount or booking.amount_paid),
            'balance_amount': _to_float(booking.balance_amount),
            'payment_status': booking.payment_status,
            'payment_method': booking.payment_method,
            'payments': [payment.to_dict() for payment in payments]
        },
        'generated_at': _now().isoformat()
    }


def create_booking(payload, actor=None, source=SOURCE_ONLINE, business_id=None, branch_id=None,
                   default_status=BOOKING_CONFIRMED, online_only=False):
    """Create a booking for any channel. Returns (booking, error, status_code)"""
    payload = payload or {}
    try:
        check_in = availability_service.parse_date(payload.get('check_in_date'), 'Check-in date')
        check_out = availability_service.parse_date(payload.get('check_out_date'), 'Check-out date')
    except ValueError as exc:
        return None, str(exc), 400

    range_error = availability_service.validate_range(check_in, check_out)
    if range_error:
        return None, range_error, 400

    if not payload.get('room_id'):
        return None, 'room_id is required', 400
    room = db.session.get(Room, int(payload['room_id']))
    if room is None:
        return None, 'Room not found', 404
    if business_id is not None and room.business_id != int(business_id):
        return None, 'Room does not belong to this hotel', 403
    if branch_id is not None and room.branch_id != int(branch_id):
        return None, 'Room does not belong to the selected branch', 403
    if online_only and not room.is_online_bookable:
        return None, 'This room is not open for online booking', 400

    adults = int(payload.get('adults') or payload.get('num_guests') or 1)
    children = int(payload.get('children') or 0)
    num_guests = adults + children
    if room.capacity and num_guests > room.capacity:
        return None, f'Room {room.room_number} allows a maximum of {room.capacity} guests', 400

    booking_status = payload.get('booking_status') or default_status
    if booking_status not in BOOKING_STATUSES:
        return None, 'Invalid booking status', 400

    try:
        # Server-side availability check with a room row lock -> no double booking
        available, reason, _conflict = availability_service.is_room_available(
            room, check_in, check_out, lock_room=True
        )
        if not available:
            return None, reason, 409

        business = db.session.get(Business, room.business_id)
        charges = calculate_charges(
            room, check_in, check_out,
            extra_charges=payload.get('extra_charges'),
            discount_amount=payload.get('discount_amount'),
            tax_percent=payload.get('tax_percent'),
            business=business
        )

        guest_name = (payload.get('guest_name') or '').strip()
        guest_phone = (payload.get('guest_phone') or '').strip() or None
        guest_email = (payload.get('guest_email') or '').strip() or None

        guest = None
        if payload.get('user_id'):
            guest = db.session.get(User, int(payload['user_id']))
            if guest is None:
                return None, 'Guest not found', 404
            if guest.business_id not in (None, room.business_id):
                return None, 'Guest does not belong to this hotel', 403
        if guest is None:
            if not guest_name:
                return None, 'Guest name is required', 400
            if not guest_phone and not guest_email:
                return None, 'Guest phone or email is required', 400
            guest = find_or_create_guest(room.business_id, guest_name, guest_phone, guest_email)

        booking = RoomRecord(
            room_id=room.id,
            user_id=guest.id,
            business_id=room.business_id,
            branch_id=room.branch_id,
            room_type_id=room.room_type_id,
            booking_source=source,
            guest_name=guest_name or f"{guest.first_name} {guest.last_name}".strip(),
            guest_phone=guest_phone or guest.phone,
            guest_email=guest_email or guest.email,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=adults,
            children=children,
            num_guests=num_guests,
            room_charges=charges['room_charges'],
            extra_charges=charges['extra_charges'],
            discount_amount=charges['discount_amount'],
            tax_percent=charges['tax_percent'],
            tax_amount=charges['tax_amount'],
            total_price=charges['total_amount'],
            total_amount=charges['total_amount'],
            payment_method=payload.get('payment_method'),
            special_requests=payload.get('notes') or payload.get('special_requests'),
            booking_status=booking_status,
            payment_status=PAYMENT_STATUS_PENDING,
            created_by=actor.id if actor else None,
            created_by_name=_name_of(actor) if actor else None
        )
        db.session.add(booking)
        db.session.flush()

        stamp = (booking.created_at or _now()).strftime('%Y%m%d')
        booking.booking_number = f"BK-{stamp}-{booking.id:05d}"

        advance = _to_float(payload.get('advance_amount'))
        if advance > 0:
            _payment, payment_error = add_payment(
                booking, advance,
                method=payload.get('payment_method') or 'cash',
                actor=actor, payment_type=PAYMENT_TYPE_ADVANCE,
                bank_account_id=payload.get('bank_account_id'),
                upi_account_id=payload.get('upi_account_id'),
                transaction_ref=payload.get('transaction_ref'),
                commit=False
            )
            if payment_error:
                db.session.rollback()
                return None, payment_error, 400
        else:
            sync_payment_state(booking, commit=False)

        db.session.commit()
        return booking, None, 201
    except Exception as exc:  # pragma: no cover - defensive
        db.session.rollback()
        return None, f'Error creating booking: {str(exc)}', 500


def update_booking(booking, payload, actor=None):
    """Update an admin booking, re-validating availability when room/dates change"""
    payload = payload or {}
    try:
        new_room_id = int(payload.get('room_id') or booking.room_id)
        check_in = availability_service.parse_date(payload.get('check_in_date') or booking.check_in_date, 'Check-in date')
        check_out = availability_service.parse_date(payload.get('check_out_date') or booking.check_out_date, 'Check-out date')
    except (ValueError, TypeError) as exc:
        return None, str(exc), 400

    range_error = availability_service.validate_range(check_in, check_out)
    if range_error:
        return None, range_error, 400

    room = db.session.get(Room, new_room_id)
    if room is None or room.business_id != booking.business_id:
        return None, 'Room not found for this hotel', 404

    room_changed = room.id != booking.room_id
    dates_changed = check_in != booking.check_in_date or check_out != booking.check_out_date
    if (room_changed or dates_changed) and booking.booking_status != BOOKING_CANCELLED:
        available, reason, _conflict = availability_service.is_room_available(
            room, check_in, check_out, exclude_booking_id=booking.id, lock_room=True
        )
        if not available:
            return None, reason, 409

    adults = int(payload.get('adults') if payload.get('adults') is not None else (booking.adults or 1))
    children = int(payload.get('children') if payload.get('children') is not None else (booking.children or 0))
    if room.capacity and (adults + children) > room.capacity:
        return None, f'Room {room.room_number} allows a maximum of {room.capacity} guests', 400

    charges = calculate_charges(
        room, check_in, check_out,
        extra_charges=payload.get('extra_charges', booking.extra_charges),
        discount_amount=payload.get('discount_amount', booking.discount_amount),
        tax_percent=payload.get('tax_percent', booking.tax_percent),
        business=booking.business
    )

    booking.room_id = room.id
    booking.room_type_id = room.room_type_id
    booking.branch_id = room.branch_id
    booking.check_in_date = check_in
    booking.check_out_date = check_out
    booking.adults = adults
    booking.children = children
    booking.num_guests = adults + children
    booking.room_charges = charges['room_charges']
    booking.extra_charges = charges['extra_charges']
    booking.discount_amount = charges['discount_amount']
    booking.tax_percent = charges['tax_percent']
    booking.tax_amount = charges['tax_amount']
    booking.total_amount = charges['total_amount']
    booking.total_price = charges['total_amount']

    if payload.get('guest_name'):
        booking.guest_name = payload['guest_name']
    if payload.get('guest_phone'):
        booking.guest_phone = payload['guest_phone']
    if payload.get('guest_email'):
        booking.guest_email = payload['guest_email']
    if payload.get('payment_method'):
        booking.payment_method = payload['payment_method']
    if payload.get('notes') is not None or payload.get('special_requests') is not None:
        booking.special_requests = payload.get('notes') or payload.get('special_requests')
    if payload.get('booking_status'):
        if payload['booking_status'] not in BOOKING_STATUSES:
            return None, 'Invalid booking status', 400
        booking.booking_status = payload['booking_status']

    sync_payment_state(booking, commit=False)
    db.session.commit()
    return booking, None, 200

def check_in_booking(booking, actor=None, payload=None):
    """Check-in: verify -> (optional) collect advance -> room becomes occupied"""
    payload = payload or {}
    if booking.is_deleted:
        return None, 'Booking not found', 404
    if booking.booking_status in (BOOKING_CHECKED_IN, BOOKING_CHECKED_OUT):
        return None, f'Booking is already {booking.booking_status}', 400
    if booking.booking_status not in (BOOKING_PENDING, BOOKING_CONFIRMED):
        return None, f'Cannot check in a booking with status {booking.booking_status}', 400

    if _to_float(payload.get('amount')) > 0:
        _payment, payment_error = add_payment(
            booking, payload.get('amount'),
            method=payload.get('payment_method') or 'cash',
            actor=actor, payment_type=PAYMENT_TYPE_ADVANCE,
            bank_account_id=payload.get('bank_account_id'),
            upi_account_id=payload.get('upi_account_id'),
            transaction_ref=payload.get('transaction_ref'),
            commit=False
        )
        if payment_error:
            db.session.rollback()
            return None, payment_error, 400

    booking.actual_check_in = _now()
    booking.booking_status = BOOKING_CHECKED_IN
    booking.checked_in_by = actor.id if actor else None
    booking.checked_in_by_name = _name_of(actor) if actor else None
    if booking.room is not None:
        booking.room.status = ROOM_OCCUPIED
    sync_payment_state(booking, commit=False)
    db.session.commit()
    return booking, None, 200


def check_out_booking(booking, actor=None, payload=None):
    """Check-out: final bill (charges + extra - discount + tax - payments) -> room free"""
    payload = payload or {}
    if booking.booking_status != BOOKING_CHECKED_IN:
        return None, 'Only checked-in bookings can be checked out', 400

    room = booking.room
    charges = calculate_charges(
        room, booking.check_in_date, booking.check_out_date,
        extra_charges=payload.get('extra_charges', booking.extra_charges),
        discount_amount=payload.get('discount_amount', booking.discount_amount),
        tax_percent=payload.get('tax_percent', booking.tax_percent),
        business=booking.business
    )
    booking.room_charges = charges['room_charges']
    booking.extra_charges = charges['extra_charges']
    booking.discount_amount = charges['discount_amount']
    booking.tax_percent = charges['tax_percent']
    booking.tax_amount = charges['tax_amount']
    booking.total_amount = charges['total_amount']
    booking.total_price = charges['total_amount']

    if _to_float(payload.get('amount')) > 0:
        _payment, payment_error = add_payment(
            booking, payload.get('amount'),
            method=payload.get('payment_method') or 'cash',
            actor=actor, payment_type=PAYMENT_TYPE_FINAL,
            bank_account_id=payload.get('bank_account_id'),
            upi_account_id=payload.get('upi_account_id'),
            transaction_ref=payload.get('transaction_ref'),
            commit=False
        )
        if payment_error:
            db.session.rollback()
            return None, payment_error, 400

    booking.actual_check_out = _now()
    booking.booking_status = BOOKING_CHECKED_OUT
    booking.bill_number = f"BILL-{booking.booking_number}" if booking.booking_number else None
    booking.checked_out_by = actor.id if actor else None
    booking.checked_out_by_name = _name_of(actor) if actor else None
    if room is not None:
        room.status = ROOM_AVAILABLE
    sync_payment_state(booking, commit=False)
    db.session.commit()
    return booking, None, 200


def cancel_booking(booking, actor=None, reason=None):
    """Cancel a booking - cancelled bookings no longer block availability"""
    if booking.booking_status == BOOKING_CHECKED_OUT:
        return None, 'A checked-out booking cannot be cancelled', 400
    if booking.booking_status == BOOKING_CANCELLED:
        return None, 'Booking is already cancelled', 400

    booking.booking_status = BOOKING_CANCELLED
    booking.cancelled_at = _now()
    booking.cancelled_by = actor.id if actor else None
    booking.cancel_reason = reason
    if booking.room is not None and booking.room.status == ROOM_OCCUPIED:
        booking.room.status = ROOM_AVAILABLE
    db.session.commit()
    return booking, None, 200


def mark_no_show(booking, actor=None):
    """Mark a no-show booking (kept for reporting; blocks no availability)"""
    if booking.booking_status in (BOOKING_CHECKED_IN, BOOKING_CHECKED_OUT, BOOKING_CANCELLED):
        return None, f'Cannot mark a {booking.booking_status} booking as no show', 400
    booking.booking_status = BOOKING_NO_SHOW
    db.session.commit()
    return booking, None, 200

