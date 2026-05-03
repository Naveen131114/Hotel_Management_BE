from . import auth_routes
from . import room_type_routes
from . import room_routes
from . import worker_type_routes
from . import worker_routes
from . import user_routes
from . import accessory_type_routes
from . import accessory_routes
from . import room_accessory_routes
from . import room_record_routes
from . import booking_accessory_routes
from . import payment_routes
from . import review_routes
from . import maintenance_log_routes

__all__ = [
    'auth_routes', 'room_type_routes', 'room_routes',
    'worker_type_routes', 'worker_routes', 'user_routes',
    'accessory_type_routes', 'accessory_routes', 'room_accessory_routes',
    'room_record_routes', 'booking_accessory_routes', 'payment_routes',
    'review_routes', 'maintenance_log_routes'
]
