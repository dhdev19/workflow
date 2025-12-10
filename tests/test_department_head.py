import pytest
from models import User, Task, TaskAssignment

class TestDepartmentHeadFunctionality:
    """Test department head functionality."""
    
    def test_department_head_dashboard(self, client, department_head):
        """Test department head can access dashboard."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        response = client.get('/dept-head/dashboard')
        assert response.status_code == 200
    
    def test_add_team_member(self, client, department_head):
        """Test department head can add team member."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        response = client.post('/dept-head/team-members/add', data={
            'email': 'newmember@test.com',
            'username': 'newmember',
            'full_name': 'New Member',
            'password': 'member123'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify team member was created
        with client.application.app_context():
            from models import User
            member = User.query.filter_by(email='newmember@test.com').first()
            head = User.query.filter_by(email='head@test.com').first()
            assert member is not None
            assert member.role == 'team_member'
            assert member.department_id == head.department_id
    
    def test_create_task(self, client, department_head, team_member):
        """Test department head can create task."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        with client.application.app_context():
            from models import User
            member = User.query.filter_by(email='member@test.com').first()
            member_id = member.id
        response = client.post('/dept-head/tasks/create', data={
            'task_name': 'Dept Head Task',
            'description': 'Task from department head',
            'priority': 'URGENT',
            'client_name': 'Test Client',
            'deadline': '',
            'remark': '',
            'assign_to[]': [str(member_id)]
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify task was created
        with client.application.app_context():
            from models import User
            task = Task.query.filter_by(task_name='Dept Head Task').first()
            head = User.query.filter_by(email='head@test.com').first()
            assert task is not None
            assert task.department_id == head.department_id
    
    def test_forward_task(self, client, department_head, task, team_member):
        """Test forwarding task to team member."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            task_id = t.id
            member_id = member.id
        response = client.post(f'/dept-head/tasks/{task_id}/forward', data={
            'assign_to[]': [str(member_id)]
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify task was assigned
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment.query.filter_by(
                task_id=t.id,
                user_id=member.id
            ).first()
            assert assignment is not None
    
    def test_cannot_delete_task(self, client, department_head, task):
        """Test department head cannot delete tasks."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            task_id = t.id
        # Try to access delete endpoint (should not exist for dept head)
        response = client.post(f'/admin/tasks/{task_id}/delete', follow_redirects=True)
        # Should either 403 or redirect (no access)
        assert response.status_code in [403, 404, 302]

