from flask import Blueprint, request

from src import db
from src.models.payments import Payment
from src.models.room_records import RoomRecord
from src.services import booking_service
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user,
)
from src.utils.constants import ACTIVITY_DELETE, ACTIVITY_PAYMENT, ACTIVITY_UPDATE, MODULE_PAYMENTS

bp = Blueprint('payments', __name__, url_prefix='/api/payments')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_payments():
    """Get all payments of the current hotel/branch with optional filters"""
    try:
        query = tenant_scope(Payment, Payment.query)

        if request.args.get('room_record_id'):
            query = query.filter_by(room_record_id=request.args.get('room_record_id'))
        if request.args.get('status'):
            query = query.filter_by(status=request.args.get('status'))
        if request.args.get('method'):
            query = query.filter_by(method=request.args.get('method'))
        if request.args.get('payment_type'):
            query = query.filter_by(payment_type=request.args.get('payment_type'))
        if request.args.get('from'):
            query = query.filter(Payment.paid_at >= request.args['from'])
        if request.args.get('to'):
            query = query.filter(Payment.paid_at <= f"{request.args['to']} 23:59:59")

        payments = query.order_by(Payment.paid_at.desc()).all()
        return success_response('Payments fetched successfully',
                                [payment.to_dict() for payment in payments], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_payment(id):
    """Get payment by ID (tenant scoped)"""
    try:
        payment = tenant_scope(Payment, Payment.query).filter(Payment.id == id).first()
        if not payment:
            return error_response('Payment not found', 404)
        return success_response('Payment fetched successfully', payment.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('edit')
def create_payment():
    """Record a payment against a booking owned by the current hotel"""
    try:
        data = request.get_json()

        required_fields = ['room_record_id', 'amount']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)

        booking = tenant_scope(RoomRecord, RoomRecord.query).filter(
            RoomRecord.id == data['room_record_id']
        ).first()
        if not booking:
            return error_response('Booking not found', 404)

        payment, error = booking_service.add_payment(
            booking, data['amount'],
            method=data.get('method') or 'cash',
            actor=get_current_user(),
            payment_type=data.get('payment_type') or 'advance',
            bank_account_id=data.get('bank_account_id'),
            upi_account_id=data.get('upi_account_id'),
            transaction_ref=data.get('transaction_ref'),
            notes=data.get('notes')
        )
        if error:
            return error_response(error, 400)

        log_activity(ACTIVITY_PAYMENT, MODULE_PAYMENTS, payment.id, booking.booking_number,
                     f"Collected {payment.amount} via {payment.method} for booking {booking.booking_number}",
                     branch_id=booking.branch_id)
        return success_response('Payment created successfully', payment.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_payment(id):
    """Update a payment (status changes recompute the booking balance)"""
    try:
        payment = tenant_scope(Payment, Payment.query).filter(Payment.id == id).first()
        if not payment:
            return error_response('Payment not found', 404)

        data = request.get_json()
        for field in ('amount', 'method', 'status', 'transaction_ref', 'notes',
                      'bank_account_id', 'upi_account_id', 'payment_type'):
            if field in data:
                setattr(payment, field, data[field])
        booking_service.sync_payment_state(payment.room_record, commit=False)
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_PAYMENTS, payment.id,
                     payment.room_record.booking_number if payment.room_record else None,
                     f"Updated payment #{payment.id}")
        return success_response('Payment updated successfully', payment.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_payment(id):
    """Delete a payment (booking balance is recomputed)"""
    try:
        payment = tenant_scope(Payment, Payment.query).filter(Payment.id == id).first()
        if not payment:
            return error_response('Payment not found', 404)

        booking = payment.room_record
        db.session.delete(payment)
        db.session.flush()
        if booking is not None:
            db.session.refresh(booking)
            booking_service.sync_payment_state(booking, commit=False)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_PAYMENTS, id, None, f"Deleted payment #{id}")
        return success_response('Payment deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
