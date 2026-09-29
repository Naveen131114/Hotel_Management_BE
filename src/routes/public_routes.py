from datetime import date, datetime

from flask import Blueprint, request

from src import db
from src.models.businesses import Business
from src.models.branches import Branch
from src.models.rooms import Room
from src.models.users import User
from src.models.business_subscriptions import BusinessSubscription
from src.services import availability_service, booking_service
from src.utils import success_response, error_response
from src.utils.constants import (
    ROLE_OWNER, SOURCE_ONLINE, SUBSCRIPTION_ACTIVE,
)

bp = Blueprint('public', __name__, url_prefix='/api/public')


def _active_business(slug):
    """Resolve a hotel by slug (public data only, inactive hotels are hidden)"""
    business = Business.query.filter(Business.slug == slug.lower()).first()
    if not business or not business.is_active:
        return None, error_response('Hotel not found', 404)
    return business, None


@bp.route('/hotels', methods=['GET'])
def list_hotels():
    """Directory of hotels available for online booking"""
    try:
        query = Business.query.filter(Business.is_active.is_(True))
        if request.args.get('city'):
            query = query.filter(Business.city.ilike(f"%{request.args.get('city')}%"))
        if request.args.get('search'):
            term = f"%{request.args.get('search')}%"
            query = query.filter(db.or_(Business.name.ilike(term), Business.city.ilike(term)))
        businesses = query.order_by(Business.name.asc()).all()

        data = []
        for business in businesses:
            payload = business.public_dict()
            if business.tax_percent is not None:
                payload['tax_percent'] = float(business.tax_percent)
            payload['branches'] = [
                {'id': branch.id, 'name': branch.name, 'city': branch.city}
                for branch in Branch.query.filter_by(business_id=business.id, is_active=True).all()
            ]
            data.append(payload)
        return success_response('Hotels fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/hotels/<slug>', methods=['GET'])
def hotel_details(slug):
    """Public hotel page: details, branches, room types and facilities"""
    try:
        business, error = _active_business(slug)
        if error:
            return error

        from src.models.room_types import RoomType
        from src.models.accessories import Accessory

        branches = Branch.query.filter_by(business_id=business.id, is_active=True).all()
        room_types = RoomType.query.filter_by(business_id=business.id, is_active=True).all()
        rooms = Room.query.filter(
            Room.business_id == business.id,
            Room.is_online_bookable.is_(True),
            ~Room.status.in_(('maintenance', 'blocked'))
        ).all()

        data = business.public_dict()
        data.update({
            'branches': [branch.to_dict() for branch in branches],
            'room_types': [{
                **room_type.to_dict(),
                'available_rooms': len([room for room in rooms if room.room_type_id == room_type.id])
            } for room_type in room_types],
            'facilities': [accessory.name for accessory in
                           Accessory.query.filter_by(business_id=business.id).limit(30).all()],
            'online_rooms': len(rooms),
            'from_price': min([float(room.base_price or 0) for room in rooms if room.base_price] or [0])
        })
        return success_response('Hotel fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/hotels/<slug>/availability', methods=['GET'])
def hotel_availability(slug):
    """Real-time availability for the public search form (same rules as the panel)"""
    try:
        business, error = _active_business(slug)
        if error:
            return error

        try:
            check_in = availability_service.parse_date(request.args.get('check_in'), 'Check-in date')
            check_out = availability_service.parse_date(request.args.get('check_out'), 'Check-out date')
        except ValueError as exc:
            return error_response(str(exc), 400)

        range_error = availability_service.validate_range(check_in, check_out)
        if range_error:
            return error_response(range_error, 400)
        if check_in < date.today():
            return error_response('Check-in date cannot be in the past', 400)

        data = availability_service.availability_summary(
            business.id, check_in, check_out,
            branch_id=int(request.args['branch_id']) if request.args.get('branch_id') else None,
            room_type_id=int(request.args['room_type_id']) if request.args.get('room_type_id') else None,
            guests=int(request.args['guests']) if request.args.get('guests') else None,
            online_only=True
        )
        data['hotel'] = business.public_dict()
        return success_response('Availability fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/hotels/<slug>/bookings', methods=['POST'])
