from src import db
from datetime import datetime
import json


class SubscriptionPlan(db.Model):
    """Subscription Plan Model - created/managed by the Super Admin (product owner)"""
    __tablename__ = 'subscription_plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    duration_days = db.Column(db.Integer, default=30)
    max_staff = db.Column(db.Integer, default=1)
    max_branches = db.Column(db.Integer, default=1)
    max_rooms = db.Column(db.Integer, default=10)
    # Free-form JSON string so extra limits/features can be added later
    # without a schema change (e.g. {"online_booking": true, "reports": false})
    features = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = db.relationship('BusinessSubscription', backref='plan', lazy=True)

    def feature_dict(self):
        if not self.features:
            return {}
        try:
            return json.loads(self.features)
        except (ValueError, TypeError):
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else 0,
            'duration_days': self.duration_days,
            'max_staff': self.max_staff,
            'max_branches': self.max_branches,
            'max_rooms': self.max_rooms,
            'features': self.feature_dict(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def limit_dict(self):
        """Limits snapshot stored on a business subscription"""
        return {
            'max_staff': self.max_staff,
            'max_branches': self.max_branches,
            'max_rooms': self.max_rooms
        }
