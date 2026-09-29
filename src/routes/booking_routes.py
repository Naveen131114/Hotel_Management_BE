from datetime import date, datetime

from flask import Blueprint, request

from src import db
from src.models.room_records import RoomRecord
from src.models.rooms import Room
from src.services import availability_service, booking_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, tenant_scope, get_current_user, current_business_id, current_branch_id,
)
from src.utils.constants import (
    ACTIVITY_CANCEL, ACTIVITY_CHECK_IN, ACTIVITY_CHECK_OUT, ACTIVITY_CREATE, ACTIVITY_DELETE,
    ACTIVITY_PAYMENT, ACTIVITY_UPDATE, BOOKING_STATUSES, MODULE_BOOKINGS, MODULE_PAYMENTS,
    SOURCE_OFFLINE,
)

bp = Blueprint('bookings', __name__, url_prefix='/api/bookings')


def _booking_or_error(id, with_relations=False):
    """Fetch a booking that belongs to the current tenant/branch scope"""
    query = tenant_scope(RoomRecord, RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)))
    booking = query.filter(RoomRecord.id == id).first()
    if not booking:
        return None, error_response('Booking not found', 404)
    return booking, None


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_bookings():
    """List bookings of the hotel/branch with the usual operational filters"""
    try:
        query = tenant_scope(RoomRecord, RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)))

        if request.args.get('booking_status'):
            query = query.filter(RoomRecord.booking_status == request.args.get('booking_status'))
        if request.args.get('booking_source'):
            query = query.filter(RoomRecord.booking_source == request.args.get('booking_source'))
        if request.args.get('room_id'):
            query = query.filter(RoomRecord.room_id == request.args.get('room_id'))
        if request.args.get('payment_status'):
            query = query.filter(RoomRecord.payment_status == request.args.get('payment_status'))
        if request.args.get('from'):
            query = query.filter(RoomRecord.check_in_date >= availability_service.parse_date(request.args.get('from'), 'from'))
        if request.args.get('to'):
            query = query.filter(RoomRecord.check_out_date <= availability_service.parse_date(request.args.get('to'), 'to'))
        if request.args.get('today_check_ins') in ('1', 'true'):
            query = query.filter(RoomRecord.check_in_date == date.today())
        if request.args.get('today_check_outs') in ('1', 'true'):
            query = query.filter(RoomRecord.check_out_date == date.today())
        if request.args.get('search'):
            term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(
                RoomRecord.booking_number.ilike(term),
                RoomRecord.guest_name.ilike(term),
                RoomRecord.guest_phone.ilike(term)
            ))

        limit = int(request.args.get('limit', 200))
        bookings = query.order_by(RoomRecord.check_in_date.desc(), RoomRecord.id.desc()).limit(limit).all()
        data = [booking.to_dict() for booking in bookings]
        return success_response('Bookings fetched successfully', data, status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/availability', methods=['GET'])
@auth_required()
@require_permission('view')
def check_availability():
    """Real-time availability for a date range (same service used by the public site)"""
    try:
        check_in = availability_service.parse_date(request.args.get('check_in'), 'Check-in date')
        check_out = availability_service.parse_date(request.args.get('check_out'), 'Check-out date')
    except ValueError as e:
        return error_response(str(e), 400)

    range_error = availability_service.validate_range(check_in, check_out)
    if range_error:
        return error_response(range_error, 400)

    user = get_current_user()
    branch_id = request.args.get('branch_id') or current_branch_id()
    if branch_id and str(branch_id).isdigit():
        branch_id = int(branch_id)
    else:
        branch_id = None

    from src.utils.auth_utils import allowed_branch_ids
    try:
        data = availability_service.availability_summary(
            current_business_id(), check_in, check_out,
            branch_id=branch_id,
            room_type_id=int(request.args['room_type_id']) if request.args.get('room_type_id') else None,
            guests=int(request.args['guests']) if request.args.get('guests') else None,
            allowed_branch_ids=allowed_branch_ids()
        )
        return success_response('Availability fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/calendar', methods=['GET'])
@auth_required()
@require_permission('view')
def booking_calendar():
    """Room grid for a date range (reception board)"""
    try:
        start = availability_service.parse_date(request.args.get('start'), 'Start date')
        end = availability_service.parse_date(request.args.get('end') or request.args.get('start'), 'End date')
    except ValueError as e:
        return error_response(str(e), 400)

    query = tenant_scope(RoomRecord, RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)))
    bookings = query.filter(
        RoomRecord.check_in_date < end,
        RoomRecord.check_out_date > start,
        RoomRecord.booking_status.in_(('pending', 'confirmed', 'checked_in')),
    ).all()
    return success_response('Calendar fetched successfully',
                            [b.to_dict() for b in bookings], status_code=200)



