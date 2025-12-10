import pytest
from models import Task, Subtask, TaskAssignment
from datetime import datetime

class TestTaskFunctionality:
    """Test task-related functionality."""
    
    def test_view_task_detail(self, client, admin_user, task):
        """Test viewing task details."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            task_id = t.id
        response = client.get(f'/tasks/{task_id}')
        assert response.status_code == 200
        assert b'Test Task' in response.data
    
    def test_task_priorities(self, client, admin_user, department):
        """Test different task priorities."""
        priorities = ['URGENT', 'IMPORTANT', 'DAILY TASK']
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Department
            dept = Department.query.filter_by(name='Test Department').first()
            dept_id = dept.id
        
        for priority in priorities:
            response = client.post('/admin/tasks/create', data={
                'task_name': f'{priority} Task',
                'description': f'Task with {priority} priority',
                'priority': priority,
                'department_id': dept_id,
                'assign_to[]': [],
                'assign_type[]': []
            }, follow_redirects=True)
            assert response.status_code == 200
        
        # Verify all priorities were created
        with client.application.app_context():
            for priority in priorities:
                task = Task.query.filter_by(priority=priority).first()
                assert task is not None
    
    def test_task_statuses(self, client, team_member, task):
        """Test different task statuses."""
        statuses = ['ASSIGNED', 'PENDING', 'COMPLETED', 'Review with ADMIN', 'Waiting for approval from Client']
        
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
        
        for status in statuses:
            response = client.post(f'/team-member/tasks/{task_id}/update-status', data={
                'status': status
            }, follow_redirects=True)
            assert response.status_code == 200
            # Verify status was updated
            with client.application.app_context():
                from models import Task
                updated_task = Task.query.get(task_id)
                assert updated_task.status == status
    
    def test_task_with_deadline(self, client, admin_user, department):
        """Test creating task with deadline."""
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        with client.application.app_context():
            from models import Department
            dept = Department.query.filter_by(name='Test Department').first()
            dept_id = dept.id
        deadline = '2025-12-31T23:59'
        response = client.post('/admin/tasks/create', data={
            'task_name': 'Task with Deadline',
            'description': 'Task with a deadline',
            'priority': 'URGENT',
            'department_id': dept_id,
            'deadline': deadline,
            'assign_to[]': [],
            'assign_type[]': []
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify deadline was set
        with client.application.app_context():
            task = Task.query.filter_by(task_name='Task with Deadline').first()
            assert task is not None
            assert task.deadline is not None
    
    def test_subtask_status_update(self, client, team_member, task):
        """Test updating subtask status."""
        # Create subtask
        with client.application.app_context():
            from models import Task, User
            t = Task.query.filter_by(task_name='Test Task').first()
            member = User.query.filter_by(email='member@test.com').first()
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            subtask = Subtask(
                task_id=t.id,
                subtask_name='Test Subtask',
                description='Test',
                created_by_id=member.id
            )
            from extensions import db
            db.session.add(assignment)
            db.session.add(subtask)
            db.session.commit()
            subtask_id = subtask.id
        
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.post(f'/tasks/subtasks/{subtask_id}/update-status', data={
            'status': 'COMPLETED'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify subtask status was updated
        with client.application.app_context():
            updated_subtask = Subtask.query.get(subtask_id)
            assert updated_subtask.status == 'COMPLETED'
    
    def test_multiple_user_assignment(self, client, admin_user, department, team_member):
        """Test assigning task to multiple users."""
        # Create another team member
        with client.application.app_context():
            from models import Department, User
            dept = Department.query.filter_by(name='Test Department').first()
            member = User.query.filter_by(email='member@test.com').first()
            member2 = User(
                email='member2@test.com',
                username='member2',
                password_hash='hashed',
                role='team_member',
                full_name='Member 2',
                department_id=dept.id
            )
            from extensions import db
            db.session.add(member2)
            db.session.commit()
            member_id = member.id
            member2_id = member2.id
            dept_id = dept.id
        
        client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        response = client.post('/admin/tasks/create', data={
            'task_name': 'Multi-assign Task',
            'description': 'Task for multiple users',
            'priority': 'IMPORTANT',
            'department_id': dept_id,
            'assign_to[]': [str(member_id), str(member2_id)],
            'assign_type[]': ['user', 'user']
        }, follow_redirects=True)
        assert response.status_code == 200
        # Verify both users are assigned
        with client.application.app_context():
            from models import Task
            task = Task.query.filter_by(task_name='Multi-assign Task').first()
            assert task is not None
            assignments = TaskAssignment.query.filter_by(task_id=task.id).all()
            assert len(assignments) == 2

