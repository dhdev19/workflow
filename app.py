from flask import Flask
from config import Config
from extensions import db, bcrypt, login_manager
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
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
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(dept_head_bp, url_prefix='/dept-head')
    app.register_blueprint(team_member_bp, url_prefix='/team-member')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    
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
    
    with app.app_context():
        try:
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
                print(f"Database initialization error: {e}")
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

