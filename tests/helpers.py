"""Helper functions for tests."""
from models import User, Department, Task

def get_user_id(client, email):
    """Get user ID by email within app context."""
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        return user.id if user else None

def get_department_id(client, name):
    """Get department ID by name within app context."""
    with client.application.app_context():
        dept = Department.query.filter_by(name=name).first()
        return dept.id if dept else None

def get_task_id(client, task_name):
    """Get task ID by name within app context."""
    with client.application.app_context():
        task = Task.query.filter_by(task_name=task_name).first()
        return task.id if task else None

def get_fresh_user(app, email):
    """Get fresh user object within app context."""
    with app.app_context():
        from models import User
        return User.query.filter_by(email=email).first()

def get_fresh_department(app, name):
    """Get fresh department object within app context."""
    with app.app_context():
        from models import Department
        return Department.query.filter_by(name=name).first()

def get_fresh_task(app, task_name):
    """Get fresh task object within app context."""
    with app.app_context():
        from models import Task
        return Task.query.filter_by(task_name=task_name).first()

