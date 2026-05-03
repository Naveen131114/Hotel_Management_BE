from src import db
from datetime import datetime


class RoomAccessory(db.Model):
    """Room Accessory Model"""
    __tablename__ = 'room_accessories'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    accessory_id = db.Column(db.Integer, db.ForeignKey('accessories.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    condition = db.Column(db.String(20), default='good')  # good, damaged, missing
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('room_id', 'accessory_id', name='unique_room_accessory'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'accessory_id': self.accessory_id,
            'quantity': self.quantity,
            'condition': self.condition,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
