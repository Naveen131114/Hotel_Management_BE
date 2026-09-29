"""Legacy booking endpoints (/api/room-records) kept for backward compatibility.

POST now delegates to `booking_service`, so bookings created here are validated
against the same availability rules as every other channel.
New integrations should use `/api/bookings`.
"""
from flask import Blueprint, request

from src import db
from src.models.room_records import RoomRecord
from src.services import booking_service
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user, current_business_id, current_branch_id,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_BOOKINGS

bp = Blueprint('room_records', __name__, url_prefix='/api/room-records')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_room_records():
    """Get all room records of the current hotel/branch with optional filters"""
    try:
        query = tenant_scope(RoomRecord, RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)))

        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('user_id'):
            query = query.filter_by(user_id=request.args.get('user_id'))
        if request.args.get('booking_status'):
            query = query.filter_by(booking_status=request.args.get('booking_status'))
        if request.args.get('payment_status'):
            query = query.filter_by(payment_status=request.args.get('payment_status'))

        room_records = query.order_by(RoomRecord.check_in_date.desc()).all()
        return success_response('Room records fetched successfully',
                                [rr.to_dict() for rr in room_records], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_room_record(id):
    """Get room record by ID (tenant scoped)"""
    try:
        room_record = tenant_scope(RoomRecord, RoomRecord.query).filter(RoomRecord.id == id).first()
        if not room_record:
            return error_response('Room record not found', 404)
        return success_response('Room record fetched successfully',
                                room_record.to_dict(include_payments=True), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_room_record():
    """Create a booking through the shared booking service (availability enforced)"""
    try:
        data = request.get_json() or {}

        required_fields = ['room_id', 'check_in_date', 'check_out_date']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)

        booking, error, status = booking_service.create_booking(
            data, actor=get_current_user(),
            source=data.get('booking_source') or 'offline',
            business_id=current_business_id(),
            branch_id=data.get('branch_id') or current_branch_id(),
            default_status=data.get('booking_status') or 'confirmed'
        )
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CREATE, MODULE_BOOKINGS, booking.id, booking.booking_number,
                     f"Created booking {booking.booking_number}", branch_id=booking.branch_id)
        return success_response('Room record created successfully', booking.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_room_record(id):
    """Update a booking (availability re-validated by the booking service)"""
    try:
        room_record = tenant_scope(RoomRecord, RoomRecord.query).filter(RoomRecord.id == id).first()
        if not room_record:
            return error_response('Room record not found', 404)

        updated, error, status = booking_service.update_booking(
            room_record, request.get_json() or {}, get_current_user()
        )
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_UPDATE, MODULE_BOOKINGS, updated.id, updated.booking_number,
                     f"Updated booking {updated.booking_number}", branch_id=updated.branch_id)
        return success_response('Room record updated successfully', updated.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_room_record(id):
    """Soft delete a room record (booking history and payments are preserved)"""
    try:
        room_record = tenant_scope(RoomRecord, RoomRecord.query).filter(RoomRecord.id == id).first()
        if not room_record:
            return error_response('Room record not found', 404)

        if room_record.booking_status != 'cancelled':
            booking_service.cancel_booking(room_record, get_current_user(),
                                           'Deleted from the legacy booking list')
        room_record.is_deleted = True
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_BOOKINGS, id, room_record.booking_number,
                     f"Deleted booking {room_record.booking_number}", branch_id=room_record.branch_id)
        return success_response('Room record deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)

