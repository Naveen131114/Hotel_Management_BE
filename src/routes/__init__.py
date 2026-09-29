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
from . import branch_routes
from . import staff_routes
from . import business_routes
from . import subscription_plan_routes
from . import subscription_routes
from . import super_admin_routes
from . import booking_routes
from . import bank_account_routes
from . import upi_account_routes
from . import activity_log_routes
from . import dashboard_routes
from . import public_routes

__all__ = [
    'auth_routes', 'room_type_routes', 'room_routes',
    'worker_type_routes', 'worker_routes', 'user_routes',
    'accessory_type_routes', 'accessory_routes', 'room_accessory_routes',
    'room_record_routes', 'booking_accessory_routes', 'payment_routes',
    'review_routes', 'maintenance_log_routes',
    'branch_routes', 'staff_routes', 'business_routes',
    'subscription_plan_routes', 'subscription_routes', 'super_admin_routes',
    'booking_routes', 'bank_account_routes', 'upi_account_routes',
    'activity_log_routes', 'dashboard_routes', 'public_routes'
]
