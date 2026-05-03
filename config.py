import os
from dotenv import load_dotenv
from datetime import timedelta

# Load .env file
load_dotenv(override=True)


class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default_jwt_secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "src/assets/"
    SERVE_STATIC_FOLDER = os.path.abspath("src/assets")
    ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = "production"


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
