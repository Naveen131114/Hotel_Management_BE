from src import db
from datetime import datetime


class WorkerType(db.Model):
    """Worker Type Model"""
    __tablename__ = 'worker_types'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)  # receptionist, housekeeping, manager
    description = db.Column(db.Text)
    base_salary = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    workers = db.relationship('Worker', backref='worker_type', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'base_salary': float(self.base_salary) if self.base_salary else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
