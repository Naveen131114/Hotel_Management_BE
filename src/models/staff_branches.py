from src import db
from datetime import datetime


class StaffBranch(db.Model):
    """Staff Branch Model - which branches a staff login may access"""
    __tablename__ = 'staff_branches'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships with explicit backrefs and overlaps declared
    user = db.relationship('User', foreign_keys=[user_id], overlaps="allowed_branches,staff_users,staff_branch_links")
    branch = db.relationship('Branch', foreign_keys=[branch_id], overlaps="allowed_branches,staff_users,staff_links")

    __table_args__ = (
        db.UniqueConstraint('user_id', 'branch_id', name='unique_staff_branch'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'branch_id': self.branch_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

