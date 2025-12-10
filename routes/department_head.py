from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Department, Task, TaskAssignment, Subtask
from extensions import bcrypt
from utils import dept_head_required
from datetime import datetime

dept_head_bp = Blueprint('dept_head', __name__)

@dept_head_bp.route('/dashboard')
@login_required
@dept_head_required
def dashboard():
    # Get tasks for department head's department
    dept_id = current_user.department_id
    if not dept_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('auth.logout'))
    
    tasks = Task.query.filter_by(department_id=dept_id).order_by(Task.created_at.desc()).all()
    return render_template('dept_head/dashboard.html', tasks=tasks)

@dept_head_bp.route('/team-members')
@login_required
@dept_head_required
def team_members():
    dept_id = current_user.department_id
    if not dept_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('auth.logout'))
    
    members = User.query.filter_by(department_id=dept_id, role='team_member').all()
    return render_template('dept_head/team_members.html', members=members)

@dept_head_bp.route('/team-members/add', methods=['GET', 'POST'])
@login_required
@dept_head_required
def add_team_member():
    dept_id = current_user.department_id
    if not dept_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('dept_head.team_members'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('User with this email already exists', 'error')
            return redirect(url_for('dept_head.add_team_member'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('dept_head.add_team_member'))
        
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='team_member',
            department_id=dept_id
        )
        db.session.add(user)
        db.session.commit()
        flash('Team member added successfully', 'success')
        return redirect(url_for('dept_head.team_members'))
    
    return render_template('dept_head/add_team_member.html')

@dept_head_bp.route('/team-members/<int:user_id>/delete', methods=['POST'])
@login_required
@dept_head_required
def delete_team_member(user_id):
    member = User.query.get_or_404(user_id)
    
    if member.department_id != current_user.department_id:
        flash('You can only remove members from your department', 'error')
        return redirect(url_for('dept_head.team_members'))
    
    if member.role != 'team_member':
        flash('You can only remove team members', 'error')
        return redirect(url_for('dept_head.team_members'))
    
    db.session.delete(member)
    db.session.commit()
    flash('Team member removed successfully', 'success')
    return redirect(url_for('dept_head.team_members'))

@dept_head_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
@dept_head_required
def create_task():
    dept_id = current_user.department_id
    if not dept_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        description = request.form.get('description', '')
        priority = request.form.get('priority')
        client_name = request.form.get('client_name', '')
        deadline_str = request.form.get('deadline', '')
        remark = request.form.get('remark', '')
        
        deadline = None
        if deadline_str:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
        task = Task(
            task_name=task_name,
            description=description,
            priority=priority,
            department_id=dept_id,
            created_by_id=current_user.id,
            client_name=client_name,
            deadline=deadline,
            remark=remark
        )
        db.session.add(task)
        db.session.flush()
        
        # Assign to team members
        assign_to = request.form.getlist('assign_to[]')
        for user_id in assign_to:
            if user_id:
                member = User.query.get(int(user_id))
                if member and member.department_id == dept_id:
                    assignment = TaskAssignment(
                        task_id=task.id,
                        user_id=member.id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(assignment)
        
        db.session.commit()
        flash('Task created successfully', 'success')
        return redirect(url_for('dept_head.dashboard'))
    
    members = User.query.filter_by(department_id=dept_id, role='team_member').all()
    return render_template('dept_head/create_task.html', members=members)

@dept_head_bp.route('/tasks/<int:task_id>/reassign', methods=['GET', 'POST'])
@login_required
@dept_head_required
def reassign_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.department_id != current_user.department_id:
        flash('You can only reassign tasks from your department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    if request.method == 'POST':
        new_dept_head_id = request.form.get('new_dept_head_id')
        new_dept_head = User.query.get(new_dept_head_id)
        
        if not new_dept_head or new_dept_head.role != 'department_head':
            flash('Invalid department head selected', 'error')
            return redirect(url_for('dept_head.reassign_task', task_id=task_id))
        
        # Update task department
        task.department_id = new_dept_head.department_id
        
        # Remove old assignments and assign to new department head
        TaskAssignment.query.filter_by(task_id=task_id).delete()
        assignment = TaskAssignment(
            task_id=task.id,
            user_id=new_dept_head.id,
            assigned_by_id=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Task reassigned successfully', 'success')
        return redirect(url_for('dept_head.dashboard'))
    
    # Get all department heads
    dept_heads = User.query.filter_by(role='department_head').all()
    return render_template('dept_head/reassign_task.html', task=task, dept_heads=dept_heads)

@dept_head_bp.route('/tasks/<int:task_id>/forward', methods=['GET', 'POST'])
@login_required
@dept_head_required
def forward_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.department_id != current_user.department_id:
        flash('You can only forward tasks from your department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    if request.method == 'POST':
        assign_to = request.form.getlist('assign_to[]')
        for user_id in assign_to:
            if user_id:
                member = User.query.get(int(user_id))
                if member and member.department_id == current_user.department_id:
                    # Check if assignment already exists
                    existing = TaskAssignment.query.filter_by(task_id=task_id, user_id=member.id).first()
                    if not existing:
                        assignment = TaskAssignment(
                            task_id=task.id,
                            user_id=member.id,
                            assigned_by_id=current_user.id
                        )
                        db.session.add(assignment)
        
        db.session.commit()
        flash('Task forwarded successfully', 'success')
        return redirect(url_for('dept_head.dashboard'))
    
    members = User.query.filter_by(department_id=current_user.department_id, role='team_member').all()
    current_assignments = [a.user_id for a in task.assignments]
    return render_template('dept_head/forward_task.html', task=task, members=members, current_assignments=current_assignments)

