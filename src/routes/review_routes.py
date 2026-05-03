from flask import Blueprint, request
from sqlalchemy import func
from src import db
from src.models.reviews import Review
from src.utils import success_response, error_response, token_required

bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')


@bp.route('', methods=['GET'])
def get_all_reviews():
    """Get all reviews with optional filters"""
    try:
        query = Review.query
        
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('user_id'):
            query = query.filter_by(user_id=request.args.get('user_id'))
        if request.args.get('is_published'):
            is_published = request.args.get('is_published').lower() == 'true'
            query = query.filter_by(is_published=is_published)
        
        reviews = query.all()
        data = [review.to_dict() for review in reviews]
        return success_response('Reviews fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
def get_review(id):
    """Get review by ID"""
    try:
        review = Review.query.get(id)
        if not review:
            return error_response('Review not found', 404)
        return success_response('Review fetched successfully', review.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/room/<int:room_id>/average-rating', methods=['GET'])
def get_average_rating(room_id):
    """Get average ratings for a room"""
    try:
        reviews = Review.query.filter_by(room_id=room_id, is_published=True).all()
        
        if not reviews:
            return success_response('No reviews found', {
                'room_id': room_id,
                'average_rating': 0,
                'cleanliness_rating': 0,
                'staff_rating': 0,
                'value_rating': 0,
                'total_reviews': 0
            }, status_code=200)
        
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        avg_cleanliness = sum(r.cleanliness_rating for r in reviews if r.cleanliness_rating) / len([r for r in reviews if r.cleanliness_rating]) if any(r.cleanliness_rating for r in reviews) else 0
        avg_staff = sum(r.staff_rating for r in reviews if r.staff_rating) / len([r for r in reviews if r.staff_rating]) if any(r.staff_rating for r in reviews) else 0
        avg_value = sum(r.value_rating for r in reviews if r.value_rating) / len([r for r in reviews if r.value_rating]) if any(r.value_rating for r in reviews) else 0
        
        data = {
            'room_id': room_id,
            'average_rating': round(avg_rating, 2),
            'cleanliness_rating': round(avg_cleanliness, 2),
            'staff_rating': round(avg_staff, 2),
            'value_rating': round(avg_value, 2),
            'total_reviews': len(reviews)
        }
        
        return success_response('Average ratings fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@token_required
def create_review():
    """Create a new review (protected)"""
    try:
        data = request.get_json()
        
        required_fields = ['room_record_id', 'user_id', 'room_id', 'rating']
        if not all(field in data for field in required_fields):
            return error_response('Missing required fields', 400)
        
        review = Review(
            room_record_id=data['room_record_id'],
            user_id=data['user_id'],
            room_id=data['room_id'],
            rating=data['rating'],
            cleanliness_rating=data.get('cleanliness_rating'),
            staff_rating=data.get('staff_rating'),
            value_rating=data.get('value_rating'),
            comment=data.get('comment'),
            is_published=data.get('is_published', True)
        )
        
        db.session.add(review)
        db.session.commit()
        
        return success_response('Review created successfully', review.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_review(id):
    """Update review (protected)"""
    try:
        review = Review.query.get(id)
        if not review:
            return error_response('Review not found', 404)
        
        data = request.get_json()
        
        if 'rating' in data:
            review.rating = data['rating']
        if 'cleanliness_rating' in data:
            review.cleanliness_rating = data['cleanliness_rating']
        if 'staff_rating' in data:
            review.staff_rating = data['staff_rating']
        if 'value_rating' in data:
            review.value_rating = data['value_rating']
        if 'comment' in data:
            review.comment = data['comment']
        if 'is_published' in data:
            review.is_published = data['is_published']
        
        db.session.commit()
        
        return success_response('Review updated successfully', review.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@token_required
def delete_review(id):
    """Delete review (protected)"""
    try:
        review = Review.query.get(id)
        if not review:
            return error_response('Review not found', 404)
        
        db.session.delete(review)
        db.session.commit()
        
        return success_response('Review deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
