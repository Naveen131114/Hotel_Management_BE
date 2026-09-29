from datetime import date, datetime

from flask import Blueprint, request

from src import db
from src.models.businesses import Business
from src.models.branches import Branch
from src.models.rooms import Room
from src.models.users import User
from src.models.room_records import RoomRecord
from src.models.business_subscriptions import BusinessSubscription
from src.services import subscription_service
from src.utils import success_response, error_response, auth_required, log_activity, get_current_user
from src.utils.constants import (
    ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, ROLE_OWNER, ROLE_STAFF, ROLE_SUPER_ADMIN,
    SUBSCRIPTION_ACTIVE, SUBSCRIPTION_EXPIRED, SUBSCRIPTION_PENDING,
)

bp = Blueprint('super_admin', __name__, url_prefix='/api/super-admin')


@bp.route('/dashboard', methods=['GET'])
@auth_required(ROLE_SUPER_ADMIN)
def dashboard():
    """SaaS level dashboard: hotels, subscriptions, users, branches, rooms, bookings"""
    try:
        # Keep the subscription statuses honest before reporting
        subscription_service.expire_stale_subscriptions()
        today = date.today()

        subscriptions = BusinessSubscription.query.all()
        active = [s for s in subscriptions if s.is_active_now()]
        expired = [s for s in subscriptions if s.status == SUBSCRIPTION_EXPIRED
                   or (s.status == SUBSCRIPTION_ACTIVE and not s.is_active_now())]
        pending = [s for s in subscriptions if s.status == SUBSCRIPTION_PENDING]
        revenue = sum(float(s.amount_paid or 0) for s in subscriptions if s.status == SUBSCRIPTION_ACTIVE)

        data = {
            'total_businesses': Business.query.count(),
            'active_businesses': Business.query.filter_by(is_active=True).count(),
            'total_subscriptions': len(subscriptions),
            'active_subscriptions': len(active),
            'expired_subscriptions': len(expired),
            'trial_subscriptions': len([s for s in active if s.plan and not float(s.plan.price or 0)]),
            'pending_requests': len(pending),
            'total_users': User.query.count(),
            'owner_logins': User.query.filter_by(role=ROLE_OWNER).count(),
            'staff_logins': User.query.filter_by(role=ROLE_STAFF).count(),
            'total_branches': Branch.query.count(),
            'total_rooms': Room.query.count(),
            'total_bookings': RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)).count(),
            'bookings_today': RoomRecord.query.filter(
                RoomRecord.is_deleted.is_(False),
                RoomRecord.created_at >= datetime.combine(today, datetime.min.time())
            ).count(),
            'subscription_revenue': round(revenue, 2),
            'recent_businesses': [
                business.to_dict() for business in
                Business.query.order_by(Business.created_at.desc()).limit(5).all()
            ],
            'pending_requests_list': [
                item.to_dict() for item in
                sorted(pending, key=lambda s: s.request_date or datetime.utcnow(), reverse=True)[:10]
            ]
        }
        return success_response('Super admin dashboard fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)



@bp.route('/businesses', methods=['GET'])
@auth_required(ROLE_SUPER_ADMIN)
def list_businesses():
    """List all hotel/lodge tenants with their subscription state and usage"""
    try:
        businesses = Business.query.order_by(Business.created_at.desc()).all()
        data = []
        for business in businesses:
            state, subscription = subscription_service.subscription_status(business.id)
            limits = subscription_service.limit_status(business.id)
            payload = business.to_dict()
            payload['subscription_status'] = state
            payload['subscription'] = subscription.to_dict() if subscription else None
            payload['usage'] = limits['usage']
            payload['limits'] = limits['limits']
            data.append(payload)
        return success_response('Businesses fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/businesses', methods=['POST'])
@auth_required(ROLE_SUPER_ADMIN)
def create_business():
    """Create a hotel/lodge tenant together with its first branch and owner login"""
    try:
        data = request.get_json() or {}
        required = ['name', 'slug', 'owner_email']
        if not all(data.get(field) for field in required):
            return error_response('name, slug and owner_email are required', 400)

        slug = str(data['slug']).strip().lower()
        if Business.query.filter_by(slug=slug).first():
            return error_response('This slug is already in use', 400)
        if User.query.filter_by(email=data['owner_email']).first():
            return error_response('This owner email is already registered', 400)

        business = Business(
            name=data['name'],
            slug=slug,
            owner_name=data.get('owner_name'),
            email=data.get('email') or data['owner_email'],
            phone=data.get('phone'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            gst_number=data.get('gst_number'),
            tax_percent=data.get('tax_percent', 0),
            description=data.get('description'),
            is_active=True
        )
        db.session.add(business)
        db.session.flush()

        branch = Branch(
            business_id=business.id,
            name=data.get('branch_name') or 'Main Branch',
            city=data.get('city'),
            phone=data.get('phone'),
            address=data.get('address'),
            is_active=True
        )
        db.session.add(branch)
        db.session.flush()

        owner = User(
            first_name=data.get('owner_first_name') or 'Owner',
            last_name=data.get('owner_last_name') or business.name,
            email=data['owner_email'],
            phone=data.get('owner_phone') or data.get('phone'),
            business_id=business.id,
            branch_id=branch.id,
            role=ROLE_OWNER,
            permission_level='full',
            is_active=True
        )
        owner.set_password(data.get('owner_password') or 'owner@123')
        db.session.add(owner)
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, business.id, business.name,
                     f"Created business {business.name} with owner {owner.email}",
                     user=get_current_user(), business_id=business.id, branch_id=branch.id)
        payload = business.to_dict()
        payload['branches'] = [branch.to_dict()]
        payload['owner'] = owner.to_dict()
        return success_response('Business created successfully', payload, status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/businesses/<int:id>/status', methods=['PUT'])
@auth_required(ROLE_SUPER_ADMIN)
def set_business_status(id):
    """Activate / deactivate a hotel account (data is always preserved)"""
    try:
        business = db.session.get(Business, id)
        if not business:
            return error_response('Business not found', 404)

        data = request.get_json() or {}
        if 'is_active' not in data:
            return error_response('is_active is required', 400)

        business.is_active = bool(data['is_active'])
        db.session.commit()
        log_activity(ACTIVITY_UPDATE, MODULE_SUBSCRIPTION, business.id, business.name,
                     f"{'Activated' if business.is_active else 'Deactivated'} business {business.name}",
                     business_id=business.id)
        return success_response('Business status updated successfully', business.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
