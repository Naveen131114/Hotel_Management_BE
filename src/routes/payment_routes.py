from flask import Blueprint, request
from src import db
from src.models.payments import Payment
from src.utils import success_response, error_response, token_required

bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@bp.route('', methods=['GET'])
def get_all_payments():
    """Get all payments with optional filters"""
    try:
        query = Payment.query
        
        if request.args.get('room_record_id'):
            query = query.filter_by(room_record_id=request.args.get('room_record_id'))
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        
        payments = query.all()
        data = [payment.to_dict() for payment in payments]
        return success_response('Payments fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_payment(id):
    """Get payment by ID"""
    try:
        payment = Payment.query.get(id)
        if not payment:
            return error_response('Payment not found', 404)
        return success_response('Payment fetched successfully', payment.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_payment():
    """Create a new payment (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['room_record_id', 'amount']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        payment = Payment(
            room_record_id=data['room_record_id'],
            amount=data['amount'],
            method=data.get('method'),
            status=data.get('status', 'completed'),
            transaction_ref=data.get('transaction_ref'),
            notes=data.get('notes')
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return success_response('Payment created successfully', payment.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_payment(id):
    """Update payment (protected)"""
    try:
        payment = Payment.query.get(id)
        if not payment:
            return error_response('Payment not found', 404)
        
        data = request.get_json()
        
        if 'amount' in data:
            payment.amount = data['amount']
        if 'method' in data:
            payment.method = data['method']
        if 'status' in data:
            payment.status = data['status']
        if 'transaction_ref' in data:
            payment.transaction_ref = data['transaction_ref']
        if 'notes' in data:
            payment.notes = data['notes']
        
        db.session.commit()
        
        return success_response('Payment updated successfully', payment.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_payment(id):
    """Delete payment (protected)"""
    try:
        payment = Payment.query.get(id)
        if not payment:
            return error_response('Payment not found', 404)
        
        db.session.delete(payment)
        db.session.commit()
        
        return success_response('Payment deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
