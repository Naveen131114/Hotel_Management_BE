from src import db
from datetime import datetime


class Room(db.Model):
    """Room Model"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), nullable=False)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance, reserved
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room_accessories = db.relationship('RoomAccessory', backref='room', lazy=True, cascade='all, delete-orphan')
    room_records = db.relationship('RoomRecord', backref='room', lazy=True, cascade='all, delete-orphan')
    maintenance_logs = db.relationship('MaintenanceLog', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_type_id': self.room_type_id,
            'room_number': self.room_number,
            'floor': self.floor,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
