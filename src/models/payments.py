from src import db
from datetime import datetime


class Payment(db.Model):
    """Payment Model"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    room_record_id = db.Column(db.Integer, db.ForeignKey('room_records.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(50))  # cash, bank, upi, card, other
    status = db.Column(db.String(20), default='completed')  # pending, completed, failed, refunded
    transaction_ref = db.Column(db.String(200))
    # ── Multi-tenant / payment routing fields ──
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'))
    upi_account_id = db.Column(db.Integer, db.ForeignKey('upi_accounts.id'))
    payment_type = db.Column(db.String(20), default='advance')  # advance, final, additional, refund
    received_by = db.Column(db.Integer)
    received_by_name = db.Column(db.String(150))
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
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'bank_account_id': self.bank_account_id,
            'bank_account_name': self.bank_account.bank_name if self.bank_account else None,
            'upi_account_id': self.upi_account_id,
            'upi_account_name': self.upi_account.upi_name if self.upi_account else None,
            'payment_type': self.payment_type,
            'received_by': self.received_by,
            'received_by_name': self.received_by_name,
            'notes': self.notes,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }
