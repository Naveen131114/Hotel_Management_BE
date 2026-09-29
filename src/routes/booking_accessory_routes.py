from flask import Blueprint, request

from src import db
from src.models.booking_accessories import BookingAccessory
from src.models.room_records import RoomRecord
from src.models.accessories import Accessory
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE

bp = Blueprint('booking_accessories', __name__, url_prefix='/api/booking-accessories')


def _scoped(query):
    """Add-on records inherit the tenant scope through their booking"""
    return query.filter(BookingAccessory.room_record_id.in_(
        tenant_scope(RoomRecord, RoomRecord.query).with_entities(RoomRecord.id)
    ))


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_booking_accessories():
    """Get accessories added to bookings of the current hotel"""
    try:
        query = _scoped(BookingAccessory.query)
        if request.args.get('room_record_id'):
            query = query.filter_by(room_record_id=request.args.get('room_record_id'))
        items = query.all()
        return success_response('Booking accessories fetched successfully',
                                [item.to_dict() for item in items], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_booking_accessory(id):
    """Get a booking-accessory record by ID (tenant scoped)"""
    try:
        item = _scoped(BookingAccessory.query).filter(BookingAccessory.id == id).first()
        if not item:
            return error_response('Booking accessory not found', 404)
        return success_response('Booking accessory fetched successfully', item.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_booking_accessory():
    """Add an accessory to a booking; chargeable items update the bill total"""
    try:
        data = request.get_json()
        if not data.get('room_record_id') or not data.get('accessory_id'):
            return error_response('room_record_id and accessory_id are required', 400)

        booking = tenant_scope(RoomRecord, RoomRecord.query).filter(
            RoomRecord.id == data['room_record_id']
        ).first()
        if not booking:
            return error_response('Booking not found', 404)

        accessory = Accessory.query.filter_by(id=data['accessory_id'], business_id=booking.business_id).first()
        if accessory is None:
            return error_response('Accessory not found for this hotel', 404)

        quantity = int(data.get('quantity') or 1)
        item = BookingAccessory(
            room_record_id=booking.id,
            accessory_id=accessory.id,
            quantity=quantity,
            price_at_booking=data.get('price_at_booking', accessory.unit_price)
        )
        db.session.add(item)

        if accessory.is_chargeable:
            from src.services import booking_service
            extra = float(item.price_at_booking or 0) * quantity
            booking.extra_charges = float(booking.extra_charges or 0) + extra
            charges = booking_service.calculate_charges(
                booking.room, booking.check_in_date, booking.check_out_date,
                extra_charges=booking.extra_charges,
                discount_amount=booking.discount_amount,
                tax_percent=booking.tax_percent,
                business=booking.business
            )
            booking.room_charges = charges['room_charges']
            booking.tax_amount = charges['tax_amount']
            booking.total_amount = charges['total_amount']
            booking.total_price = charges['total_amount']


            booking_service.sync_payment_state(booking, commit=False)

        db.session.commit()

        log_activity(ACTIVITY_CREATE, 'booking_accessories', item.id, booking.booking_number,
                     f"Added accessory {accessory.name} to booking {booking.booking_number}",
                     branch_id=booking.branch_id)
        return success_response('Booking accessory created successfully', item.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_booking_accessory(id):
    """Update a booking-accessory record"""
    try:
        item = _scoped(BookingAccessory.query).filter(BookingAccessory.id == id).first()
        if not item:
            return error_response('Booking accessory not found', 404)

        data = request.get_json()
        for field in ('quantity', 'price_at_booking'):
            if field in data:
                setattr(item, field, data[field])
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, 'booking_accessories', item.id, None,
                     f"Updated booking accessory #{item.id}")
        return success_response('Booking accessory updated successfully', item.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_booking_accessory(id):
    """Remove an accessory from a booking"""
    try:
        item = _scoped(BookingAccessory.query).filter(BookingAccessory.id == id).first()
        if not item:
            return error_response('Booking accessory not found', 404)

        db.session.delete(item)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, 'booking_accessories', id, None, f"Removed booking accessory #{id}")
        return success_response('Booking accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
