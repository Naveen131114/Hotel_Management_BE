from flask import Blueprint, request
from src import db
from src.models.booking_accessories import BookingAccessory
from src.utils import success_response, error_response, token_required

bp = Blueprint('booking_accessories', __name__, url_prefix='/api/booking-accessories')


@bp.route('', methods=['GET'])
def get_all_booking_accessories():
    """Get all booking accessories with optional filters"""
    try:
        query = BookingAccessory.query
        
        if request.args.get('room_record_id'):
            query = query.filter_by(room_record_id=request.args.get('room_record_id'))
        
        booking_accessories = query.all()
        data = [ba.to_dict() for ba in booking_accessories]
        return success_response('Booking accessories fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_booking_accessory(id):
    """Get booking accessory by ID"""
    try:
        booking_accessory = BookingAccessory.query.get(id)
        if not booking_accessory:
            return error_response('Booking accessory not found', 404)
        return success_response('Booking accessory fetched successfully', booking_accessory.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_booking_accessory():
    """Create a new booking accessory (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['room_record_id', 'accessory_id']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        booking_accessory = BookingAccessory(
            room_record_id=data['room_record_id'],
            accessory_id=data['accessory_id'],
            quantity=data.get('quantity', 1),
            price_at_booking=data.get('price_at_booking', 0.00)
        )
        
        db.session.add(booking_accessory)
        db.session.commit()
        
        return success_response('Booking accessory created successfully', booking_accessory.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_booking_accessory(id):
    """Update booking accessory (protected)"""
    try:
        booking_accessory = BookingAccessory.query.get(id)
        if not booking_accessory:
            return error_response('Booking accessory not found', 404)
        
        data = request.get_json()
        
        if 'quantity' in data:
            booking_accessory.quantity = data['quantity']
        if 'price_at_booking' in data:
            booking_accessory.price_at_booking = data['price_at_booking']
        
        db.session.commit()
        
        return success_response('Booking accessory updated successfully', booking_accessory.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_booking_accessory(id):
    """Delete booking accessory (protected)"""
    try:
        booking_accessory = BookingAccessory.query.get(id)
        if not booking_accessory:
            return error_response('Booking accessory not found', 404)
        
        db.session.delete(booking_accessory)
        db.session.commit()
        
        return success_response('Booking accessory deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
