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
        # Department head can see tasks in their department OR tasks assigned to their department
        if not user.department_id:
            return False
        # Check if task belongs to their department
        if user.department_id == task.department_id:
            return True
        # Check if task is assigned to their department via TaskDepartmentAssignment
        from models import TaskDepartmentAssignment
        dept_assignment = TaskDepartmentAssignment.query.filter_by(
            task_id=task.id,
            department_id=user.department_id
        ).first()
        return dept_assignment is not None
    elif user.role == 'team_member':
        # Team member can only see tasks assigned to them
        return any(assignment.user_id == user.id for assignment in task.assignments)
    return False

def send_task_assignment_notification(user, task, assigned_by):
    """Send FCM notification when a task is assigned to a user (sends to all user devices)"""
    try:
        from fcm_service import send_notification_to_multiple, send_notification
        from models import FCMDevice
        
        # Get all FCM tokens for the user
        # devices = FCMDevice.query.filter_by(user_id=user.id).all()
        try:
            device = user.fcm_devices[0]
            devices = [device.fcm_token]
        except Exception as e:
            print(f"Error getting FCM token: {e}")
            devices = []
        if not devices:
            return False
        # 
        # fcm_tokens = [device.fcm_token for device in devices if device.fcm_token]
        # if not fcm_tokens:
        #     return False
        
        title = "New Task Assigned"
        priority_emoji = {
            'URGENT': '🔴',
            'IMPORTANT': '🟡',
            'DAILY TASK': '🟢'
        }.get(task.priority, '📋')
        
        body = f"{priority_emoji} {task.task_name}"
        if task.priority == 'URGENT':
            body = f"🔴 URGENT: {task.task_name}"
        
        data = {
            'type': 'task_assigned',
            'task_id': str(task.id),
            'task_name': task.task_name,
            'priority': task.priority,
        }
        
        # Send to all user devices
        # result = send_notification_to_multiple(fcm_tokens, title, body, data)
        result = send_notification(devices[0], title, body, data)
        # Log notification attempt (success/failure logged in fcm_service)
        from flask import current_app
        if current_app:
            status = "SUCCESS" if result else "FAILED"
            current_app.logger.error(f"FCM Task Assignment Notification - {status} - User: {user.email} (ID: {user.id}), Task: '{task.task_name}' (ID: {task.id}), Assigned by: {assigned_by.email}")
        return result
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f"FCM Task Assignment Notification - EXCEPTION - User: {user.email if user else 'Unknown'} (ID: {user.id if user else 'N/A'}), Task: '{task.task_name if task else 'Unknown'}' (ID: {task.id if task else 'N/A'}), Error: {str(e)}")
        return False

