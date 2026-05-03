from src import db
from datetime import datetime


class RoomRecord(db.Model):
    """Room Record (Booking) Model"""
    __tablename__ = 'room_records'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    actual_check_in = db.Column(db.DateTime)
    actual_check_out = db.Column(db.DateTime)
    num_guests = db.Column(db.Integer, default=1)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0.00)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid, refunded
    booking_status = db.Column(db.String(20), default='confirmed')  # confirmed, checked_in, checked_out, cancelled, no_show
    payment_method = db.Column(db.String(50))  # cash, card, online, bank_transfer
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payments = db.relationship('Payment', backref='room_record', lazy=True, cascade='all, delete-orphan')
    booking_accessories = db.relationship('BookingAccessory', backref='room_record', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='booking', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'worker_id': self.worker_id,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'actual_check_in': self.actual_check_in.isoformat() if self.actual_check_in else None,
            'actual_check_out': self.actual_check_out.isoformat() if self.actual_check_out else None,
            'num_guests': self.num_guests,
            'total_price': float(self.total_price) if self.total_price else 0,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0,
            'payment_status': self.payment_status,
            'booking_status': self.booking_status,
            'payment_method': self.payment_method,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
