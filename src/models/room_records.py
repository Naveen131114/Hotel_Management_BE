from src import db
from datetime import datetime

from src.utils.constants import BLOCKING_BOOKING_STATUSES


class RoomRecord(db.Model):
    """Room Record (Booking) Model

    Reused by every booking channel (walk-in, phone, offline, online) so the
    availability/booking rules live in one place: `src/services/booking_service.py`.
    """
    __tablename__ = 'room_records'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    # ── Multi-tenant / branch fields ──
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), index=True)
    booking_number = db.Column(db.String(40), unique=True, index=True)
    booking_source = db.Column(db.String(20), default='offline', index=True)  # walk_in, phone, offline, online
    # Guest details are copied onto the booking so walk-in/phone guests are kept
    # intact even if the guest account is later edited.
    guest_name = db.Column(db.String(150), index=True)
    guest_phone = db.Column(db.String(20), index=True)
    guest_email = db.Column(db.String(150))
    check_in_date = db.Column(db.Date, nullable=False, index=True)
    check_out_date = db.Column(db.Date, nullable=False, index=True)
    actual_check_in = db.Column(db.DateTime)
    actual_check_out = db.Column(db.DateTime)
    num_guests = db.Column(db.Integer, default=1)
    adults = db.Column(db.Integer, default=1)
    children = db.Column(db.Integer, default=0)
    # ── Charges / bill breakdown ──
    room_charges = db.Column(db.Numeric(10, 2), default=0.00)
    extra_charges = db.Column(db.Numeric(10, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00)
    tax_percent = db.Column(db.Numeric(5, 2), default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00)
    advance_amount = db.Column(db.Numeric(10, 2), default=0.00)
    amount_paid = db.Column(db.Numeric(10, 2), default=0.00)
    received_amount = db.Column(db.Numeric(10, 2), default=0.00)
    balance_amount = db.Column(db.Numeric(10, 2), default=0.00)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid, refunded
    booking_status = db.Column(db.String(20), default='confirmed')  # pending, confirmed, checked_in, checked_out, cancelled, no_show
    payment_method = db.Column(db.String(50))  # cash, bank, upi, card, other
    bill_number = db.Column(db.String(40))
    special_requests = db.Column(db.Text)
    checked_in_by = db.Column(db.Integer)
    checked_in_by_name = db.Column(db.String(150))
    checked_out_by = db.Column(db.Integer)
    checked_out_by_name = db.Column(db.String(150))
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer)
    cancel_reason = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    created_by_name = db.Column(db.String(150))
    # Soft delete marker: booking history is preserved instead of being removed
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    payments = db.relationship('Payment', backref='room_record', lazy=True, cascade='all, delete-orphan')
    booking_accessories = db.relationship('BookingAccessory', backref='room_record', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='booking', lazy=True, cascade='all, delete-orphan')
    
    # ── Domain helpers ─────────────────────────────────────────────────
    def nights(self):
        if not self.check_in_date or not self.check_out_date:
            return 0
        return max((self.check_out_date - self.check_in_date).days, 0)

    def blocks_availability(self):
        """Only live bookings block a room (cancelled / no-show / deleted do not)"""
        return (
            self.booking_status in BLOCKING_BOOKING_STATUSES
            and not self.is_deleted
        )

    def to_dict(self, include_payments=False):
        room = self.room
        branch = self.branch
        data = {
            'id': self.id,
            'booking_number': self.booking_number,
            'room_id': self.room_id,
            'room_number': room.room_number if room else None,
            'room_type_id': self.room_type_id,
            'room_type_name': room.room_type.name if room and room.room_type else None,
            'branch_id': self.branch_id,
            'branch_name': branch.name if branch else None,
            'business_id': self.business_id,
            'user_id': self.user_id,
            'guest_name': self.guest_name or (f"{self.guest.first_name} {self.guest.last_name}".strip() if self.guest else None),
            'guest_phone': self.guest_phone or (self.guest.phone if self.guest else None),
            'guest_email': self.guest_email or (self.guest.email if self.guest else None),
            'worker_id': self.worker_id,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'actual_check_in': self.actual_check_in.isoformat() if self.actual_check_in else None,
            'actual_check_out': self.actual_check_out.isoformat() if self.actual_check_out else None,
            'nights': self.nights(),
            'num_guests': self.num_guests,
            'adults': self.adults,
            'children': self.children,
            'booking_source': self.booking_source,
            'room_charges': float(self.room_charges or 0),
            'extra_charges': float(self.extra_charges or 0),
            'discount_amount': float(self.discount_amount or 0),
            'tax_percent': float(self.tax_percent or 0),
            'tax_amount': float(self.tax_amount or 0),
            'total_price': float(self.total_price) if self.total_price else 0,
            'total_amount': float(self.total_amount or self.total_price or 0),
            'advance_amount': float(self.advance_amount or 0),
            'amount_paid': float(self.amount_paid or 0),
            'received_amount': float(self.received_amount or 0),
            'balance_amount': float(self.balance_amount or 0),
            'payment_status': self.payment_status,
            'booking_status': self.booking_status,
            'payment_method': self.payment_method,
            'bill_number': self.bill_number,
            'special_requests': self.special_requests,
            'checked_in_by_name': self.checked_in_by_name,
            'checked_out_by_name': self.checked_out_by_name,
            'created_by_name': self.created_by_name,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancel_reason': self.cancel_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_payments:
            data['payments'] = [payment.to_dict() for payment in self.payments]
        return data
