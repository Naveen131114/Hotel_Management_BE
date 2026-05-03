# Hotel Management System - Flask Backend

A comprehensive Flask-based RESTful API backend for managing hotel operations, bookings, staff, rooms, and guest reviews.

## 🏗️ Project Structure

```
hotel-management-system/
├── src/
│   ├── __init__.py                 # App factory
│   ├── models/
│   │   ├── room_types.py           # Room type definitions
│   │   ├── rooms.py                # Room inventory
│   │   ├── worker_types.py         # Staff positions
│   │   ├── workers.py              # Staff management
│   │   ├── users.py                # Guest accounts
│   │   ├── accessory_types.py      # Item categories
│   │   ├── accessories.py          # Items in hotel
│   │   ├── room_accessories.py     # Room inventory
│   │   ├── room_records.py         # Bookings
│   │   ├── booking_accessories.py  # Add-on services
│   │   ├── payments.py             # Payment tracking
│   │   ├── reviews.py              # Guest reviews
│   │   └── maintenance_logs.py     # Maintenance tracking
│   ├── routes/
│   │   ├── auth_routes.py          # Authentication endpoints
│   │   ├── room_type_routes.py     # Room type management
│   │   ├── room_routes.py          # Room management
│   │   ├── worker_type_routes.py   # Position management
│   │   ├── worker_routes.py        # Staff management
│   │   ├── user_routes.py          # Guest management
│   │   ├── accessory_type_routes.py # Category management
│   │   ├── accessory_routes.py     # Item management
│   │   ├── room_accessory_routes.py # Inventory management
│   │   ├── room_record_routes.py   # Booking management
│   │   ├── booking_accessory_routes.py # Add-on management
│   │   ├── payment_routes.py       # Payment management
│   │   ├── review_routes.py        # Review management
│   │   └── maintenance_log_routes.py # Maintenance management
│   └── utils/
│       ├── jwt_utils.py            # JWT authentication
│       └── response_handler.py     # Response formatting
├── app.py                          # Application entry point
├── config.py                       # Configuration
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
└── README.md                       # Documentation
```

## 🎯 Features

### ✅ Authentication & Security
- JWT token-based authentication
- Bcrypt password hashing
- Token expiration (24 hours)
- Protected routes with decorators

### ✅ Room Management
- Room types with pricing
- Individual room tracking
- Room status management (available, occupied, maintenance, reserved)
- Floor and location tracking

### ✅ Booking System
- Create and manage reservations
- Check-in/check-out tracking
- Guest count management
- Special requests handling

### ✅ Payment Processing
- Multiple payment methods (cash, card, online, bank_transfer)
- Payment tracking and status management
- Amount paid vs. total price tracking
- Transaction references

### ✅ Staff Management
- Worker types and positions
- Staff assignment to bookings
- Employment status tracking
- Hire date management

### ✅ Guest Reviews & Ratings
- 5-star rating system
- Category-specific ratings (cleanliness, staff, value)
- Average ratings calculation
- Published/unpublished control

### ✅ Maintenance Tracking
- Room issue reporting
- Issue type categorization
- Status tracking (reported, in_progress, resolved)
- Worker assignment
- Automatic timestamp tracking

### ✅ Inventory Management
- Accessory categorization
- Room inventory tracking
- Condition monitoring (good, damaged, missing)
- Chargeable items identification

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- pip

### Step 1: Clone Repository
```bash
git clone https://github.com/Naveen131114/Hotel_Management_BE.git
cd Hotel_Management_BE
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Setup Database
```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE hotel_management_db;
```

### Step 5: Configure Environment
```bash
# Copy and edit .env file
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Secrets
JWT_SECRET_KEY = 'your_jwt_secret_key_here'
SECRET_KEY = 'your_secret_key_here'

# Database
DATABASE_URI=mysql+pymysql://root:password@localhost/hotel_management_db

# Server
FLASK_ENV=development
FLASK_DEBUG=True
```

### Step 6: Run Database Migrations
```bash
# Initialize migrations
flask db init

# Create initial migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade

# Check migration history
flask db history
```

### Step 7: Run Application
```bash
python app.py
```

Server will run at: `http://localhost:5000`

## 📡 API Endpoints

### Authentication
```
POST   /api/auth/register              - Register new user
POST   /api/auth/login                 - Login user
```

### Room Management
```
GET    /api/room-types                 - Get all room types
GET    /api/room-types/<id>            - Get room type by ID
POST   /api/room-types                 - Create room type (protected)
PUT    /api/room-types/<id>            - Update room type (protected)
DELETE /api/room-types/<id>            - Delete room type (protected)

GET    /api/rooms                      - Get all rooms (filters: status, floor, room_type_id)
GET    /api/rooms/<id>                 - Get room by ID
POST   /api/rooms                      - Create room (protected)
PUT    /api/rooms/<id>                 - Update room (protected)
DELETE /api/rooms/<id>                 - Delete room (protected)
```

### Staff Management
```
GET    /api/worker-types               - Get all worker types
GET    /api/worker-types/<id>          - Get worker type by ID
POST   /api/worker-types               - Create worker type (protected)
PUT    /api/worker-types/<id>          - Update worker type (protected)
DELETE /api/worker-types/<id>          - Delete worker type (protected)

GET    /api/workers                    - Get all workers (filters: status, worker_type_id)
GET    /api/workers/<id>               - Get worker by ID
POST   /api/workers                    - Create worker (protected)
PUT    /api/workers/<id>               - Update worker (protected)
DELETE /api/workers/<id>               - Delete worker (protected)
```

