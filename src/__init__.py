from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import DevelopmentConfig

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(DevelopmentConfig)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Register database models
    with app.app_context():
        # Import models to register them
        from src.models import (
            room_types, rooms, worker_types, workers, users,
            accessory_types, accessories, room_accessories,
            room_records, booking_accessories, payments,
            reviews, maintenance_logs
        )
        
        # Create tables if they don't exist
        db.create_all()
    
    # Register blueprints
    from src.routes import (
        auth_routes, room_type_routes, room_routes,
        worker_type_routes, worker_routes, user_routes,
        accessory_type_routes, accessory_routes, room_accessory_routes,
        room_record_routes, booking_accessory_routes, payment_routes,
        review_routes, maintenance_log_routes
    )
    
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(room_type_routes.bp)
    app.register_blueprint(room_routes.bp)
    app.register_blueprint(worker_type_routes.bp)
    app.register_blueprint(worker_routes.bp)
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(accessory_type_routes.bp)
    app.register_blueprint(accessory_routes.bp)
    app.register_blueprint(room_accessory_routes.bp)
    app.register_blueprint(room_record_routes.bp)
    app.register_blueprint(booking_accessory_routes.bp)
    app.register_blueprint(payment_routes.bp)
    app.register_blueprint(review_routes.bp)
    app.register_blueprint(maintenance_log_routes.bp)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'message': 'Hotel Management API is running!'}, 200
    
    return app
