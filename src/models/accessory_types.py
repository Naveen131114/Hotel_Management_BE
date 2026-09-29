from src import db
from datetime import datetime


class AccessoryType(db.Model):
    """Accessory Type Model"""
    __tablename__ = 'accessory_types'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    name = db.Column(db.String(100), nullable=False)  # electronics, furniture, linen, minibar
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    accessories = db.relationship('Accessory', backref='accessory_type', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_id': self.business_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
