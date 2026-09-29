from src import db
from datetime import datetime


class ActivityLog(db.Model):
    """Activity Log Model - audit trail for important operations"""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    user_id = db.Column(db.Integer)
    user_name = db.Column(db.String(150))
    action = db.Column(db.String(50), index=True)  # create, update, check_in, payment ...
    module = db.Column(db.String(50), index=True)  # bookings, rooms, staff ...
    record_id = db.Column(db.Integer)
    record_ref = db.Column(db.String(100))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'branch_name': self.branch.name if self.branch else None,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'action': self.action,
            'module': self.module,
            'record_id': self.record_id,
            'record_ref': self.record_ref,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
