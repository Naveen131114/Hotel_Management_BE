from flask import Blueprint, request

from src import db
from src.models.subscription_plans import SubscriptionPlan
from src.models.business_subscriptions import BusinessSubscription
from src.utils import success_response, error_response, auth_required, log_activity, get_current_user
from src.utils.constants import (
    ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, ROLE_SUPER_ADMIN,
)

bp = Blueprint('subscription_plans', __name__, url_prefix='/api/subscription-plans')


@bp.route('', methods=['GET'])
@auth_required()
def get_plans():
    """List subscription plans (hotel owners see the active ones only)"""
    try:
        user = get_current_user()
        query = SubscriptionPlan.query
        if user.role != ROLE_SUPER_ADMIN or request.args.get('include_inactive') not in ('1', 'true'):
            query = query.filter(SubscriptionPlan.is_active.is_(True))
        plans = query.order_by(SubscriptionPlan.price.asc()).all()
        return success_response('Subscription plans fetched successfully',
                                [plan.to_dict() for plan in plans], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
def get_plan(id):
    """Get a single subscription plan"""
    try:
        plan = db.session.get(SubscriptionPlan, id)
        if not plan:
            return error_response('Subscription plan not found', 404)
        return success_response('Subscription plan fetched successfully', plan.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required(ROLE_SUPER_ADMIN)
def create_plan():
    """Create a subscription plan (super admin / product owner only)"""
    try:
        data = request.get_json() or {}
        if not data.get('name'):
            return error_response('Plan name is required', 400)

        plan = SubscriptionPlan(
            name=data['name'],
            description=data.get('description'),
            price=data.get('price', 0),
            duration_days=int(data.get('duration_days') or 30),
            max_staff=int(data.get('max_staff') or 1),
            max_branches=int(data.get('max_branches') or 1),
            max_rooms=int(data.get('max_rooms') or 10),
            features=data.get('features'),
            is_active=data.get('is_active', True)
        )
        if isinstance(plan.features, (dict, list)):
            import json
            plan.features = json.dumps(plan.features)

        db.session.add(plan)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, MODULE_SUBSCRIPTION, plan.id, plan.name,
                     f"Created subscription plan {plan.name}", business_id=None)
        return success_response('Subscription plan created successfully', plan.to_dict(), status_code=201)
    except (TypeError, ValueError):
        return error_response('price, duration_days and limits must be numbers', 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required(ROLE_SUPER_ADMIN)
def update_plan(id):
    """Update a subscription plan"""
    try:
        plan = db.session.get(SubscriptionPlan, id)
        if not plan:
            return error_response('Subscription plan not found', 404)

        data = request.get_json() or {}
        for field in ('name', 'description', 'features', 'is_active'):
            if field in data:
                setattr(plan, field, data[field])
        if isinstance(plan.features, (dict, list)):
            import json
            plan.features = json.dumps(plan.features)
        for field in ('price', 'duration_days', 'max_staff', 'max_branches', 'max_rooms'):
            if field in data:
                setattr(plan, field, data[field] if field == 'price' else int(data[field]))

        db.session.commit()
        log_activity(ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, plan.id, plan.name,
                     f"Updated subscription plan {plan.name}", business_id=None)
        return success_response('Subscription plan updated successfully', plan.to_dict(), status_code=200)
    except (TypeError, ValueError):
        return error_response('price, duration_days and limits must be numbers', 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required(ROLE_SUPER_ADMIN)
def delete_plan(id):
    """Delete a plan, or deactivate it when subscriptions still reference it"""
    try:
        plan = db.session.get(SubscriptionPlan, id)
        if not plan:
            return error_response('Subscription plan not found', 404)

        in_use = BusinessSubscription.query.filter_by(plan_id=plan.id).count()
        if in_use:
            plan.is_active = False
            db.session.commit()
            return success_response(
                'This plan is used by existing subscriptions, so it was deactivated instead of deleted',
                plan.to_dict(), status_code=200
            )

        db.session.delete(plan)
        db.session.commit()
        log_activity(ACTIVITY_DELETE, MODULE_SUBSCRIPTION, id, plan.name,
                     f"Deleted subscription plan {plan.name}", business_id=None)
        return success_response('Subscription plan deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
