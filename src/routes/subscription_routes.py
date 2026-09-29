from datetime import datetime

from flask import Blueprint, request

from src import db
from src.models.business_subscriptions import BusinessSubscription
from src.models.subscription_plans import SubscriptionPlan
from src.services import subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import (
    ACTIVITY_APPROVE, ACTIVITY_CREATE, ACTIVITY_REJECT, MODULE_SUBSCRIPTION,
    ROLE_OWNER, ROLE_SUPER_ADMIN, SUBSCRIPTION_PENDING, SUBSCRIPTION_REJECTED,
)

bp = Blueprint('subscriptions', __name__, url_prefix='/api/subscriptions')


@bp.route('/my', methods=['GET'])
@auth_required()
@require_permission('view')
def my_subscription():
    """Current subscription, limits, usage and request history for the hotel"""
    try:
        business_id = current_business_id()
        status = subscription_service.limit_status(business_id)
        history = (
            BusinessSubscription.query
            .filter_by(business_id=business_id)
            .order_by(BusinessSubscription.request_date.desc())
            .all()
        )
        status['history'] = [item.to_dict() for item in history]
        return success_response('Subscription information fetched successfully', status, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/requests', methods=['GET'])
@auth_required()
def list_requests():
    """Subscription requests: all (super admin) or own hotel's (owner)"""
    try:
        user = get_current_user()
        query = BusinessSubscription.query
        if user.role == ROLE_SUPER_ADMIN:
            scoped = request.args.get('business_id')
            if scoped and str(scoped).isdigit():
                query = query.filter(BusinessSubscription.business_id == int(scoped))
        else:
            query = query.filter(BusinessSubscription.business_id == user.business_id)

        if request.args.get('status'):
            query = query.filter(BusinessSubscription.status == request.args.get('status'))

        requests = query.order_by(BusinessSubscription.request_date.desc()).all()
        return success_response('Subscription requests fetched successfully',
                                [item.to_dict() for item in requests], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/requests', methods=['POST'])
@auth_required(ROLE_OWNER)
@require_permission('create')
def request_subscription():
    """Hotel owner requests a subscription plan -> waiting for super admin approval"""
    try:
        data = request.get_json() or {}
        plan_id = data.get('plan_id')
        if not plan_id:
            return error_response('plan_id is required', 400)

        plan = db.session.get(SubscriptionPlan, int(plan_id))
        if plan is None or not plan.is_active:
            return error_response('Subscription plan not found or inactive', 404)

        subscription, error, status = subscription_service.create_request(
            current_business_id(), plan.id, requested_by=get_current_user(), notes=data.get('notes')
        )
        if error:
            return error_response(error, status)

        log_activity(ACTIVITY_CREATE, MODULE_SUBSCRIPTION, subscription.id, plan.name,
                     f"Requested subscription plan {plan.name}")
        return success_response('Subscription request submitted successfully',
                                subscription.to_dict(), status_code=201)
    except (TypeError, ValueError):
        return error_response('plan_id must be a number', 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/requests/<int:id>/approve', methods=['POST'])
@auth_required(ROLE_SUPER_ADMIN)
def approve_request(id):
    """Super admin approves a request -> the subscription becomes active"""
    try:
        subscription = db.session.get(BusinessSubscription, id)
        if not subscription:
            return error_response('Subscription request not found', 404)
        if subscription.is_active_now():
            return error_response('This subscription is already active', 400)

        data = request.get_json() or {}
        start_date = None
        if data.get('start_date'):
            try:
                start_date = datetime.strptime(str(data['start_date'])[:10], '%Y-%m-%d').date()
            except ValueError:
                return error_response('start_date must be in YYYY-MM-DD format', 400)

        subscription.rejection_reason = None
        subscription = subscription_service.activate_subscription(
            subscription, approved_by=get_current_user(),
            start_date=start_date, amount_paid=data.get('amount_paid')
        )

        log_activity(ACTIVITY_APPROVE, MODULE_SUBSCRIPTION, subscription.id, subscription.plan.name if subscription.plan else None,
                     f"Approved subscription request #{subscription.id} for business #{subscription.business_id}",
                     business_id=subscription.business_id)
        return success_response('Subscription approved successfully', subscription.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/requests/<int:id>/reject', methods=['POST'])
@auth_required(ROLE_SUPER_ADMIN)
def reject_request(id):
    """Super admin rejects a subscription request"""
    try:
        subscription = db.session.get(BusinessSubscription, id)
        if not subscription:
            return error_response('Subscription request not found', 404)

        data = request.get_json() or {}
        subscription.status = SUBSCRIPTION_REJECTED
        subscription.rejection_reason = data.get('reason') or data.get('rejection_reason')
        subscription.approval_date = datetime.utcnow()
        approver = get_current_user()
        subscription.approved_by = approver.id
        subscription.approved_by_name = f"{approver.first_name or ''} {approver.last_name or ''}".strip()
        db.session.commit()

        log_activity(ACTIVITY_REJECT, MODULE_SUBSCRIPTION, subscription.id, None,
                     f"Rejected subscription request #{subscription.id}",
                     business_id=subscription.business_id)
        return success_response('Subscription request rejected', subscription.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
