from src import db
from datetime import datetime, date


class BusinessSubscription(db.Model):
    """Business Subscription Model - a request/approval record with a limits snapshot"""
    __tablename__ = 'business_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)
    # pending, active, expired, rejected, cancelled
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    # Snapshot of the plan limits at request/approval time. The backend always
    # enforces these values - they are never hard-coded in the frontend.
    max_staff = db.Column(db.Integer, default=1)
    max_branches = db.Column(db.Integer, default=1)
    max_rooms = db.Column(db.Integer, default=10)
    amount_paid = db.Column(db.Numeric(10, 2), default=0.00)
    requested_by = db.Column(db.Integer)
    requested_by_name = db.Column(db.String(150))
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer)
    approved_by_name = db.Column(db.String(150))
    approval_date = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_active_now(self):
        """True when the subscription is active and inside its validity window"""
        today = date.today()
        return (
            self.status == 'active'
            and self.start_date is not None
            and self.end_date is not None
            and self.start_date <= today <= self.end_date
        )

    def days_remaining(self):
        if not self.end_date:
            return None
        return (self.end_date - date.today()).days

    def limit_dict(self):
        return {
            'max_staff': self.max_staff,
            'max_branches': self.max_branches,
            'max_rooms': self.max_rooms
        }

    def to_dict(self):
        plan = self.plan
        return {
            'id': self.id,
            'business_id': self.business_id,
            'business_name': self.business.name if self.business else None,
            'plan_id': self.plan_id,
            'plan_name': plan.name if plan else None,
            'plan_price': float(plan.price) if plan and plan.price else 0,
            'plan_duration_days': plan.duration_days if plan else None,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'max_staff': self.max_staff,
            'max_branches': self.max_branches,
            'max_rooms': self.max_rooms,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0,
            'requested_by': self.requested_by,
            'requested_by_name': self.requested_by_name,
            'request_date': self.request_date.isoformat() if self.request_date else None,
            'approved_by': self.approved_by,
            'approved_by_name': self.approved_by_name,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'rejection_reason': self.rejection_reason,
            'notes': self.notes,
            'is_active_now': self.is_active_now(),
            'days_remaining': self.days_remaining(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