def create_online_booking(slug):
    """Public (online) booking - availability is enforced by the shared service"""
    try:
        business, error = _active_business(slug)
        if error:
            return error

        from src.services import subscription_service
        if subscription_service.subscription_status(business.id)[0] != SUBSCRIPTION_ACTIVE:
            return error_response('Online booking is temporarily unavailable for this hotel. Please contact the hotel directly.', 403)

        data = request.get_json() or {}
        required = ['room_id', 'check_in_date', 'check_out_date', 'guest_name', 'guest_phone']
        if not all(data.get(field) for field in required):
            return error_response('Room, dates, guest name and phone number are required', 400)

        try:
            check_in = availability_service.parse_date(data['check_in_date'], 'Check-in date')
        except ValueError as exc:
            return error_response(str(exc), 400)
        if check_in < date.today():
            return error_response('Check-in date cannot be in the past', 400)

        booking, error, status = booking_service.create_booking(
            data, actor=None, source=SOURCE_ONLINE,
            business_id=business.id, branch_id=None,
            default_status='pending', online_only=True
        )
        if error:
            return error_response(error, status)

        return success_response('Booking confirmed successfully', {
            'booking_number': booking.booking_number,
            'customer_name': booking.guest_name,
            'room_number': booking.room.room_number if booking.room else None,
            'room_type': booking.room.room_type.name if booking.room and booking.room.room_type else None,
            'branch_name': booking.branch.name if booking.branch else None,
            'hotel_name': business.name,
            'check_in_date': booking.check_in_date.isoformat(),
            'check_out_date': booking.check_out_date.isoformat(),
            'nights': booking.nights(),
            'adults': booking.adults,
            'children': booking.children,
            'total_amount': float(booking.total_amount or 0),
            'advance_amount': float(booking.advance_amount or 0),
            'balance_amount': float(booking.balance_amount or 0),
            'booking_status': booking.booking_status,
            'booking_source': booking.booking_source,
            'contact_phone': business.phone,
            'message': 'Your booking request has been received. The hotel will confirm it shortly.'
        }, status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/hotels/<slug>/bookings/<booking_number>', methods=['GET'])
def booking_status(slug, booking_number):
    """Booking lookup for a guest (booking number + registered phone number)"""
    try:
        business, error = _active_business(slug)
        if error:
            return error

        from src.models.room_records import RoomRecord
        phone = request.args.get('phone')
        query = RoomRecord.query.filter_by(business_id=business.id, booking_number=booking_number, is_deleted=False)
        booking = query.first()
        if booking is None:
            return error_response('Booking not found', 404)
        if phone and (booking.guest_phone or '')[-10:] != phone[-10:]:
            return error_response('The phone number does not match this booking', 403)

        return success_response('Booking fetched successfully', {
            'booking_number': booking.booking_number,
            'customer_name': booking.guest_name,
            'room_number': booking.room.room_number if booking.room else None,
            'check_in_date': booking.check_in_date.isoformat(),
            'check_out_date': booking.check_out_date.isoformat(),
            'booking_status': booking.booking_status,
            'payment_status': booking.payment_status,
            'total_amount': float(booking.total_amount or 0),
            'balance_amount': float(booking.balance_amount or 0)
        }, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)

@bp.route('/register-hotel', methods=['POST'])
def register_hotel():
    """Hotel/lodge self-onboarding: creates the tenant, its first branch, the
    owner login and a pending subscription request (approved by the super admin)."""
    try:
        from src.models.subscription_plans import SubscriptionPlan
        from src.services import subscription_service
        from src.utils.constants import ROLE_OWNER, PERMISSION_FULL

        data = request.get_json() or {}
        required = ['business_name', 'slug', 'email', 'password']
        if not all(data.get(field) for field in required):
            return error_response('Business name, slug, email and password are required', 400)
        if len(str(data.get('password'))) < 6:
            return error_response('Password must be at least 6 characters', 400)

        slug = str(data['slug']).strip().lower().replace(' ', '-')
        if Business.query.filter_by(slug=slug).first():
            return error_response('This booking website link is already taken', 400)
        if User.query.filter_by(email=data['email']).first():
            return error_response('This email is already registered', 400)

        business = Business(
            name=data['business_name'],
            slug=slug,
            owner_name=data.get('owner_name'),
            email=data['email'],
            phone=data.get('phone'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            gst_number=data.get('gst_number'),
            is_active=True
        )
        db.session.add(business)
        db.session.flush()

        branch = Branch(
            business_id=business.id,
            name=data.get('branch_name') or 'Main Branch',
            city=data.get('city'),
            phone=data.get('phone'),
            address=data.get('address'),
            is_active=True
        )
        db.session.add(branch)
        db.session.flush()

        owner = User(
            first_name=data.get('owner_first_name') or 'Owner',
            last_name=data.get('owner_last_name') or business.name,
            email=data['email'],
            phone=data.get('phone'),
            business_id=business.id,
            branch_id=branch.id,
            role=ROLE_OWNER,
            permission_level=PERMISSION_FULL,
            is_active=True
        )
        owner.set_password(data['password'])
        db.session.add(owner)
        db.session.commit()

        request_note = None
        if data.get('plan_id'):
            plan = db.session.get(SubscriptionPlan, int(data['plan_id']))
            if plan and plan.is_active:
                subscription_service.create_request(
                    business.id, plan.id, requested_by=owner,
                    notes='Subscription requested during hotel registration'
                )
                request_note = f"Subscription plan {plan.name} requested. Awaiting approval."

        return success_response('Registration successful', {
            'business': business.to_dict(),
            'branch': branch.to_dict(),
            'owner_email': owner.email,
            'booking_website': f"/book/{business.slug}",
            'subscription_request': request_note
        }, status_code=201)
    except (TypeError, ValueError):
        return error_response('plan_id must be a number', 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)

