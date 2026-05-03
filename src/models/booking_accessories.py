from src import db
from datetime import datetime


class BookingAccessory(db.Model):
    """Booking Accessory Model"""
    __tablename__ = 'booking_accessories'
    
    id = db.Column(db.Integer, primary_key=True)
    room_record_id = db.Column(db.Integer, db.ForeignKey('room_records.id'), nullable=False)
    accessory_id = db.Column(db.Integer, db.ForeignKey('accessories.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_at_booking = db.Column(db.Numeric(10, 2), default=0.00)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_record_id': self.room_record_id,
            'accessory_id': self.accessory_id,
            'quantity': self.quantity,
            'price_at_booking': float(self.price_at_booking) if self.price_at_booking else 0,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }
