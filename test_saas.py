import unittest
from datetime import datetime, timedelta
from config import TestingConfig
from src import create_app, db
from src.models.businesses import Business
from src.models.branches import Branch
from src.models.room_types import RoomType
from src.models.rooms import Room
from src.models.users import User
from src.models.subscription_plans import SubscriptionPlan
from src.models.business_subscriptions import BusinessSubscription
from src.services import availability_service, booking_service, subscription_service
from src.utils.jwt_utils import encode_token


class SaasTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed plan
        self.plan = SubscriptionPlan(
            name='Standard',
            price=999.0,
            duration_days=30,
            max_staff=2,
            max_branches=2,
            max_rooms=5,
            is_active=True
        )
        db.session.add(self.plan)
        db.session.flush()

        # Seed business
        self.biz = Business(
            name='Grand Palace Resort',
            slug='grand-palace',
            email='owner@grandpalace.com',
            is_active=True
        )
        db.session.add(self.biz)
        db.session.flush()

        # Seed subscription
        from datetime import date
        self.sub = BusinessSubscription(
            business_id=self.biz.id,
            plan_id=self.plan.id,
            status='active',
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=29),
            max_staff=2,
            max_branches=2,
            max_rooms=5
        )
        db.session.add(self.sub)

        # Seed branches
        self.branch_a = Branch(business_id=self.biz.id, name='City Branch', is_active=True)
        self.branch_b = Branch(business_id=self.biz.id, name='Beach Branch', is_active=True)
        db.session.add_all([self.branch_a, self.branch_b])
        db.session.flush()

        # Seed room type & rooms
        self.room_type = RoomType(
            name='Deluxe Suite',
            business_id=self.biz.id,
            base_price=1500.0
        )
        db.session.add(self.room_type)
        db.session.flush()

        self.room_101 = Room(
            room_number='101', room_type_id=self.room_type.id,
            business_id=self.biz.id, branch_id=self.branch_a.id,
            floor=1, base_price=1500.0, status='available'
        )
        self.room_102 = Room(
            room_number='102', room_type_id=self.room_type.id,
            business_id=self.biz.id, branch_id=self.branch_a.id,
            floor=1, base_price=1500.0, status='available'
        )
        db.session.add_all([self.room_101, self.room_102])

        # Seed owner & staff user
        self.owner = User(
            email='owner@grandpalace.com', first_name='Hotel', last_name='Owner',
            role='owner', business_id=self.biz.id, permission_level='full', is_active=True
        )
        self.owner.set_password('Password123!')

        self.staff_a = User(
            email='staffa@grandpalace.com', first_name='Staff', last_name='City',
            role='staff', business_id=self.biz.id, permission_level='view_only', is_active=True
        )
        self.staff_a.set_password('Password123!')
        db.session.add_all([self.owner, self.staff_a])
        db.session.commit()

        from src.models.staff_branches import StaffBranch
        link = StaffBranch(user_id=self.staff_a.id, branch_id=self.branch_a.id)
        db.session.add(link)
        db.session.commit()

        self.owner_token = encode_token(self.owner.id)
        self.staff_token = encode_token(self.staff_a.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


    def test_health_check(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        self.assertIn('running', res.get_json()['message'])

    def test_half_open_date_overlap_availability(self):
        booking_data = {
            'room_id': self.room_101.id,
            'check_in_date': '2026-10-01',
            'check_out_date': '2026-10-05',
            'guest_name': 'Alice Smith',
            'guest_phone': '9999999999',
            'advance_amount': 500.0,
            'payment_method': 'cash'
        }
        b1, err, status = booking_service.create_booking(
            booking_data, actor=self.owner, source='offline',
            business_id=self.biz.id, branch_id=self.branch_a.id
        )
        self.assertIsNone(err)
        self.assertIsNotNone(b1)
        self.assertEqual(float(b1.amount_paid or 0), 500.0)

        # Overlapping booking in the middle (2026-10-02 to 2026-10-04) MUST FAIL
        b2, err2, status2 = booking_service.create_booking(
            {**booking_data, 'check_in_date': '2026-10-02', 'check_out_date': '2026-10-04'},
            actor=self.owner, source='offline', business_id=self.biz.id, branch_id=self.branch_a.id
        )
        self.assertIsNotNone(err2)
        self.assertEqual(status2, 409)

        # Contiguous booking starting exactly when b1 ends (2026-10-05 to 2026-10-08) MUST SUCCEED
        b3, err3, status3 = booking_service.create_booking(
            {**booking_data, 'check_in_date': '2026-10-05', 'check_out_date': '2026-10-08', 'guest_name': 'Bob Jones'},
            actor=self.owner, source='offline', business_id=self.biz.id, branch_id=self.branch_a.id
        )
        self.assertIsNone(err3)
        self.assertIsNotNone(b3)

    def test_subscription_limit_enforcement(self):
        allowed, msg, usage, limits = subscription_service.check_limit(self.biz.id, 'branch')
        self.assertFalse(allowed)
        self.assertIn('limit reached', msg.lower())

        res = self.client.post('/api/branches', json={'name': 'Mountain Branch'},
                                headers={'Authorization': f'Bearer {self.owner_token}'})
        self.assertEqual(res.status_code, 403)

    def test_staff_permission_and_branch_restriction(self):
        # Staff is view_only, so POST /api/rooms must return 403
        res = self.client.post('/api/rooms', json={'room_number': '999', 'room_type_id': self.room_type.id, 'price_per_night': 1000},
                                headers={'Authorization': f'Bearer {self.staff_token}'})
        self.assertEqual(res.status_code, 403)

        res_view = self.client.get('/api/rooms', headers={'Authorization': f'Bearer {self.staff_token}'})
        self.assertEqual(res_view.status_code, 200)

    def test_public_hotel_and_availability_endpoint(self):
        res = self.client.get(f'/api/public/hotels/{self.biz.slug}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()['data']
        self.assertEqual(data['name'], 'Grand Palace Resort')

        res_avail = self.client.get(
            f'/api/public/hotels/{self.biz.slug}/availability?check_in=2026-11-01&check_out=2026-11-05'
        )
        self.assertEqual(res_avail.status_code, 200)
        avail_data = res_avail.get_json()['data']
        self.assertEqual(avail_data['available_rooms'], 2)


if __name__ == '__main__':
    unittest.main()

