from src import db
from datetime import datetime


class Branch(db.Model):
    """Branch Model - a physical property belonging to a business (tenant)"""
    __tablename__ = 'branches'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(150))
    gst_number = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rooms = db.relationship('Room', backref='branch', lazy=True)
    staff_links = db.relationship('StaffBranch', cascade='all, delete-orphan', lazy=True, overlaps="allowed_branches,staff_users")

    __table_args__ = (
        db.UniqueConstraint('business_id', 'name', name='unique_business_branch_name'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'city': self.city,
            'phone': self.phone,
            'email': self.email,
            'gst_number': self.gst_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
