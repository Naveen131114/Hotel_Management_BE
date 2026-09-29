"""Shared constants for the multi-tenant Lodge/Hotel Management SaaS.

Keeping the enumerations in one module lets new limits/statuses/features be
added later without touching the models or the route layer.
"""

# ── Roles ────────────────────────────────────────────────────────────────
ROLE_SUPER_ADMIN = "super_admin"
ROLE_OWNER = "owner"
ROLE_STAFF = "staff"
ROLE_GUEST = "guest"

ROLES = (ROLE_SUPER_ADMIN, ROLE_OWNER, ROLE_STAFF, ROLE_GUEST)

# Roles that can log into the management panel
PANEL_ROLES = (ROLE_SUPER_ADMIN, ROLE_OWNER, ROLE_STAFF)

# ── Permissions (permission_level) ───────────────────────────────────────
PERMISSION_VIEW_ONLY = "view_only"
PERMISSION_EDIT = "edit"
PERMISSION_FULL = "full"

PERMISSION_LEVELS = (PERMISSION_VIEW_ONLY, PERMISSION_EDIT, PERMISSION_FULL)

PERMISSION_ACTIONS = {
    PERMISSION_VIEW_ONLY: ("view",),
    PERMISSION_EDIT: ("view", "create", "edit"),
    PERMISSION_FULL: ("view", "create", "edit", "delete"),
}

# ── Room status ──────────────────────────────────────────────────────────
ROOM_AVAILABLE = "available"
ROOM_RESERVED = "reserved"
ROOM_OCCUPIED = "occupied"
ROOM_MAINTENANCE = "maintenance"
ROOM_BLOCKED = "blocked"

ROOM_STATUSES = (
    ROOM_AVAILABLE, ROOM_RESERVED, ROOM_OCCUPIED, ROOM_MAINTENANCE, ROOM_BLOCKED,
)

# Room statuses that make a room un-bookable regardless of dates
UNBOOKABLE_ROOM_STATUSES = (ROOM_MAINTENANCE, ROOM_BLOCKED, ROOM_OCCUPIED)

# ── Booking status ───────────────────────────────────────────────────────
BOOKING_PENDING = "pending"
BOOKING_CONFIRMED = "confirmed"
BOOKING_CHECKED_IN = "checked_in"
BOOKING_CHECKED_OUT = "checked_out"
BOOKING_CANCELLED = "cancelled"
BOOKING_NO_SHOW = "no_show"

BOOKING_STATUSES = (
    BOOKING_PENDING, BOOKING_CONFIRMED, BOOKING_CHECKED_IN,
    BOOKING_CHECKED_OUT, BOOKING_CANCELLED, BOOKING_NO_SHOW,
)

# Only these statuses block a room's availability for a date range
BLOCKING_BOOKING_STATUSES = (BOOKING_PENDING, BOOKING_CONFIRMED, BOOKING_CHECKED_IN)

# ── Booking source ───────────────────────────────────────────────────────
SOURCE_WALK_IN = "walk_in"
SOURCE_PHONE = "phone"
SOURCE_OFFLINE = "offline"
SOURCE_ONLINE = "online"

BOOKING_SOURCES = (SOURCE_WALK_IN, SOURCE_PHONE, SOURCE_OFFLINE, SOURCE_ONLINE)

# ── Payment ──────────────────────────────────────────────────────────────
PAYMENT_CASH = "cash"
PAYMENT_BANK = "bank"
PAYMENT_UPI = "upi"
PAYMENT_CARD = "card"
PAYMENT_ONLINE = "online"
PAYMENT_OTHER = "other"

PAYMENT_METHODS = (
    PAYMENT_CASH, PAYMENT_BANK, PAYMENT_UPI, PAYMENT_CARD,
    PAYMENT_ONLINE, PAYMENT_OTHER,
)

PAYMENT_TYPE_ADVANCE = "advance"
PAYMENT_TYPE_FINAL = "final"
PAYMENT_TYPE_ADDITIONAL = "additional"
PAYMENT_TYPE_REFUND = "refund"

PAYMENT_TYPES = (
    PAYMENT_TYPE_ADVANCE, PAYMENT_TYPE_FINAL,
    PAYMENT_TYPE_ADDITIONAL, PAYMENT_TYPE_REFUND,
)

# Payment / booking payment_status values (kept compatible with legacy data)
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PARTIAL = "partial"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_REFUNDED = "refunded"

# ── Subscription ─────────────────────────────────────────────────────────
SUBSCRIPTION_PENDING = "pending"
SUBSCRIPTION_ACTIVE = "active"
SUBSCRIPTION_EXPIRED = "expired"
SUBSCRIPTION_REJECTED = "rejected"
SUBSCRIPTION_CANCELLED = "cancelled"

SUBSCRIPTION_STATUSES = (
    SUBSCRIPTION_PENDING, SUBSCRIPTION_ACTIVE, SUBSCRIPTION_EXPIRED,
    SUBSCRIPTION_REJECTED, SUBSCRIPTION_CANCELLED,
)

# Capabilities checked against the subscription
CAPABILITY_WRITE = "write"
CAPABILITY_CREATE_BRANCH = "create_branch"
CAPABILITY_CREATE_ROOM = "create_room"
CAPABILITY_CREATE_STAFF = "create_staff"

# ── Activity log ─────────────────────────────────────────────────────────
ACTIVITY_CREATE = "create"
ACTIVITY_UPDATE = "update"
ACTIVITY_DELETE = "delete"
ACTIVITY_VIEW = "view"
ACTIVITY_LOGIN = "login"
ACTIVITY_CHECK_IN = "check_in"
ACTIVITY_CHECK_OUT = "check_out"
ACTIVITY_PAYMENT = "payment"
ACTIVITY_APPROVE = "approve"
ACTIVITY_REJECT = "reject"
ACTIVITY_CANCEL = "cancel"

# ── Modules (used by permissions + activity log + FE menu) ───────────────
MODULE_BRANCHES = "branches"
MODULE_ROOMS = "rooms"
MODULE_ROOM_TYPES = "room_types"
MODULE_ACCESSORIES = "accessories"
MODULE_ACCESSORY_TYPES = "accessory_types"
MODULE_WORKERS = "workers"
MODULE_WORKER_TYPES = "worker_types"
MODULE_BANK_ACCOUNTS = "bank_accounts"
MODULE_UPI_ACCOUNTS = "upi_accounts"
MODULE_STAFF = "staff"
MODULE_BOOKINGS = "bookings"
MODULE_PAYMENTS = "payments"
MODULE_REPORTS = "reports"
MODULE_ACTIVITY_LOGS = "activity_logs"
MODULE_SUBSCRIPTION = "subscription"

# No hard-coded plan limits: these are only fallbacks used when a business has
# no active subscription at all (kept intentionally tiny so an active plan is
# always required for real usage).
DEFAULT_FALLBACK_LIMITS = {
    "max_staff": 1,
    "max_branches": 1,
    "max_rooms": 5,
}
