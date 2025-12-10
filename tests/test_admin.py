import pytest
from models import User, Department, Task, TaskAssignment

class TestAdminFunctionality:
    """Test admin functionality."""
    
    def test_admin_dashboard_access(self, client, admin_user):
        """Test admin can access dashboard."""
        # Login as admin
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'All Tasks' in response.data or b'Dashboard' in response.data
    
    def test_create_department(self, client, admin_user):
        """Test creating a department."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        response = client.post('/admin/departments/add', data={
            'name': 'New Department',
            'description': 'New Department Description'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify department was created
        with client.application.app_context():
            dept = Department.query.filter_by(name='New Department').first()
            assert dept is not None
    
    def test_create_user(self, client, admin_user, department):
        """Test creating a new user."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Department
            dept = Department.query.filter_by(name='Test Department').first()
            dept_id = dept.id
        response = client.post('/admin/users/add', data={
            'email': 'newuser@test.com',
            'username': 'newuser',
            'full_name': 'New User',
            'password': 'password123',
            'role': 'team_member',
            'department_id': dept_id
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify user was created
        with client.application.app_context():
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.role == 'team_member'
    
    def test_create_task(self, client, admin_user, department, team_member):
        """Test creating a task."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Department, User
            dept = Department.query.filter_by(name='Test Department').first()
            member = User.query.filter_by(email='member@test.com').first()
            dept_id = dept.id
            member_id = member.id
        response = client.post('/admin/tasks/create', data={
            'task_name': 'New Task',
            'description': 'Task Description',
            'priority': 'IMPORTANT',
            'department_id': dept_id,
            'assign_to[]': [str(member_id)],
            'assign_type[]': ['user']
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify task was created
        with client.application.app_context():
            task = Task.query.filter_by(task_name='New Task').first()
            assert task is not None
            assert task.priority == 'IMPORTANT'
    
    def test_edit_task(self, client, admin_user, task):
        """Test editing a task."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            task_id = t.id
            dept_id = t.department_id
        response = client.post(f'/admin/tasks/{task_id}/edit', data={
            'task_name': 'Updated Task Name',
            'description': 'Updated Description',
            'priority': 'DAILY TASK',
            'department_id': dept_id,
            'client_name': 'Test Client',
            'deadline': '',
            'remark': 'Test remark'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify task was updated
        with client.application.app_context():
            from models import Task
            updated_task = Task.query.get(task_id)
            assert updated_task.task_name == 'Updated Task Name'
            assert updated_task.priority == 'DAILY TASK'
    
    def test_delete_task(self, client, admin_user, task):
        """Test deleting a task."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            task_id = t.id
        response = client.post(f'/admin/tasks/{task_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        # Verify task was deleted
        with client.application.app_context():
            from models import Task
            deleted_task = Task.query.get(task_id)
            assert deleted_task is None
    
    def test_analytics_page(self, client, admin_user):
        """Test analytics page access."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        response = client.get('/admin/analytics')
        assert response.status_code == 200

