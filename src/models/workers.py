from src import db
from datetime import datetime


class Worker(db.Model):
    """Worker Model"""
    __tablename__ = 'workers'
    
    id = db.Column(db.Integer, primary_key=True)
    worker_type_id = db.Column(db.Integer, db.ForeignKey('worker_types.id'), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True)
    phone = db.Column(db.String(20))
    national_id = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')  # active, inactive, on_leave
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    room_records = db.relationship('RoomRecord', backref='assigned_worker', lazy=True)
    maintenance_logs = db.relationship('MaintenanceLog', backref='assigned_worker', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'worker_type_id': self.worker_type_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'national_id': self.national_id,
            'status': self.status,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
