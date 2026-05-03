from src import db
from datetime import datetime


class RoomType(db.Model):
    """Room Type Model"""
    __tablename__ = 'room_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    max_occupancy = db.Column(db.Integer, default=2)
    total_floors = db.Column(db.Integer, default=1)
    bed_type = db.Column(db.String(50))  # single, double, king, twin
    view_type = db.Column(db.String(50))  # sea, city, garden, pool
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='room_type', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'base_price': float(self.base_price) if self.base_price else 0,
            'max_occupancy': self.max_occupancy,
            'total_floors': self.total_floors,
            'bed_type': self.bed_type,
            'view_type': self.view_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
