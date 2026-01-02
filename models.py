from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.orm import relationship
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, department_head, team_member
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    department = relationship('Department', back_populates='members')
    assigned_tasks = relationship('TaskAssignment', primaryjoin='TaskAssignment.user_id == User.id', back_populates='user', cascade='all, delete-orphan')
    created_tasks = relationship('Task', foreign_keys='Task.created_by_id', back_populates='creator')
    fcm_devices = relationship('FCMDevice', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    members = relationship('User', back_populates='department')
    head = relationship('User', uselist=False, primaryjoin='and_(Department.id==User.department_id, User.role=="department_head")', overlaps="department,members", viewonly=True)
    tasks = relationship('Task', back_populates='department')
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(50), nullable=False)  # URGENT, IMPORTANT, DAILY TASK
    status = db.Column(db.String(50), nullable=False, default='ASSIGNED')  # COMPLETED, PENDING, ASSIGNED, Review with ADMIN, Complete, Waiting for approval from Client
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    client_name = db.Column(db.String(200), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    department = relationship('Department', back_populates='tasks')
    creator = relationship('User', foreign_keys=[created_by_id], back_populates='created_tasks')
    assignments = relationship('TaskAssignment', back_populates='task', cascade='all, delete-orphan')
    subtasks = relationship('Subtask', back_populates='task', cascade='all, delete-orphan')
    department_assignments = relationship('TaskDepartmentAssignment', back_populates='task', cascade='all, delete-orphan')
    department_completions = relationship('DepartmentTaskCompletion', back_populates='task', cascade='all, delete-orphan')
    approval_requests = relationship('TaskApprovalRequest', back_populates='task', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Task {self.task_name}>'

class TaskAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    task = relationship('Task', back_populates='assignments')
    user = relationship('User', foreign_keys=[user_id], back_populates='assigned_tasks')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id])
    
    def __repr__(self):
        return f'<TaskAssignment task_id={self.task_id} user_id={self.user_id}>'

class Subtask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    subtask_name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='PENDING')  # COMPLETED, PENDING
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    task = relationship('Task', back_populates='subtasks')
    creator = relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f'<Subtask {self.subtask_name}>'

class TaskDepartmentAssignment(db.Model):
    """Tracks which departments are assigned to work on a task"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    task = relationship('Task', back_populates='department_assignments')
    department = relationship('Department')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id])
    
    __table_args__ = (db.UniqueConstraint('task_id', 'department_id', name='unique_task_department'),)
    
    def __repr__(self):
        return f'<TaskDepartmentAssignment task_id={self.task_id} department_id={self.department_id}>'

class DepartmentTaskCompletion(db.Model):
    """Tracks completion status for each department assigned to a task"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    task = relationship('Task', back_populates='department_completions')
    department = relationship('Department')
    completed_by = relationship('User', foreign_keys=[completed_by_id])
    
    __table_args__ = (db.UniqueConstraint('task_id', 'department_id', name='unique_task_department_completion'),)
    
    def __repr__(self):
        return f'<DepartmentTaskCompletion task_id={self.task_id} department_id={self.department_id} is_completed={self.is_completed}>'

class TaskApprovalRequest(db.Model):
    """Tracks approval requests for department head actions"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    request_type = db.Column(db.String(50), nullable=False)  # 'reassign' or 'assign_departments'
    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='PENDING')  # PENDING, APPROVED, REJECTED
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)
    
    # For reassign requests
    new_dept_head_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # For assign_departments requests - stored as JSON or separate table
    # We'll use a JSON field or create a separate table for requested departments
    requested_department_ids = db.Column(db.Text, nullable=True)  # JSON array of department IDs
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    task = relationship('Task', back_populates='approval_requests')
    requested_by = relationship('User', foreign_keys=[requested_by_id])
    approved_by = relationship('User', foreign_keys=[approved_by_id])
    new_dept_head = relationship('User', foreign_keys=[new_dept_head_id])
    
    def __repr__(self):
        return f'<TaskApprovalRequest task_id={self.task_id} type={self.request_type} status={self.status}>'

class FCMDevice(db.Model):
    """Stores FCM tokens for user devices"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fcm_token = db.Column(db.String(500), nullable=False, unique=True, index=True)
    device_name = db.Column(db.String(200), nullable=True)  # e.g., "John's iPhone", "Samsung Galaxy"
    device_type = db.Column(db.String(50), nullable=True)  # e.g., "android", "ios", "web"
    last_active = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship('User', back_populates='fcm_devices')
    
    def __repr__(self):
        return f'<FCMDevice user_id={self.user_id} device={self.device_name}>'

