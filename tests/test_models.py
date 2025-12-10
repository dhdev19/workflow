import pytest
from models import User, Department, Task, TaskAssignment, Subtask
from extensions import db, bcrypt

class TestModels:
    """Test database models."""
    
    def test_user_creation(self, app):
        """Test user model creation."""
        with app.app_context():
            user = User(
                email='testuser@test.com',
                username='testuser',
                password_hash=bcrypt.generate_password_hash('password').decode('utf-8'),
                role='team_member',
                full_name='Test User'
            )
            db.session.add(user)
            db.session.commit()
            
            retrieved_user = User.query.filter_by(email='testuser@test.com').first()
            assert retrieved_user is not None
            assert retrieved_user.username == 'testuser'
            assert retrieved_user.role == 'team_member'
    
    def test_department_creation(self, app):
        """Test department model creation."""
        with app.app_context():
            dept = Department(
                name='Test Department',
                description='Test Description'
            )
            db.session.add(dept)
            db.session.commit()
            
            retrieved_dept = Department.query.filter_by(name='Test Department').first()
            assert retrieved_dept is not None
            assert retrieved_dept.description == 'Test Description'
    
    def test_task_creation(self, app, admin_user, department):
        """Test task model creation."""
        with app.app_context():
            from models import Department, User
            dept = Department.query.filter_by(name='Test Department').first()
            admin = User.query.filter_by(email='admin@test.com').first()
            task = Task(
                task_name='Test Task',
                description='Test Description',
                priority='URGENT',
                status='ASSIGNED',
                department_id=dept.id,
                created_by_id=admin.id,
                client_name='Test Client'
            )
            db.session.add(task)
            db.session.commit()
            
            retrieved_task = Task.query.filter_by(task_name='Test Task').first()
            assert retrieved_task is not None
            assert retrieved_task.priority == 'URGENT'
            assert retrieved_task.client_name == 'Test Client'
    
    def test_task_assignment(self, app, task, team_member):
        """Test task assignment model."""
        with app.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            db.session.add(assignment)
            db.session.commit()
            
            retrieved_assignment = TaskAssignment.query.filter_by(
                task_id=t.id,
                user_id=member.id
            ).first()
            assert retrieved_assignment is not None
    
    def test_subtask_creation(self, app, task, team_member):
        """Test subtask model creation."""
        with app.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            subtask = Subtask(
                task_id=t.id,
                subtask_name='Test Subtask',
                description='Subtask Description',
                created_by_id=member.id
            )
            db.session.add(subtask)
            db.session.commit()
            
            retrieved_subtask = Subtask.query.filter_by(subtask_name='Test Subtask').first()
            assert retrieved_subtask is not None
            assert retrieved_subtask.task_id == t.id
    
    def test_user_department_relationship(self, app, department):
        """Test user-department relationship."""
        with app.app_context():
            from models import Department
            dept = Department.query.filter_by(name='Test Department').first()
            user = User(
                email='deptuser@test.com',
                username='deptuser',
                password_hash='hashed',
                role='team_member',
                full_name='Dept User',
                department_id=dept.id
            )
            db.session.add(user)
            db.session.commit()
            
            # Refresh both objects
            db.session.refresh(user)
            db.session.refresh(dept)
            
            # Test relationship
            assert user.department is not None
            assert user.department.name == dept.name
            assert user in dept.members
    
    def test_task_department_relationship(self, app, task, department):
        """Test task-department relationship."""
        with app.app_context():
            from models import Task, Department
            t = Task.query.filter_by(task_name='Test Task').first()
            dept = Department.query.filter_by(name='Test Department').first()
            # Test relationship
            assert t.department is not None
            assert t.department.id == dept.id
            assert t in dept.tasks

