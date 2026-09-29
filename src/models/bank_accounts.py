from src import db
from datetime import datetime


class BankAccount(db.Model):
    """Bank Account Model - business bank accounts selectable during payments"""
    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    bank_name = db.Column(db.String(150), nullable=False)
    account_holder_name = db.Column(db.String(150), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    ifsc_code = db.Column(db.String(30))
    branch_name = db.Column(db.String(150))
    account_type = db.Column(db.String(30), default='current')  # savings, current
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payments = db.relationship('Payment', backref='bank_account', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'bank_name': self.bank_name,
            'account_holder_name': self.account_holder_name,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'ifsc_code': self.ifsc_code,
            'branch_name': self.branch_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
