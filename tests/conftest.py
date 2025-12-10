import pytest
from app import create_app
from extensions import db, bcrypt
from models import User, Department, Task, TaskAssignment, Subtask
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    # Remove MySQL-specific settings for test database
    SQLALCHEMY_ENGINE_OPTIONS = {}

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    with app.app_context():
        user = User(
            email='admin@test.com',
            username='admin',
            password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin',
            full_name='Admin User'
        )
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def department(app, admin_user):
    """Create test department."""
    with app.app_context():
        dept = Department(
            name='Test Department',
            description='Test Department Description'
        )
        db.session.add(dept)
        db.session.commit()
        # Access ID while in session to avoid detached instance
        _ = dept.id
        db.session.expunge(dept)
        # Reattach by merging when needed
        return dept

@pytest.fixture
def department_head(app, department):
    """Create department head user."""
    with app.app_context():
        # Query department fresh to get ID
        dept = Department.query.filter_by(name='Test Department').first()
        user = User(
            email='head@test.com',
            username='depthead',
            password_hash=bcrypt.generate_password_hash('head123').decode('utf-8'),
            role='department_head',
            full_name='Department Head',
            department_id=dept.id
        )
        db.session.add(user)
        db.session.commit()
        _ = user.id
        db.session.expunge(user)
        return user

@pytest.fixture
def team_member(app, department):
    """Create team member user."""
    with app.app_context():
        # Query department fresh to get ID
        dept = Department.query.filter_by(name='Test Department').first()
        user = User(
            email='member@test.com',
            username='member',
            password_hash=bcrypt.generate_password_hash('member123').decode('utf-8'),
            role='team_member',
            full_name='Team Member',
            department_id=dept.id
        )
        db.session.add(user)
        db.session.commit()
        _ = user.id
        db.session.expunge(user)
        return user

@pytest.fixture
def task(app, admin_user, department):
    """Create test task."""
    with app.app_context():
        # Query fresh instances to get IDs
        dept = Department.query.filter_by(name='Test Department').first()
        admin = User.query.filter_by(email='admin@test.com').first()
        task = Task(
            task_name='Test Task',
            description='Test Task Description',
            priority='URGENT',
            status='ASSIGNED',
            department_id=dept.id,
            created_by_id=admin.id
        )
        db.session.add(task)
        db.session.commit()
        _ = task.id
        db.session.expunge(task)
        return task

