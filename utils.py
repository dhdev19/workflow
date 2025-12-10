from functools import wraps
from flask import abort, current_app
from flask_login import current_user
from models import User

def role_required(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            if current_user.role not in roles:
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    return role_required('admin')(f)

def dept_head_required(f):
    """Decorator to require department head role"""
    return role_required('admin', 'department_head')(f)

def get_assigned_users_for_task(task):
    """Helper function to get all assigned users for a task"""
    return [assignment.user for assignment in task.assignments]

def can_access_task(user, task):
    """Check if user can access/view a task"""
    if user.role == 'admin':
        return True
    elif user.role == 'department_head':
        # Department head can see tasks in their department
        return user.department_id == task.department_id
    elif user.role == 'team_member':
        # Team member can only see tasks assigned to them
        return any(assignment.user_id == user.id for assignment in task.assignments)
    return False

