import pytest
from models import Task, User

class TestPermissions:
    """Test role-based permissions."""
    
    def test_team_member_cannot_access_admin_routes(self, client, team_member):
        """Test team member cannot access admin routes."""
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        # Try to access admin dashboard
        response = client.get('/admin/dashboard', follow_redirects=True)
        assert response.status_code == 403 or b'403' in response.data or response.status_code == 302
    
    def test_team_member_cannot_delete_tasks(self, client, team_member, task):
        """Test team member cannot delete tasks."""
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        with client.application.app_context():
            from models import Task
            t = Task.query.filter_by(task_name='Test Task').first()
            task_id = t.id
        # Try to delete task (endpoint should not exist for team member)
        response = client.post(f'/admin/tasks/{task_id}/delete', follow_redirects=True)
        assert response.status_code in [403, 404, 302]
    
    def test_department_head_cannot_access_admin_users(self, client, department_head):
        """Test department head cannot access admin user management."""
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        # Try to access admin users page
        response = client.get('/admin/users', follow_redirects=True)
        assert response.status_code == 403 or b'403' in response.data or response.status_code == 302
    
    def test_department_head_can_only_see_own_department_tasks(self, client, department_head, task, admin_user, department):
        """Test department head only sees tasks from their department."""
        # Create task in different department
        with client.application.app_context():
            from models import Department, Task, User
            other_dept = Department(name='Other Department')
            admin = User.query.filter_by(email='admin@test.com').first()
            from extensions import db
            db.session.add(other_dept)
            db.session.commit()
            
            other_task = Task(
                task_name='Other Department Task',
                description='Task in other department',
                priority='URGENT',
                status='ASSIGNED',
                department_id=other_dept.id,
                created_by_id=admin.id
            )
            db.session.add(other_task)
            db.session.commit()
        
        client.post('/auth/login', data={
            'email': 'head@test.com',
            'password': 'head123'
        })
        response = client.get('/dept-head/dashboard')
        assert response.status_code == 200
        # Should see task from their department
        assert b'Test Task' in response.data
        # Should not see task from other department
        assert b'Other Department Task' not in response.data
    
    def test_team_member_can_only_see_assigned_tasks(self, client, team_member, task):
        """Test team member only sees assigned tasks."""
        # Create another task not assigned to member
        with client.application.app_context():
            from models import Task, User, TaskAssignment
            member = User.query.filter_by(email='member@test.com').first()
            t = Task.query.filter_by(task_name='Test Task').first()
            other_task = Task(
                task_name='Unassigned Task',
                description='Task not assigned to member',
                priority='URGENT',
                status='ASSIGNED',
                department_id=member.department_id,
                created_by_id=member.id
            )
            from extensions import db
            db.session.add(other_task)
            db.session.commit()
            
            # Assign only the first task
            assignment = TaskAssignment(
                task_id=t.id,
                user_id=member.id,
                assigned_by_id=member.id
            )
            db.session.add(assignment)
            db.session.commit()
        
        client.post('/auth/login', data={
            'email': 'member@test.com',
            'password': 'member123'
        })
        response = client.get('/team-member/dashboard')
        assert response.status_code == 200
        # Should see assigned task
        assert b'Test Task' in response.data
        # Should not see unassigned task
        assert b'Unassigned Task' not in response.data

