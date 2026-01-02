import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
    
    # Firebase configuration
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'workflow-firebase.json')
    FIREBASE_VAPID_KEY = os.getenv('FIREBASE_VAPID_KEY', '')
    
    # Database configuration
    DB_HOSTNAME = os.getenv('DB_HOSTNAME', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', '')
    
    # Build database URI
    # Use MySQL if DB credentials are provided, otherwise fallback to SQLite
    if DB_HOSTNAME and DB_USER and DB_PASSWORD:
        # URL encode password in case it contains special characters
        encoded_password = quote_plus(DB_PASSWORD)
        if DB_NAME:
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOSTNAME}/{DB_NAME}?charset=utf8mb4"
        else:
            # Connect without database if name not provided (for testing connection)
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOSTNAME}?charset=utf8mb4"
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///workflow.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MySQL connection pool settings to handle "server has gone away" errors
    if DB_HOSTNAME and DB_USER and DB_PASSWORD:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,      # Verify connections before using them (reconnects if stale)
            'pool_recycle': 3600,       # Recycle connections after 1 hour (3600 seconds)
            'pool_timeout': 20,         # Timeout for getting connection from pool
            'max_overflow': 10,         # Allow connections to overflow pool
            'pool_size': 5,             # Maintain 5 connections in pool
            'connect_args': {
                'connect_timeout': 10,  # Connection timeout
                'read_timeout': 30,     # Read timeout
                'write_timeout': 30,    # Write timeout
            }
        }

