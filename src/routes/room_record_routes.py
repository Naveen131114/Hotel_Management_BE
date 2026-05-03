from flask import Blueprint, request
from src import db
from src.models.room_records import RoomRecord
from src.utils import success_response, error_response, token_required

bp = Blueprint('room_records', __name__, url_prefix='/api/room-records')


@bp.route('', methods=['GET'])
def get_all_room_records():
    """Get all room records with optional filters"""
    try:
        query = RoomRecord.query
        
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('user_id'):
            query = query.filter_by(user_id=request.args.get('user_id'))
        if request.args.get('booking_status'):
            query = query.filter_by(booking_status=request.args.get('booking_status'))
        if request.args.get('payment_status'):
            query = query.filter_by(payment_status=request.args.get('payment_status'))
        
        room_records = query.all()
        data = [rr.to_dict() for rr in room_records]
        return success_response('Room records fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_room_record(id):
    """Get room record by ID"""
    try:
        room_record = RoomRecord.query.get(id)
        if not room_record:
            return error_response('Room record not found', 404)
        return success_response('Room record fetched successfully', room_record.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_room_record():
    """Create a new room record (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['room_id', 'user_id', 'check_in_date', 'check_out_date', 'total_price']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        room_record = RoomRecord(
            room_id=data['room_id'],
            user_id=data['user_id'],
            worker_id=data.get('worker_id'),
            check_in_date=data['check_in_date'],
            check_out_date=data['check_out_date'],
            num_guests=data.get('num_guests', 1),
            total_price=data['total_price'],
            amount_paid=data.get('amount_paid', 0.00),
            payment_status=data.get('payment_status', 'pending'),
            booking_status=data.get('booking_status', 'confirmed'),
            payment_method=data.get('payment_method'),
            special_requests=data.get('special_requests')
        )
        
        db.session.add(room_record)
        db.session.commit()
        
        return success_response('Room record created successfully', room_record.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_room_record(id):
    """Update room record (protected)"""
    try:
        room_record = RoomRecord.query.get(id)
        if not room_record:
            return error_response('Room record not found', 404)
        
        data = request.get_json()
        
        if 'actual_check_in' in data:
            room_record.actual_check_in = data['actual_check_in']
        if 'actual_check_out' in data:
            room_record.actual_check_out = data['actual_check_out']
        if 'num_guests' in data:
            room_record.num_guests = data['num_guests']
        if 'amount_paid' in data:
            room_record.amount_paid = data['amount_paid']
        if 'payment_status' in data:
            room_record.payment_status = data['payment_status']
        if 'booking_status' in data:
            room_record.booking_status = data['booking_status']
        if 'payment_method' in data:
            room_record.payment_method = data['payment_method']
        if 'special_requests' in data:
            room_record.special_requests = data['special_requests']
        
        db.session.commit()
        
        return success_response('Room record updated successfully', room_record.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_room_record(id):
    """Delete room record (protected)"""
    try:
        room_record = RoomRecord.query.get(id)
        if not room_record:
            return error_response('Room record not found', 404)
        
        db.session.delete(room_record)
        db.session.commit()
        
        return success_response('Room record deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
