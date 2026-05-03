from src import db
from datetime import datetime


class AccessoryType(db.Model):
    """Accessory Type Model"""
    __tablename__ = 'accessory_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # electronics, furniture, linen, minibar
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accessories = db.relationship('Accessory', backref='accessory_type', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