### Guest Management
```
GET    /api/users                      - Get all users
GET    /api/users/<id>                 - Get user by ID
PUT    /api/users/<id>                 - Update user profile (protected)
DELETE /api/users/<id>                 - Delete user account (protected)
```

### Booking Management
```
GET    /api/room-records               - Get all bookings (filters: room_id, user_id, booking_status, payment_status)
GET    /api/room-records/<id>          - Get booking by ID
POST   /api/room-records               - Create booking (protected)
PUT    /api/room-records/<id>          - Update booking (protected)
DELETE /api/room-records/<id>          - Delete booking (protected)
```

### Payment Management
```
GET    /api/payments                   - Get all payments (filters: room_record_id, status)
GET    /api/payments/<id>              - Get payment by ID
POST   /api/payments                   - Create payment (protected)
PUT    /api/payments/<id>              - Update payment (protected)
DELETE /api/payments/<id>              - Delete payment (protected)
```

### Review Management
```
GET    /api/reviews                    - Get all reviews (filters: room_id, user_id, is_published)
GET    /api/reviews/<id>               - Get review by ID
GET    /api/reviews/room/<room_id>/average-rating - Get average ratings
POST   /api/reviews                    - Create review (protected)
PUT    /api/reviews/<id>               - Update review (protected)
DELETE /api/reviews/<id>               - Delete review (protected)
```

### Maintenance Management
```
GET    /api/maintenance-logs           - Get all logs (filters: room_id, status, issue_type)
GET    /api/maintenance-logs/<id>      - Get log by ID
POST   /api/maintenance-logs           - Create log (protected)
PUT    /api/maintenance-logs/<id>      - Update log (protected)
DELETE /api/maintenance-logs/<id>      - Delete log (protected)
```

### Accessory Management
```
GET    /api/accessory-types            - Get all types
GET    /api/accessory-types/<id>       - Get type by ID
POST   /api/accessory-types            - Create type (protected)
PUT    /api/accessory-types/<id>       - Update type (protected)
DELETE /api/accessory-types/<id>       - Delete type (protected)

GET    /api/accessories                - Get all accessories (filters: accessory_type_id, is_chargeable)
GET    /api/accessories/<id>           - Get accessory by ID
POST   /api/accessories                - Create accessory (protected)
PUT    /api/accessories/<id>           - Update accessory (protected)
DELETE /api/accessories/<id>           - Delete accessory (protected)
```

## 🔐 Authentication Usage

### Register Example
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "address": "2/96,Pillayar kovil street,Sengottai",
        "email": "munees@gmail.com",
        "first_name": "Muneeswaran",
        "id_number": "123456789012",
        "id_type": "Aadhar",
        "password": "1234",
        "last_name": "D",
        "nationality": "Indian",
        "phone": "+918754198220"
  }'
```

Response:
```json
{
  "message": "User registered successfully",
  "data": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    ...
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Login Example
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "secure123"
  }'
```

### Using Protected Endpoints
```bash
curl -X GET http://localhost:5000/api/rooms \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 📊 Database Schema Highlights

### Key Relationships
- RoomType → Room (1-to-many)
- WorkerType → Worker (1-to-many)
- Room → RoomAccessory (1-to-many)
- Accessory → RoomAccessory (1-to-many)
- User → RoomRecord (1-to-many)
- RoomRecord → Payment (1-to-many)
- RoomRecord → BookingAccessory (1-to-many)
- RoomRecord → Review (1-to-many)

### Key Enums
- Room Status: available, occupied, maintenance, reserved
- Booking Status: confirmed, checked_in, checked_out, cancelled, no_show
- Payment Status: pending, partial, paid, refunded
- Worker Status: active, inactive, on_leave
- Maintenance Status: reported, in_progress, resolved
- Condition: good, damaged, missing

## 🛠️ Development

### Update Dependencies
```bash
pip freeze > requirements.txt
```

### Database Migration Commands
```bash
# Create new migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Revert migration
flask db downgrade

# View history
flask db history

# Mark specific version
flask db stamp <revision_id>
```

### Testing API
```bash
# Using curl (examples above)
# Or use Postman/Insomnia for testing
```

## 📝 Response Format

All API responses follow this format:

### Success Response
```json
{
  "message": "Operation successful",
  "data": { /* actual data */ },
  "token": "jwt_token_here" // only for auth endpoints
}
```

### Error Response
```json
{
  "message": "Error description"
}
```

HTTP Status Codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Server Error

## 🔒 Security Best Practices

- ✅ JWT tokens with 24-hour expiration
- ✅ Bcrypt password hashing (cost factor: 12)
- ✅ Protected endpoints with token validation
- ✅ CORS enabled for cross-origin requests
- ✅ Input validation on all endpoints
- ✅ Environment variables for sensitive data

## 📱 Frontend Integration

The API is CORS-enabled and can be integrated with any frontend framework:

```javascript
// Example: Fetch with authentication
const token = localStorage.getItem('token');

fetch('http://localhost:5000/api/rooms', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(res => res.json())
.then(data => console.log(data));
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature-name`)
3. Commit changes (`git commit -m "Add feature"`)
4. Push to branch (`git push origin feature-name`)
5. Open Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 📧 Support

For issues or questions, please open an issue on GitHub or contact the project maintainer.

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-03  
**Author**: Naveen131114
