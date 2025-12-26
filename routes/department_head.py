from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Department, Task, TaskAssignment, Subtask, TaskDepartmentAssignment, DepartmentTaskCompletion
from extensions import bcrypt
from utils import dept_head_required
from datetime import datetime
from sqlalchemy import or_

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
    
    # Get tasks that belong to this department OR are assigned to this department
    # Get task IDs assigned to this department via TaskDepartmentAssignment
    assigned_task_ids = [a.task_id for a in TaskDepartmentAssignment.query.filter_by(department_id=dept_id).all()]
    
    # Query tasks: either primary department matches OR task is assigned to this department
    if assigned_task_ids:
        tasks = Task.query.filter(
            or_(
                Task.department_id == dept_id,
                Task.id.in_(assigned_task_ids)
            )
        ).order_by(Task.created_at.desc()).all()
    else:
        # If no assigned tasks, just get primary department tasks
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
        
        # Assign to departments (including own department)
        assign_to_depts = request.form.getlist('assign_to_dept[]')
        for dept_id_str in assign_to_depts:
            if dept_id_str:
                assigned_dept_id = int(dept_id_str)
                # Check if assignment already exists
                existing = TaskDepartmentAssignment.query.filter_by(
                    task_id=task.id,
                    department_id=assigned_dept_id
                ).first()
                if not existing:
                    dept_assignment = TaskDepartmentAssignment(
                        task_id=task.id,
                        department_id=assigned_dept_id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(dept_assignment)
                    
                    # Initialize completion status
                    completion = DepartmentTaskCompletion(
                        task_id=task.id,
                        department_id=assigned_dept_id,
                        is_completed=False
                    )
                    db.session.add(completion)
        
        db.session.commit()
        flash('Task created successfully', 'success')
        return redirect(url_for('dept_head.dashboard'))
    
    members = User.query.filter_by(department_id=dept_id, role='team_member').all()
    departments = Department.query.all()
    return render_template('dept_head/create_task.html', members=members, departments=departments)

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
    
    if not current_user.department_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    # Check if task belongs to user's department OR is assigned to user's department
    can_access = False
    if task.department_id == current_user.department_id:
        can_access = True
    else:
        # Check if task is assigned to user's department via TaskDepartmentAssignment
        dept_assignment = TaskDepartmentAssignment.query.filter_by(
            task_id=task_id,
            department_id=current_user.department_id
        ).first()
        if dept_assignment:
            can_access = True
    
    if not can_access:
        flash('You can only forward tasks from your department or tasks assigned to your department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    if request.method == 'POST':
        assign_to = request.form.getlist('assign_to[]')
        # Convert to integers
        checked_user_ids = {int(user_id) for user_id in assign_to if user_id}
        
        # Get all team members in the department
        dept_members = User.query.filter_by(
            department_id=current_user.department_id, 
            role='team_member'
        ).all()
        
        # Get current assignments for team members only
        current_assignments = TaskAssignment.query.filter_by(task_id=task_id).join(
            User, TaskAssignment.user_id == User.id
        ).filter(User.role == 'team_member').all()
        
        # Remove assignments for unchecked users
        for assignment in current_assignments:
            if assignment.user_id not in checked_user_ids:
                db.session.delete(assignment)
        
        # Add assignments for checked users who don't have one yet
        existing_user_ids = {a.user_id for a in current_assignments}
        for member in dept_members:
            if member.id in checked_user_ids and member.id not in existing_user_ids:
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

@dept_head_bp.route('/tasks/<int:task_id>/assign-departments', methods=['GET', 'POST'])
@login_required
@dept_head_required
def assign_departments(task_id):
    task = Task.query.get_or_404(task_id)
    
    if not current_user.department_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    # Department heads can assign departments to tasks from their department OR tasks assigned to their department
    can_access = False
    if task.department_id == current_user.department_id:
        can_access = True
    else:
        # Check if task is assigned to user's department via TaskDepartmentAssignment
        dept_assignment = TaskDepartmentAssignment.query.filter_by(
            task_id=task_id,
            department_id=current_user.department_id
        ).first()
        if dept_assignment:
            can_access = True
    
    if not can_access:
        flash('You can only assign departments to tasks from your department or tasks assigned to your department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    if request.method == 'POST':
        # Get selected departments
        assign_to_depts = request.form.getlist('assign_to_dept[]')
        checked_dept_ids = {int(dept_id) for dept_id in assign_to_depts if dept_id}
        
        # Get current department assignments
        current_dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task_id).all()
        current_dept_ids = {a.department_id for a in current_dept_assignments}
        
        # Remove assignments for unchecked departments
        for assignment in current_dept_assignments:
            if assignment.department_id not in checked_dept_ids:
                db.session.delete(assignment)
                # Also remove completion status if exists
                completion = DepartmentTaskCompletion.query.filter_by(
                    task_id=task_id, 
                    department_id=assignment.department_id
                ).first()
                if completion:
                    db.session.delete(completion)
        
        # Add assignments for checked departments that don't have one yet
        for dept_id in checked_dept_ids:
            if dept_id not in current_dept_ids:
                dept_assignment = TaskDepartmentAssignment(
                    task_id=task.id,
                    department_id=dept_id,
                    assigned_by_id=current_user.id
                )
                db.session.add(dept_assignment)
                
                # Initialize completion status
                completion = DepartmentTaskCompletion(
                    task_id=task.id,
                    department_id=dept_id,
                    is_completed=False
                )
                db.session.add(completion)
        
        # Update overall task status based on department completions
        _update_task_completion_status(task)
        
        db.session.commit()
        flash('Task assigned to departments successfully', 'success')
        return redirect(url_for('dept_head.dashboard'))
    
    departments = Department.query.all()
    current_dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task_id).all()
    current_dept_ids = {a.department_id for a in current_dept_assignments}
    
    return render_template('dept_head/assign_departments.html', 
                         task=task, 
                         departments=departments,
                         current_dept_ids=current_dept_ids)

def _update_task_completion_status(task):
    """Update task status to COMPLETED only if all assigned departments have completed"""
    dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task.id).all()
    
    if not dept_assignments:
        # No department assignments, keep current status logic
        return
    
    # Check if all departments have completed
    all_completed = True
    for dept_assignment in dept_assignments:
        completion = DepartmentTaskCompletion.query.filter_by(
            task_id=task.id,
            department_id=dept_assignment.department_id
        ).first()
        
        if not completion or not completion.is_completed:
            all_completed = False
            break
    
    # Update task status
    if all_completed and dept_assignments:
        task.status = 'COMPLETED'
    elif task.status == 'COMPLETED':
        # If task was marked complete but not all departments are done, revert to ASSIGNED
        task.status = 'ASSIGNED'

