import pytest
from models import Task, TaskAssignment, Subtask

class TestTeamMemberFunctionality:
    """Test team member functionality."""
    
    def test_team_member_dashboard(self, client, team_member):
        """Test team member can access dashboard."""
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.get('/team-member/dashboard')
        assert response.status_code == 200
    
    def test_view_assigned_tasks(self, client, team_member, task):
        """Test team member can view assigned tasks."""
        # Assign task to team member
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            from extensions import db
            db.session.add(assignment)
            db.session.commit()
        
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.get('/team-member/dashboard')
        assert response.status_code == 200
        assert b'Test Task' in response.data
    
    def test_create_task(self, client, team_member):
        """Test team member can create task."""
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.post('/team-member/tasks/create', data={
            'task_name': 'Member Task',
            'description': 'Task created by member',
            'priority': 'DAILY TASK',
            'client_name': '',
            'deadline': '',
            'remark': ''
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify task was created
        with client.application.app_context():
            from models import User
            task = Task.query.filter_by(task_name='Member Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assert task is not None
            assert task.department_id == member.department_id
    
    def test_update_task_status(self, client, team_member, task):
        """Test team member can update task status."""
        # Assign task to team member
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            from extensions import db
            db.session.add(assignment)
            db.session.commit()
            task_id = t.id
        
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.post(f'/team-member/tasks/{task_id}/update-status', data={
            'status': 'COMPLETED'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify status was updated
        with client.application.app_context():
            from models import Task
            updated_task = Task.query.get(task_id)
            assert updated_task.status == 'COMPLETED'
    
    def test_add_subtask(self, client, team_member, task):
        """Test adding subtask to task."""
        # Assign task to team member
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            from extensions import db
            db.session.add(assignment)
            db.session.commit()
            task_id = t.id
        
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.post(f'/tasks/{task_id}/subtasks/add', data={
            'subtask_name': 'Test Subtask',
            'description': 'Subtask description'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify subtask was created
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            subtask = Subtask.query.filter_by(subtask_name='Test Subtask').first()
            assert subtask is not None
            assert subtask.task_id == t.id

