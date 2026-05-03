from src import db
from datetime import datetime


class Review(db.Model):
    """Review Model"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    room_record_id = db.Column(db.Integer, db.ForeignKey('room_records.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    cleanliness_rating = db.Column(db.Integer)  # 1 to 5
    staff_rating = db.Column(db.Integer)  # 1 to 5
    value_rating = db.Column(db.Integer)  # 1 to 5
    comment = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_record_id': self.room_record_id,
            'user_id': self.user_id,
            'room_id': self.room_id,
            'rating': self.rating,
            'cleanliness_rating': self.cleanliness_rating,
            'staff_rating': self.staff_rating,
            'value_rating': self.value_rating,
            'comment': self.comment,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
