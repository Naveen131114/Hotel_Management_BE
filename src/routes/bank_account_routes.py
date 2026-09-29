from flask import Blueprint, request

from src import db
from src.models.bank_accounts import BankAccount
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, tenant_scope, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_BANK_ACCOUNTS,
    ROLE_OWNER, ROLE_STAFF,
)

bp = Blueprint('bank_accounts', __name__, url_prefix='/api/bank-accounts')


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_bank_accounts():
    """List bank accounts of the hotel (selectable during payments)"""
    try:
        query = tenant_scope(BankAccount, BankAccount.query)
        if request.args.get('active_only') in ('1', 'true', 'True'):
            query = query.filter(BankAccount.is_active.is_(True))
        accounts = query.order_by(BankAccount.bank_name.asc()).all()
        return success_response('Bank accounts fetched successfully',
                                [a.to_dict() for a in accounts], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_bank_account(id):
    """Get a single bank account"""
    try:
        account = tenant_scope(BankAccount, BankAccount.query).filter(BankAccount.id == id).first()
        if not account:
            return error_response('Bank account not found', 404)
        return success_response('Bank account fetched successfully', account.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required(ROLE_OWNER, ROLE_STAFF)
@require_permission('create')
def create_bank_account():
    """Create a bank account for the current hotel"""
    try:
        data = request.get_json() or {}
        required = ['bank_name', 'account_holder_name', 'account_number']
        if not all(field in data and data.get(field) for field in required):
            return error_response('Bank name, account holder name and account number are required', 400)

        user = get_current_user()
        account = BankAccount(
            business_id=current_business_id(),
            branch_id=data.get('branch_id'),
            bank_name=data['bank_name'],
            account_holder_name=data['account_holder_name'],
            account_number=data['account_number'],
            ifsc_code=data.get('ifsc_code'),
            branch_name=data.get('branch_name'),
            account_type=data.get('account_type', 'current'),
            is_active=data.get('is_active', True),
            created_by=user.id if user else None
        )
        db.session.add(account)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_BANK_ACCOUNTS, account.id, account.bank_name,
                     f"Created bank account {account.bank_name}")
        return success_response('Bank account created successfully', account.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required(ROLE_OWNER, ROLE_STAFF)
@require_permission('edit')
def update_bank_account(id):
    """Update a bank account"""
    try:
        account = tenant_scope(BankAccount, BankAccount.query).filter(BankAccount.id == id).first()
        if not account:
            return error_response('Bank account not found', 404)

        data = request.get_json() or {}
        for field in ('bank_name', 'account_holder_name', 'account_number', 'ifsc_code',
                      'branch_name', 'account_type', 'is_active', 'branch_id'):
            if field in data:
                setattr(account, field, data[field])
        account.updated_by = get_current_user().id
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_BANK_ACCOUNTS, account.id, account.bank_name,
                     f"Updated bank account {account.bank_name}")
        return success_response('Bank account updated successfully', account.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required(ROLE_OWNER)
@require_permission('delete')
def delete_bank_account(id):
    """Delete a bank account"""
    try:
        account = tenant_scope(BankAccount, BankAccount.query).filter(BankAccount.id == id).first()
        if not account:
            return error_response('Bank account not found', 404)

        db.session.delete(account)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, MODULE_BANK_ACCOUNTS, id, account.bank_name,
                     f"Deleted bank account {account.bank_name}")
        return success_response('Bank account deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
