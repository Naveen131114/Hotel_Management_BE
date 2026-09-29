from src import db
from datetime import datetime


class Business(db.Model):
    """Business (Tenant) Model - one hotel/lodge group using the SaaS product"""
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    owner_name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    gst_number = db.Column(db.String(50))
    tax_percent = db.Column(db.Numeric(5, 2), default=0.00)
    logo_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    branches = db.relationship('Branch', backref='business', lazy=True)
    subscriptions = db.relationship('BusinessSubscription', backref='business', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'owner_name': self.owner_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'gst_number': self.gst_number,
            'tax_percent': float(self.tax_percent) if self.tax_percent else 0,
            'logo_url': self.logo_url,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def public_dict(self):
        """Limited payload for the public booking website (no sensitive data)"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'city': self.city,
            'state': self.state,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'logo_url': self.logo_url,
            'description': self.description,
            'tax_percent': float(self.tax_percent) if self.tax_percent else 0
        }
