from src import db
from datetime import datetime


class Room(db.Model):
    """Room Model"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_type_id = db.Column(db.Integer, db.ForeignKey('room_types.id'), nullable=False)
    # ── Multi-tenant / branch fields (added for the SaaS product) ──
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    room_number = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(100))
    floor = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    base_price = db.Column(db.Numeric(10, 2))
    extra_guest_price = db.Column(db.Numeric(10, 2), default=0.00)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    is_online_bookable = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance, reserved, blocked
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room_accessories = db.relationship('RoomAccessory', backref='room', lazy=True, cascade='all, delete-orphan')
    room_records = db.relationship('RoomRecord', backref='room', lazy=True)
    maintenance_logs = db.relationship('MaintenanceLog', backref='room', lazy=True, cascade='all, delete-orphan')

    # A room number only needs to be unique inside its branch (multi-tenant safe)
    __table_args__ = (
        db.UniqueConstraint('branch_id', 'room_number', name='unique_branch_room_number'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_type_id': self.room_type_id,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'branch_name': self.branch.name if self.branch else None,
            'room_number': self.room_number,
            'name': self.name,
            'floor': self.floor,
            'capacity': self.capacity,
            'base_price': float(self.base_price) if self.base_price else 0,
            'extra_guest_price': float(self.extra_guest_price) if self.extra_guest_price else 0,
            'description': self.description,
            'image_url': self.image_url,
            'is_online_bookable': self.is_online_bookable,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
