"""Subscription rules: active plan resolution, usage counters and limit checks.

All limits are enforced here (server side) and exposed to the frontend only for
display purposes - the backend is always the source of truth.
"""
from datetime import date, datetime, timedelta

from src import db
from src.models.branches import Branch
from src.models.rooms import Room
from src.models.users import User
from src.models.business_subscriptions import BusinessSubscription
from src.models.subscription_plans import SubscriptionPlan
from src.utils.constants import (
    DEFAULT_FALLBACK_LIMITS, ROLE_STAFF, SUBSCRIPTION_ACTIVE, SUBSCRIPTION_CANCELLED,
    SUBSCRIPTION_EXPIRED, SUBSCRIPTION_PENDING, SUBSCRIPTION_REJECTED,
)


def _today():
    return date.today()


def latest_subscription(business_id):
    """Most recent subscription record of a business (any status)"""
    if not business_id:
        return None
    return (
        BusinessSubscription.query
        .filter_by(business_id=business_id)
        .order_by(BusinessSubscription.request_date.desc(), BusinessSubscription.id.desc())
        .first()
    )


def expire_stale_subscriptions(business_id=None):
    """Flip active-but-out-of-window subscriptions to `expired` (no data deleted)"""
    query = BusinessSubscription.query.filter(BusinessSubscription.status == SUBSCRIPTION_ACTIVE)
    if business_id:
        query = query.filter(BusinessSubscription.business_id == business_id)
    changed = False
    for subscription in query.all():
        if subscription.end_date and subscription.end_date < _today():
            subscription.status = SUBSCRIPTION_EXPIRED
            changed = True
    if changed:
        db.session.commit()
    return changed


def get_active_subscription(business_id):
    """Currently valid subscription (status active and inside its date window)"""
    if not business_id:
        return None
    today = _today()
    subscription = (
        BusinessSubscription.query
        .filter(
            BusinessSubscription.business_id == business_id,
            BusinessSubscription.status == SUBSCRIPTION_ACTIVE,
            BusinessSubscription.start_date <= today,
            BusinessSubscription.end_date >= today,
        )
        .order_by(BusinessSubscription.end_date.desc())
        .first()
    )
    if subscription is None:
        expire_stale_subscriptions(business_id)
    return subscription


def subscription_status(business_id):
    """Return (state, subscription) where state is active/expired/pending/rejected/none"""
    active = get_active_subscription(business_id)
    if active is not None:
        return SUBSCRIPTION_ACTIVE, active
    latest = latest_subscription(business_id)
    if latest is None:
        return 'none', None
    if latest.status in (SUBSCRIPTION_PENDING, SUBSCRIPTION_REJECTED, SUBSCRIPTION_CANCELLED, SUBSCRIPTION_EXPIRED):
        return latest.status, latest


def effective_limits(business_id):
    """Limits snapshot of the active subscription (falls back to tiny defaults)"""
    active = get_active_subscription(business_id)
    if active is None:
        return dict(DEFAULT_FALLBACK_LIMITS), False
    return active.limit_dict(), True


def business_usage(business_id):
    """Current usage counters checked against the plan limits"""
    if not business_id:
        return {'branches': 0, 'rooms': 0, 'staff': 0}
    return {
        'branches': Branch.query.filter_by(business_id=business_id).count(),
        'rooms': Room.query.filter_by(business_id=business_id).count(),
        'staff': User.query.filter_by(business_id=business_id, role=ROLE_STAFF).count(),
    }


def limit_status(business_id):
    """Display payload: state + limits + usage + remaining"""
    limits, has_active = effective_limits(business_id)
    used = business_usage(business_id)
    state, subscription = subscription_status(business_id)
    return {
        'status': state,
        'has_active_subscription': has_active,
        'subscription': subscription.to_dict() if subscription else None,
        'limits': limits,
        'usage': used,
        'remaining': {
            'branches': max(limits['max_branches'] - used['branches'], 0),
            'rooms': max(limits['max_rooms'] - used['rooms'], 0),
            'staff': max(limits['max_staff'] - used['staff'], 0),
        },
    }


