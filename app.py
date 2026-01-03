from flask import Flask, request
from config import Config
from extensions import db, bcrypt, login_manager
import os
import json
import logging
import traceback
from logging.handlers import RotatingFileHandler

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Setup logging for production
    if config_class.IS_PRODUCTION:
        # Configure logging to file
        if not app.debug:
            # Setup error log handler (ERROR level only) - errorlog.txt
            error_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'errorlog.txt')
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            error_handler.setLevel(logging.ERROR)
            
            # Setup production log handler (INFO level and above) - prodlogs.txt
            prod_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prodlogs.txt')
            prod_handler = RotatingFileHandler(
                prod_log_file,
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            prod_handler.setLevel(logging.INFO)
            
            # Create formatter for both handlers
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            error_handler.setFormatter(formatter)
            prod_handler.setFormatter(formatter)
            
            # Add both handlers to app logger
            app.logger.addHandler(error_handler)
            app.logger.addHandler(prod_handler)
            app.logger.setLevel(logging.INFO)  # Set to INFO to capture all logs
    
    # Apply engine options to app config if using MySQL
    if hasattr(config_class, 'SQLALCHEMY_ENGINE_OPTIONS') and config_class.SQLALCHEMY_ENGINE_OPTIONS:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = config_class.SQLALCHEMY_ENGINE_OPTIONS
    
    # Initialize extensions (Flask-SQLAlchemy 3.x reads SQLALCHEMY_ENGINE_OPTIONS from app.config)
    db.init_app(app)
    
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.department_head import dept_head_bp
    from routes.team_member import team_member_bp
    from routes.tasks import tasks_bp
    from routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(dept_head_bp, url_prefix='/dept-head')
    app.register_blueprint(team_member_bp, url_prefix='/team-member')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    
    # Add custom Jinja2 filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object"""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'department_head':
                return redirect(url_for('dept_head.dashboard'))
            elif current_user.role == 'team_member':
                return redirect(url_for('team_member.dashboard'))
        return redirect(url_for('auth.login'))
    
    # Register error handlers for production logging
    @app.errorhandler(404)
    def not_found_error(error):
        if config_class.IS_PRODUCTION:
            app.logger.error(f'404 Error: {request.url} - {str(error)}')
        from flask import jsonify
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if config_class.IS_PRODUCTION:
            app.logger.error(
                f'500 Internal Server Error\n'
                f'Request URL: {request.url}\n'
                f'Request Method: {request.method}\n'
                f'Error: {str(error)}\n'
                f'Traceback:\n{traceback.format_exc()}'
            )
        from flask import jsonify
        return jsonify({'error': 'Internal server error'}), 500
    
    # Log unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(e):
        if config_class.IS_PRODUCTION:
            app.logger.error(
                f'Unhandled Exception: {type(e).__name__}: {str(e)}\n'
                f'Request URL: {request.url}\n'
                f'Request Method: {request.method}\n'
                f'Request Data: {request.get_data(as_text=True)[:500]}\n'
                f'Traceback:\n{traceback.format_exc()}'
            )
        # Re-raise in debug mode to see full error
        if app.debug:
            raise
        from flask import jsonify
        return jsonify({'error': 'An unexpected error occurred'}), 500
    
    with app.app_context():
        try:
            # Import all models to ensure they're registered with SQLAlchemy
            from models import User, Department, Task, TaskAssignment, Subtask, TaskDepartmentAssignment, DepartmentTaskCompletion, TaskApprovalRequest, FCMDevice
            db.create_all()
            
            # Create default admin if not exists (skip in test mode)
            if not app.config.get('TESTING', False):
                from models import User, Department
                admin = User.query.filter_by(email='admin@digitalhomeez.com', role='admin').first()
                if not admin:
                    admin = User(
                        email='admin@digitalhomeez.com',
                        username='admin',
                        password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                        role='admin',
                        full_name='System Admin'
                    )
                    db.session.add(admin)
                    db.session.commit()
        except Exception as e:
            if not app.config.get('TESTING', False):
                error_msg = f"Database initialization error: {e}\n{traceback.format_exc()}"
                print(error_msg)
                if config_class.IS_PRODUCTION:
                    app.logger.error(error_msg)
                print("\nPlease check:")
                print("1. Database name in .env file (DB_NAME) - it might be different from username")
                print("2. Database exists in your MySQL server")
                print("3. User has proper permissions to access the database")
                print("\nTo find your database name, check your hosting control panel (cPanel/hPanel)")
                raise
            # In test mode, just pass - errors are expected during setup
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=8000)

