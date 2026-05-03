from src import db
from datetime import datetime


class Payment(db.Model):
    """Payment Model"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    room_record_id = db.Column(db.Integer, db.ForeignKey('room_records.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(50))  # cash, card, online, bank_transfer
    status = db.Column(db.String(20), default='completed')  # pending, completed, failed, refunded
    transaction_ref = db.Column(db.String(200))
    notes = db.Column(db.Text)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_record_id': self.room_record_id,
            'amount': float(self.amount) if self.amount else 0,
            'method': self.method,
            'status': self.status,
            'transaction_ref': self.transaction_ref,
            'notes': self.notes,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }
