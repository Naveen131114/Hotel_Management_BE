from src import db
from datetime import datetime


class RoomType(db.Model):
    """Room Type Model"""
    __tablename__ = 'room_types'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    extra_guest_price = db.Column(db.Numeric(10, 2), default=0.00)
    max_occupancy = db.Column(db.Integer, default=2)
    total_floors = db.Column(db.Integer, default=1)
    bed_type = db.Column(db.String(50))  # single, double, king, twin
    view_type = db.Column(db.String(50))  # sea, city, garden, pool
    image_url = db.Column(db.String(255))
    is_online_bookable = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='room_type', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'name': self.name,
            'description': self.description,
            'base_price': float(self.base_price) if self.base_price else 0,
            'extra_guest_price': float(self.extra_guest_price) if self.extra_guest_price else 0,
            'max_occupancy': self.max_occupancy,
            'total_floors': self.total_floors,
            'bed_type': self.bed_type,
            'view_type': self.view_type,
            'image_url': self.image_url,
            'is_online_bookable': self.is_online_bookable,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
