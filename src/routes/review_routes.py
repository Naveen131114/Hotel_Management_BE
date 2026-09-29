from flask import Blueprint, request

from src import db
from src.models.reviews import Review
from src.models.rooms import Room
from src.models.room_records import RoomRecord
from src.utils import (
    success_response, error_response, auth_required, require_permission, tenant_scope,
    log_activity, get_current_user,
)
from src.utils.constants import ACTIVITY_CREATE, ACTIVITY_DELETE, ACTIVITY_UPDATE

bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')


def _scoped(query):
    """Reviews inherit the tenant scope through their room"""
    return query.filter(Review.room_id.in_(
        tenant_scope(Room, Room.query).with_entities(Room.id)
    ))


@bp.route('', methods=['GET'])
@auth_required()
@require_permission('view')
def get_all_reviews():
    """Get all reviews of the current hotel"""
    try:
        query = _scoped(Review.query)
        if request.args.get('room_id'):
            query = query.filter_by(room_id=request.args.get('room_id'))
        if request.args.get('is_published') in ('1', 'true'):
            query = query.filter(Review.is_published.is_(True))
        reviews = query.order_by(Review.created_at.desc()).all()
        return success_response('Reviews fetched successfully',
                                [review.to_dict() for review in reviews], status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['GET'])
@auth_required()
@require_permission('view')
def get_review(id):
    """Get a review by ID (tenant scoped)"""
    try:
        review = _scoped(Review.query).filter(Review.id == id).first()
        if not review:
            return error_response('Review not found', 404)
        return success_response('Review fetched successfully', review.to_dict(), status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('', methods=['POST'])
@auth_required()
@require_permission('create')
def create_review():
    """Create a review for a booking of the current hotel"""
    try:
        data = request.get_json()
        required = ['room_record_id', 'rating']
        if not all(field in data for field in required):
            return error_response('room_record_id and rating are required', 400)

        booking = tenant_scope(RoomRecord, RoomRecord.query).filter(
            RoomRecord.id == data['room_record_id']
        ).first()
        if not booking:
            return error_response('Booking not found', 404)

        review = Review(
            room_record_id=booking.id,
            user_id=data.get('user_id') or booking.user_id,
            room_id=booking.room_id,
            rating=int(data['rating']),
            cleanliness_rating=data.get('cleanliness_rating'),
            staff_rating=data.get('staff_rating'),
            value_rating=data.get('value_rating'),
            comment=data.get('comment'),
            is_published=data.get('is_published', True)
        )
        db.session.add(review)
        db.session.commit()

        log_activity(ACTIVITY_CREATE, 'reviews', review.id, booking.booking_number,
                     f"Added review for booking {booking.booking_number}", branch_id=booking.branch_id)
        return success_response('Review created successfully', review.to_dict(), status_code=201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['PUT'])
@auth_required()
@require_permission('edit')
def update_review(id):
    """Update a review (moderation, publish/unpublish)"""
    try:
        review = _scoped(Review.query).filter(Review.id == id).first()
        if not review:
            return error_response('Review not found', 404)

        data = request.get_json()
        for field in ('rating', 'cleanliness_rating', 'staff_rating', 'value_rating',
                      'comment', 'is_published'):
            if field in data:
                setattr(review, field, data[field])
        db.session.commit()

        log_activity(ACTIVITY_UPDATE, 'reviews', review.id, None, f"Updated review #{review.id}")
        return success_response('Review updated successfully', review.to_dict(), status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/<int:id>', methods=['DELETE'])
@auth_required()
@require_permission('delete')
def delete_review(id):
    """Delete a review"""
    try:
        review = _scoped(Review.query).filter(Review.id == id).first()
        if not review:
            return error_response('Review not found', 404)

        db.session.delete(review)
        db.session.commit()

        log_activity(ACTIVITY_DELETE, 'reviews', id, None, f"Deleted review #{id}")
        return success_response('Review deleted successfully', status_code=200)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error: {str(e)}', 500)
