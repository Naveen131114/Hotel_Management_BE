from flask import Blueprint, request

from src import db
from src.models.upi_accounts import UpiAccount
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, tenant_scope, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_UPI_ACCOUNTS,
    ROLE_OWNER, ROLE_STAFF,
)

bp = Blueprint('upi_accounts', __name__, url_prefix='/api/upi-accounts')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_upi_accounts():
    """List UPI accounts of the hotel (selectable during payments)"""
    try:
        query = tenant_scope(UpiAccount, UpiAccount.query)
        if request.args.get('active_only') in ('1', 'true', 'True'):
            query = query.filter(UpiAccount.is_active.is_(True))
        accounts = query.order_by(UpiAccount.upi_name.asc()).all()
        return success_response('UPI accounts fetched successfully',
                                [a.to_dict() for a in accounts], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_upi_account(id):
    """Get a single UPI account"""
    try:
        account = tenant_scope(UpiAccount, UpiAccount.query).filter(UpiAccount.id == id).first()
        if not account:
            return error_response('UPI account not found', 404)
        return success_response('UPI account fetched successfully', account.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required(ROLE_OWNER, ROLE_STAFF)
@require_permission('create')
def create_upi_account():
    """Create a UPI account for the current hotel"""
    try:
        data = request.get_json() or {}
        if not data.get('upi_name') or not data.get('upi_id'):
            return error_response('UPI name and UPI ID are required', 400)

        user = get_current_user()
        account = UpiAccount(
            business_id=current_business_id(),
            branch_id=data.get('branch_id'),
            upi_name=data['upi_name'],
            upi_id=data['upi_id'],
            phone_number=data.get('phone_number'),
            qr_code_url=data.get('qr_code_url'),
            is_active=data.get('is_active', True),
            created_by=user.id if user else None
        )
        db.session.add(account)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_UPI_ACCOUNTS, account.id, account.upi_id,
                     f"Created UPI account {account.upi_name}")
        return success_response('UPI account created successfully', account.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required(ROLE_OWNER, ROLE_STAFF)
@require_permission('edit')
def update_upi_account(id):
    """Update a UPI account"""
    try:
        account = tenant_scope(UpiAccount, UpiAccount.query).filter(UpiAccount.id == id).first()
        if not account:
            return error_response('UPI account not found', 404)

        data = request.get_json() or {}
        for field in ('upi_name', 'upi_id', 'phone_number', 'qr_code_url', 'is_active', 'branch_id'):
            if field in data:
                setattr(account, field, data[field])
        account.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_UPI_ACCOUNTS, account.id, account.upi_id,
                     f"Updated UPI account {account.upi_name}")
        return success_response('UPI account updated successfully', account.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required(ROLE_OWNER)
@require_permission('delete')
def delete_upi_account(id):
    """Delete a UPI account"""
    try:
        account = tenant_scope(UpiAccount, UpiAccount.query).filter(UpiAccount.id == id).first()
        if not account:
            return error_response('UPI account not found', 404)

        db.session.delete(account)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_UPI_ACCOUNTS, id, account.upi_id,
                     f"Deleted UPI account {account.upi_name}")
        return success_response('UPI account deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
