from src import db
from datetime import datetime


class MaintenanceLog(db.Model):
    """Maintenance Log Model"""
    __tablename__ = 'maintenance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'))
    issue_type = db.Column(db.String(100))  # plumbing, electrical, AC, cleaning
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='reported')  # reported, in_progress, resolved
    started_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'worker_id': self.worker_id,
            'issue_type': self.issue_type,
            'description': self.description,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
