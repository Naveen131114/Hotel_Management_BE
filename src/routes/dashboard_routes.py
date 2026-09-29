from datetime import date, datetime, timedelta

from flask import Blueprint, request

from src import db
from src.models.rooms import Room
from src.models.room_records import RoomRecord
from src.models.branches import Branch
from src.services import booking_service, subscription_service
from src.utils import (
    success_response, error_response, auth_required, require_permission,
    tenant_scope, get_current_user, current_business_id, allowed_branch_ids,
)
from src.utils.constants import ROOM_AVAILABLE, ROOM_OCCUPIED

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


def _scoped_bookings():
    return tenant_scope(RoomRecord, RoomRecord.query.filter(RoomRecord.is_deleted.is_(False)))


def _scoped_rooms():
    return tenant_scope(Room, Room.query)


@bp.route('/summary', methods=['GET'])
@auth_required()
@require_permission('view')
def summary():
    """Owner + staff dashboard: today's operations, occupancy, collection, dues.

    The payload is always scoped to the user's tenant, allowed branches and
    subscription state, so a staff member can only see what they may access.
    """
    try:
        today = date.today()
        bookings_query = _scoped_bookings()
        rooms_query = _scoped_rooms()

        check_ins_today = bookings_query.filter(
            RoomRecord.check_in_date == today,
            RoomRecord.booking_status.in_(('pending', 'confirmed'))
        ).count()
        check_outs_today = bookings_query.filter(
            RoomRecord.check_out_date <= today,
            RoomRecord.booking_status == 'checked_in'
        ).count()
        today_bookings = bookings_query.filter(
            RoomRecord.created_at >= datetime.combine(today, datetime.min.time())
        ).count()
        upcoming = bookings_query.filter(
            RoomRecord.check_in_date > today,
            RoomRecord.booking_status.in_(('pending', 'confirmed'))
        ).count()

        rooms = rooms_query.all()
        occupied = len([room for room in rooms if room.status == ROOM_OCCUPIED])
        available = len([room for room in rooms if room.status == ROOM_AVAILABLE])
        maintenance = len([room for room in rooms if room.status == 'maintenance'])

        reserved = bookings_query.filter(
            RoomRecord.check_in_date > today,
            RoomRecord.booking_status.in_(('pending', 'confirmed'))
        ).with_entities(RoomRecord.room_id).distinct().count()

        # Payments collected today (uses the same tenant/branch scope as bookings)
        payments_query = bookings_query.filter(
            RoomRecord.id.in_(
                db.session.query(RoomRecord.id).filter(
                    RoomRecord.is_deleted.is_(False)
                )
            )
        )
        collection_today = 0.0
        pending_amount = 0.0
        for booking in payments_query.all():
            for payment in booking.payments:
                if payment.status != 'completed':
                    continue
                if payment.paid_at and payment.paid_at.date() == today:
                    collection_today += float(payment.amount or 0) * (-1 if payment.payment_type == 'refund' else 1)
            if booking.booking_status in ('pending', 'confirmed', 'checked_in'):
                pending_amount += float(booking.balance_amount or 0)

        from src.models.payments import Payment
        payment_scope = tenant_scope(Payment, Payment.query).filter(Payment.status == 'completed')
        data = {
            'date': today.isoformat(),
            'check_ins_today': check_ins_today,
            'check_outs_today': check_outs_today,
            'todays_bookings': today_bookings,
            'upcoming_bookings': upcoming,
            'available_rooms': available,
            'occupied_rooms': occupied,
            'reserved_rooms': reserved,
            'maintenance_rooms': maintenance,
            'total_rooms': len(rooms),
            'collection_today': round(collection_today, 2),
            'pending_amount': round(pending_amount, 2),
            'collection_all_time': round(sum(
                float(p.amount or 0) * (-1 if p.payment_type == 'refund' else 1)
                for p in payment_scope.all()
            ), 2),
            'branches': [branch.to_dict() for branch in
                         tenant_scope(Branch, Branch.query).order_by(Branch.name.asc()).all()]
            if allowed_branch_ids() is None else [],
            'subscription': subscription_service.limit_status(current_business_id())
            if current_business_id() else None
        }
        return success_response('Dashboard fetched successfully', data, status_code=200)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)


@bp.route('/room-board', methods=['GET'])
@auth_required()
@require_permission('view')
def room_board():
    """Room board for the selected date range (visual availability states)"""
    try:
        from src.services import availability_service
        check_in = availability_service.parse_date(request.args.get('date') or date.today().isoformat(), 'Date')
        check_out = check_in + timedelta(days=1)
        rooms = availability_service.available_rooms(
            current_business_id(), check_in, check_out,
            branch_id=request.args.get('branch_id') if request.args.get('branch_id') else None,
            allowed_branch_ids=allowed_branch_ids()
        )
        return success_response('Room board fetched successfully', rooms, status_code=200)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'Error: {str(e)}', 500)
