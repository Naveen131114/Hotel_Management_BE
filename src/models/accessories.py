from src import db
from datetime import datetime


class Accessory(db.Model):
    """Accessory Model"""
    __tablename__ = 'accessories'
    
    id = db.Column(db.Integer, primary_key=True)
    accessory_type_id = db.Column(db.Integer, db.ForeignKey('accessory_types.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    unit = db.Column(db.String(50))  # piece, set, bottle, kg
    unit_price = db.Column(db.Numeric(10, 2), default=0.00)
    is_chargeable = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room_accessories = db.relationship('RoomAccessory', backref='accessory', lazy=True, cascade='all, delete-orphan')
    booking_accessories = db.relationship('BookingAccessory', backref='accessory', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'accessory_type_id': self.accessory_type_id,
            'name': self.name,
            'description': self.description,
            'unit': self.unit,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'is_chargeable': self.is_chargeable,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