@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_booking(id):
    """Booking detail including payments and the current bill"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        data = booking.to_dict(include_payments=True)
        data['bill'] = booking_service.build_bill(booking)
        return success_response('Booking fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_booking():
    """Offline / phone / walk-in booking (availability is validated on the server)"""
    try:
        data = request.get_json() or {}
        user = get_current_user()

        branch_id = data.get('branch_id') or current_branch_id()
        booking, error, status = booking_service.create_booking(
            data, actor=user, source=data.get('booking_source') or SOURCE_OFFLINE,
            business_id=current_business_id(), branch_id=branch_id,
            default_status=data.get('booking_status') or 'confirmed'
        )
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CREATE, MODULE_BOOKINGS, booking.id, booking.booking_number,
                     f"Created booking {booking.booking_number} ({booking.booking_source}) for {booking.guest_name}",
                     branch_id=booking.branch_id)
        return success_response('Booking created successfully', booking.to_dict(include_payments=True),
                                status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_booking(id):
    """Update a booking (re-validates availability when room/dates change)"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        updated, error, status = booking_service.update_booking(booking, request.get_json() or {}, get_current_user())
        if error:
            return error_response(error, status)
        log_activity(ACTIVITY_UPDATE, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Updated booking {updated.booking_number}", branch_id=updated.branch_id)
        return success_response('Booking updated successfully', updated.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_booking(id):
    """Soft delete a booking so history and payments are preserved"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        booking.is_deleted = True
        if booking.booking_status in ('pending', 'confirmed', 'checked_in'):
            booking.booking_status = 'cancelled'
            booking.cancelled_at = datetime.utcnow()
            booking.cancelled_by = get_current_user().id
            booking.cancel_reason = 'Deleted from the booking list'
            if booking.room is not None and booking.room.status == 'occupied':
                booking.room.status = 'available'
        booking.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_BOOKINGS, id, booking.booking_number,
                     f"Deleted booking {booking.booking_number}", branch_id=booking.branch_id)
        return success_response('Booking deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/check-in', methods=['POST'])
@auth_required()
@require_permission('edit')
def check_in(id):
    """Check-in: verify booking/room, collect advance if given, mark room occupied"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        updated, error, status = booking_service.check_in_booking(booking, get_current_user(), request.get_json() or {})
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CHECK_IN, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Checked in guest {updated.guest_name} (room {updated.room.room_number if updated.room else '-'})",
                     branch_id=updated.branch_id)
        return success_response('Guest checked in successfully', updated.to_dict(include_payments=True), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/check-out', methods=['POST'])
@auth_required()
@require_permission('edit')
def check_out(id):
    """Check-out: build the final bill, collect the balance and release the room"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        data = request.get_json() or {}
        updated, error, status = booking_service.check_out_booking(booking, get_current_user(), data)
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CHECK_OUT, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Checked out guest {updated.guest_name} (bill #{updated.bill_number or '-'})",
                     branch_id=updated.branch_id)
        return success_response('Booking checked out successfully', updated.to_dict(include_payments=True), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/cancel', methods=['POST'])
@auth_required()
@require_permission('edit')
def cancel_booking(id):
    """Cancel a booking (cancelled bookings stop blocking availability)"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        data = request.get_json() or {}
        updated, error, status = booking_service.cancel_booking(booking, get_current_user(), data.get('reason'))
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CANCEL, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Cancelled booking {updated.booking_number}", branch_id=updated.branch_id)
        return success_response('Booking cancelled successfully', updated.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/no-show', methods=['POST'])
@auth_required()
@require_permission('edit')
def no_show(id):
    """Mark a booking as no-show"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        updated, error, status = booking_service.mark_no_show(booking, get_current_user())
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_UPDATE, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Marked booking {updated.booking_number} as no show", branch_id=updated.branch_id)
        return success_response('Booking marked as no show', updated.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/payments', methods=['POST'])
@auth_required()
@require_permission('edit')
def add_booking_payment(id):
    """Collect a payment (cash / bank + bank account / UPI + UPI account / card / other)"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        data = request.get_json() or {}

        payment, error = booking_service.add_payment(
            booking, data.get('amount'),
            method=data.get('method') or data.get('payment_method') or 'cash',
            actor=get_current_user(),
            payment_type=data.get('payment_type') or 'advance',
            bank_account_id=data.get('bank_account_id'),
            upi_account_id=data.get('upi_account_id'),
            transaction_ref=data.get('transaction_ref'),
            notes=data.get('notes')
        )
        if error:
            return error_response(error, 400)

        if data.get('method') or data.get('payment_method'):
            booking.payment_method = data.get('method') or data.get('payment_method')
            db.session.commit()

        log_activity(ACTIVITY_PAYMENT, MODULE_PAYMENTS, payment.id, booking.booking_number,
                     f"Collected {payment.amount} via {payment.method} for booking {booking.booking_number}",
                     branch_id=booking.branch_id)
        return success_response('Payment recorded successfully', {
            'payment': payment.to_dict(),
            'booking': booking.to_dict(include_payments=True)
        }, status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>/bill', methods=['GET'])
@auth_required()
@require_permission('view')
def get_bill(id):
    """Bill payload used by the thermal (58/80mm) and A4 print layouts"""
    try:
        booking, error = _booking_or_error(id)
        if error:
            return error
        return success_response('Bill fetched successfully',
                                booking_service.build_bill(booking), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)

        if error:
            return error
        updated, error, status = booking_service.check_out_booking(booking, get_current_user(), request.get_json() or {})
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CHECK_OUT, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Checked out guest {updated.guest_name} - bill {updated.bill_number}",
                     branch_id=updated.branch_id)
        payload = updated.to_dict(include_payments=True)
        payload['bill'] = booking_service.build_bill(updated)
        return success_response('Guest checked out successfully', payload, status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
