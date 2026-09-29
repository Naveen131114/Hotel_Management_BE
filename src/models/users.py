from src import db
from datetime import datetime
import bcrypt


class User(db.Model):
    """User Model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255))
    id_type = db.Column(db.String(50))  # passport, national_id, driving_license
    id_number = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    address = db.Column(db.Text)
    # ── Multi-tenant / panel login fields (added for the SaaS product) ──
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), index=True)
    role = db.Column(db.String(20), default='guest', index=True)  # super_admin, owner, staff, guest
    permission_level = db.Column(db.String(20), default='full')  # view_only, edit, full
    designation = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer)
    updated_by = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    room_records = db.relationship('RoomRecord', backref='guest', lazy=True, foreign_keys='RoomRecord.user_id')
    reviews = db.relationship('Review', backref='reviewer', lazy=True, cascade='all, delete-orphan')
    allowed_branches = db.relationship(
        'Branch',
        secondary='staff_branches',
        lazy='selectin',
        backref=db.backref('staff_users', lazy=True)
    )

    # ── Role / permission helpers ───────────────────────────────────────
    def is_super_admin(self):
        return self.role == 'super_admin'

    def is_owner(self):
        return self.role == 'owner'

    def is_staff(self):
        return self.role == 'staff'

    def is_guest(self):
        return self.role == 'guest'

    def allowed_branch_ids(self):
        return [branch.id for branch in self.allowed_branches]

    def can(self, action):
        """Check a permission action (view/create/edit/delete) for this user"""
        from src.utils.constants import PERMISSION_ACTIONS, PERMISSION_FULL, ROLE_OWNER, ROLE_SUPER_ADMIN
        if self.role in (ROLE_SUPER_ADMIN, ROLE_OWNER):
            return True
        level = self.permission_level or PERMISSION_FULL
        return action in PERMISSION_ACTIONS.get(level, PERMISSION_ACTIONS[PERMISSION_FULL])
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    def to_dict(self):
        """Safe representation - never exposes password_hash"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name or ''} {self.last_name or ''}".strip(),
            'email': self.email,
            'phone': self.phone,
            'id_type': self.id_type,
            'id_number': self.id_number,
            'nationality': self.nationality,
            'address': self.address,
            'business_id': self.business_id,
            'branch_id': self.branch_id,
            'role': self.role,
            'permission_level': self.permission_level,
            'designation': self.designation,
            'is_active': self.is_active,
            'branch_ids': self.allowed_branch_ids(),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
