from flask import Blueprint, request

from src import db
from src.models.businesses import Business
from src.services import subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    log_activity, get_current_user, current_business_id,
)
from src.utils.constants import ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, ROLE_OWNER, ROLE_SUPER_ADMIN

bp = Blueprint('business', __name__, url_prefix='/api/business')


def _current_business():
    user = get_current_user()
    if user.role == ROLE_SUPER_ADMIN:
        business_id = request.args.get('business_id') or (request.get_json(silent=True) or {}).get('business_id')
        return db.session.get(Business, int(business_id)) if business_id else None
    return db.session.get(Business, user.business_id)


@bp.route('/profile', methods=['GET'])
@auth_required()
@require_permission('view')
def get_profile():
    """Hotel/lodge profile of the current tenant"""
    try:
        business = _current_business()
        if not business:
            return error_response('Business profile not found', 404)
        return success_response('Business profile fetched successfully', business.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/profile', methods=['PUT'])
@auth_required(ROLE_OWNER)
@require_permission('edit')
def update_profile():
    """Update hotel/lodge details (name, address, GST, tax percent, logo ...)"""
    try:
        business = db.session.get(Business, current_business_id())
        if not business:
            return error_response('Business profile not found', 404)

        data = request.get_json() or {}
        for field in ('name', 'owner_name', 'email', 'phone', 'address', 'city',
                      'state', 'country', 'gst_number', 'logo_url', 'description'):
            if field in data:
                setattr(business, field, data[field])
        if 'tax_percent' in data:
            try:
                business.tax_percent = float(data['tax_percent'])
            except (TypeError, ValueError):
                return error_response('tax_percent must be a number', 400)
        if data.get('slug'):
            slug = str(data['slug']).strip().lower()
            existing = Business.query.filter(Business.slug == slug, Business.id != business.id).first()
            if existing:
                return error_response('This booking website slug is already taken', 400)
            business.slug = slug

        db.session.commit()
        log_activity(ACTIVITY_UPDATE, 'business', business.id, business.name,
                     f"Updated hotel profile {business.name}")
        return success_response('Business profile updated successfully', business.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/limits', methods=['GET'])
@auth_required()
@require_permission('view')
def get_limits():
    """Subscription state, plan limits and current usage (branch/room/staff)"""
    try:
        data = subscription_service.limit_status(current_business_id())
        return success_response('Subscription limits fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