def write_blocked_reason(business_id):
    """Message explaining why create/update is blocked (None = writes allowed)"""
    state, subscription = subscription_status(business_id)
    if state == SUBSCRIPTION_ACTIVE:
        return None
    if state == SUBSCRIPTION_EXPIRED:
        end = subscription.end_date.isoformat() if subscription and subscription.end_date else ''
        return (
            f'Your subscription expired on {end}. You can still view your data but creating or '
            'updating records is locked until the subscription is renewed.'
        )
    if state == SUBSCRIPTION_PENDING:
        return 'Your subscription request is awaiting approval. Creating or updating records is locked until it is approved.'
    if state == SUBSCRIPTION_REJECTED:
        return 'Your subscription request was rejected. Please request a plan again to continue.'
    return 'No active subscription found for this hotel. Please request a subscription plan to continue.'


def check_limit(business_id, resource):
    """Server-side limit check used by branch/room/staff creation

    Returns (allowed, message, usage, limits)
    """
    limits, has_active = effective_limits(business_id)
    used = business_usage(business_id)
    if not has_active:
        return False, write_blocked_reason(business_id), used, limits

    key = {'branch': 'branches', 'room': 'rooms', 'staff': 'staff'}.get(resource)
    if key is None:
        return True, None, used, limits

    limit_key = f'max_{key}'
    if used[key] >= limits.get(limit_key, 0):
        labels = {'branches': 'Branch', 'rooms': 'Room', 'staff': 'Staff'}
        return (
            False,
            f"{labels[key]} limit reached for your subscription plan "
            f"({used[key]}/{limits.get(limit_key)}). Please upgrade your plan.",
            used,
            limits
        )
    return True, None, used, limits


def activate_subscription(subscription, approved_by=None, start_date=None, amount_paid=None):
    """Activate (or renew) a subscription for its validity window"""
    today = start_date or _today()
    plan = subscription.plan
    duration = plan.duration_days if plan and plan.duration_days else 30

    # A renewal continues from the current end date when that is still in future
    base_date = today
    current_active = get_active_subscription(subscription.business_id)
    if current_active and current_active.id != subscription.id and current_active.end_date > today:
        base_date = current_active.end_date

    subscription.status = SUBSCRIPTION_ACTIVE
    subscription.start_date = today
    subscription.end_date = base_date + timedelta(days=duration)
    if plan:
        subscription.max_staff = plan.max_staff
        subscription.max_branches = plan.max_branches
        subscription.max_rooms = plan.max_rooms
    if amount_paid is not None:
        subscription.amount_paid = amount_paid
    subscription.approval_date = datetime.utcnow()
    if approved_by is not None:
        subscription.approved_by = approved_by.id
        subscription.approved_by_name = f"{approved_by.first_name or ''} {approved_by.last_name or ''}".strip()
    db.session.commit()
    return subscription


def create_request(business_id, plan_id, requested_by=None, notes=None):
    """Create a pending subscription request, reusing an existing pending one"""
    plan = db.session.get(SubscriptionPlan, plan_id) if plan_id else None
    if plan is None:
        return None, 'Subscription plan not found', 404

    existing = (
        BusinessSubscription.query
        .filter_by(business_id=business_id, status=SUBSCRIPTION_PENDING)
        .first()
    )
    subscription = existing or BusinessSubscription(business_id=business_id, status=SUBSCRIPTION_PENDING)
    subscription.plan_id = plan.id
    subscription.max_staff = plan.max_staff
    subscription.max_branches = plan.max_branches
    subscription.max_rooms = plan.max_rooms
    subscription.request_date = datetime.utcnow()
    subscription.notes = notes
    if requested_by is not None:
        subscription.requested_by = requested_by.id
        subscription.requested_by_name = f"{requested_by.first_name or ''} {requested_by.last_name or ''}".strip()
    db.session.add(subscription)
    db.session.commit()
    return subscription, None, 201

    return 'none', latest