@dept_head_bp.route('/tasks/<int:task_id>/mark-department-complete', methods=['POST'])
@login_required
@dept_head_required
def mark_department_complete(task_id):
    task = Task.query.get_or_404(task_id)
    
    if not current_user.department_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    # Check if this department is assigned to the task
    dept_assignment = TaskDepartmentAssignment.query.filter_by(
        task_id=task_id,
        department_id=current_user.department_id
    ).first()
    
    if not dept_assignment:
        flash('Your department is not assigned to this task', 'error')
        return redirect(url_for('dept_head.dashboard'))
    
    # Get or create completion record
    completion = DepartmentTaskCompletion.query.filter_by(
        task_id=task_id,
        department_id=current_user.department_id
    ).first()
    
    if not completion:
        completion = DepartmentTaskCompletion(
            task_id=task.id,
            department_id=current_user.department_id,
            is_completed=False
        )
        db.session.add(completion)
    
    # Toggle completion status
    completion.is_completed = not completion.is_completed
    if completion.is_completed:
        completion.completed_at = datetime.utcnow()
        completion.completed_by_id = current_user.id
        flash('Your department has been marked as completed for this task', 'success')
    else:
        completion.completed_at = None
        completion.completed_by_id = None
        flash('Your department completion status has been removed', 'info')
    
    # Update overall task status
    _update_task_completion_status(task)
    
    db.session.commit()
    return redirect(url_for('tasks.view_task', task_id=task_id))

