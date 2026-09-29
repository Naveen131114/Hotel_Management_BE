from src import db
from datetime import datetime


class UpiAccount(db.Model):
    """UPI Account Model - business UPI accounts selectable during payments"""
    __tablename__ = 'upi_accounts'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    upi_name = db.Column(db.String(150), nullable=False)
    upi_id = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(20))
    qr_code_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payments = db.relationship('Payment', backref='upi_account', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'upi_name': self.upi_name,
            'upi_id': self.upi_id,
            'phone_number': self.phone_number,
            'qr_code_url': self.qr_code_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
