"""Room availability rules - ONE implementation for every booking channel.

Date handling uses half-open intervals [check-in, check-out): a room occupied
until 12-Oct can be booked again from 12-Oct (checkout-date reuse), while an
overlap such as 10-Oct -> 15-Oct vs 12-Oct -> 14-Oct is rejected.

The same module is used by public (online) bookings, phone/walk-in bookings and
the admin panel, so no channel can bypass the rules.
"""
from datetime import date, datetime

from src import db
from src.models.rooms import Room
from src.models.room_records import RoomRecord
from src.utils.constants import BLOCKING_BOOKING_STATUSES, ROOM_MAINTENANCE, ROOM_BLOCKED, ROOM_OCCUPIED

DATE_FORMAT = '%Y-%m-%d'


def parse_date(value, field_name='date'):
    """Parse YYYY-MM-DD / ISO datetime / date into a date object"""
    if value is None or value == '':
        raise ValueError(f'{field_name} is required')
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f'{field_name} must be in YYYY-MM-DD format')


def validate_range(check_in, check_out):
    """Return an error message when the requested range is invalid"""
    if check_in >= check_out:
        return 'Check-out date must be after the check-in date'
    return None


def nights_between(check_in, check_out):
    return max((check_out - check_in).days, 0)


def overlapping_bookings_query(room_id, check_in, check_out, exclude_booking_id=None,
                               business_id=None, statuses=BLOCKING_BOOKING_STATUSES):
    """Live bookings of `room_id` whose stay range overlaps [check_in, check_out)

    Overlap rule: existing.check_in_date < requested.check_out_date
                  AND existing.check_out_date > requested.check_in_date
    """
    query = RoomRecord.query.filter(
        RoomRecord.room_id == room_id,
        RoomRecord.is_deleted.is_(False),
        RoomRecord.booking_status.in_(statuses),
        RoomRecord.check_in_date < check_out,
        RoomRecord.check_out_date > check_in,
    )
    if business_id is not None:
        query = query.filter(RoomRecord.business_id == business_id)
    if exclude_booking_id is not None:
        query = query.filter(RoomRecord.id != exclude_booking_id)
    return query


def is_room_available(room, check_in, check_out, exclude_booking_id=None, lock_room=False):
    """Return (available, reason, blocking_booking)

    `lock_room=True` takes a row lock on the room so concurrent requests are
    serialised (prevents double booking under load).
    """
    if lock_room:
        locked = Room.query.filter(Room.id == room.id).with_for_update().first()
        if locked is not None:
            room = locked

    if room.status in (ROOM_MAINTENANCE, ROOM_BLOCKED):
        return False, f'Room {room.room_number} is not bookable ({room.status})', None

    today = date.today()
    if room.status == ROOM_OCCUPIED and check_in <= today < check_out:
        return False, f'Room {room.room_number} is currently occupied', None

    conflict = overlapping_bookings_query(
        room.id, check_in, check_out,
        exclude_booking_id=exclude_booking_id,
        business_id=room.business_id
    ).order_by(RoomRecord.check_in_date.asc()).first()

    if conflict is not None:
        return False, (
            f'Room {room.room_number} is not available between '
            f'{conflict.check_in_date.isoformat()} and {conflict.check_out_date.isoformat()}'
        ), conflict

    return True, None, None


def room_availability(room, check_in, check_out, exclude_booking_id=None):
    """Availability payload for a single room (used by admin + public APIs)"""
    available, reason, conflict = is_room_available(
        room, check_in, check_out, exclude_booking_id=exclude_booking_id
    )
    payload = room.to_dict()
    payload.update({
        'is_available': available,
        'availability_reason': reason,
        'blocking_booking_id': conflict.id if conflict else None,
        'blocking_booking_number': conflict.booking_number if conflict else None,
        'requested_check_in': check_in.isoformat(),
        'requested_check_out': check_out.isoformat(),
        'nights': nights_between(check_in, check_out)
    })
    return payload


def available_rooms(business_id, check_in, check_out, branch_id=None, room_type_id=None,
                    guests=None, online_only=False, allowed_branch_ids=None):
    """List the rooms of a tenant for a date range with their availability state"""
    query = Room.query.filter(
        Room.business_id == business_id,
        ~Room.status.in_((ROOM_MAINTENANCE, ROOM_BLOCKED)),
    )
    if branch_id is not None:
        query = query.filter(Room.branch_id == branch_id)
    elif allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return []
        query = query.filter(Room.branch_id.in_(allowed_branch_ids))
    if room_type_id is not None:
        query = query.filter(Room.room_type_id == room_type_id)
    if online_only:
        query = query.filter(Room.is_online_bookable.is_(True))
    if guests:
        query = query.filter(Room.capacity >= int(guests))

    return [
        room_availability(room, check_in, check_out)
        for room in query.order_by(Room.room_number.asc()).all()
    ]


def availability_summary(business_id, check_in, check_out, branch_id=None, room_type_id=None,
                         guests=None, online_only=False, allowed_branch_ids=None):
    """Availability digest used by the public booking page (grouped by room type)"""
    rooms = available_rooms(
        business_id, check_in, check_out,
        branch_id=branch_id, room_type_id=room_type_id,
        guests=guests, online_only=online_only, allowed_branch_ids=allowed_branch_ids
    )
    available = [room for room in rooms if room['is_available']]

    grouped = {}
    for room in available:
        key = room['room_type_id']
        entry = grouped.setdefault(key, {
            'room_type_id': key,
            'room_type_name': room.get('room_type_name'),
            'price': room['base_price'] or 0,
            'available_rooms': 0,
            'max_capacity': 0,
            'image_url': room.get('image_url')
        })
        entry['available_rooms'] += 1
        entry['max_capacity'] = max(entry['max_capacity'], room['capacity'] or 0)
        if not entry['price']:
            entry['price'] = room['base_price'] or 0

    return {
        'check_in': check_in.isoformat(),
        'check_out': check_out.isoformat(),
        'nights': nights_between(check_in, check_out),
        'total_rooms': len(rooms),
        'available_rooms': len(available),
        'room_types': sorted(grouped.values(), key=lambda item: item['price'] or 0),
        'rooms': rooms
    }

    return True, None, None
