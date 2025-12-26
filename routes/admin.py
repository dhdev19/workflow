from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Department, Task, TaskAssignment, Subtask, TaskDepartmentAssignment, DepartmentTaskCompletion
from extensions import bcrypt
from utils import admin_required
from datetime import datetime
from sqlalchemy import or_

admin_bp = Blueprint('admin', __name__)

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

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get all tasks with filters
    tasks_query = Task.query
    
    # Apply filters
    task_name = request.args.get('task_name', '')
    status = request.args.get('status', '')
    department_id = request.args.get('department_id', '')
    client_name = request.args.get('client_name', '')
    
    if task_name:
        tasks_query = tasks_query.filter(Task.task_name.ilike(f'%{task_name}%'))
    if status:
        tasks_query = tasks_query.filter(Task.status == status)
    if department_id:
        tasks_query = tasks_query.filter(Task.department_id == department_id)
    if client_name:
        tasks_query = tasks_query.filter(Task.client_name.ilike(f'%{client_name}%'))
    
    tasks = tasks_query.order_by(Task.created_at.desc()).all()
    departments = Department.query.all()
    
    # Analytics data
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='COMPLETED').count()
    pending_tasks = Task.query.filter_by(status='PENDING').count()
    urgent_tasks = Task.query.filter_by(priority='URGENT').count()
    
    return render_template('admin/dashboard.html', 
                         tasks=tasks, 
                         departments=departments,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         urgent_tasks=urgent_tasks,
                         filters={
                             'task_name': task_name,
                             'status': status,
                             'department_id': department_id,
                             'client_name': client_name
                         })

@admin_bp.route('/departments')
@login_required
@admin_required
def departments():
    departments = Department.query.all()
    return render_template('admin/departments.html', departments=departments)

@admin_bp.route('/departments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_department():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if Department.query.filter_by(name=name).first():
            flash('Department with this name already exists', 'error')
            return redirect(url_for('admin.add_department'))
        
        dept = Department(name=name, description=description)
        db.session.add(dept)
        db.session.commit()
        flash('Department added successfully', 'success')
        return redirect(url_for('admin.departments'))
    
    return render_template('admin/add_department.html')

@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    flash('Department deleted successfully', 'success')
    return redirect(url_for('admin.departments'))

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    departments = Department.query.all()
    return render_template('admin/users.html', users=users, departments=departments)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        role = request.form.get('role')
        department_id = request.form.get('department_id') or None
        
        if User.query.filter_by(email=email).first():
            flash('User with this email already exists', 'error')
            return redirect(url_for('admin.add_user'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('admin.add_user'))
        
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            role=role,
            department_id=department_id
        )
        db.session.add(user)
        db.session.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('admin.users'))
    
    departments = Department.query.all()
    return render_template('admin/add_user.html', departments=departments)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task():
    if request.method == 'POST':
        task_name = request.form.get('task_name')
        description = request.form.get('description', '')
        priority = request.form.get('priority')
        department_id = request.form.get('department_id')
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
            department_id=department_id,
            created_by_id=current_user.id,
            client_name=client_name,
            deadline=deadline,
            remark=remark
        )
        db.session.add(task)
        db.session.flush()
        
        # Assign to department heads, members, or departments
        assign_to = request.form.getlist('assign_to[]')
        assign_type = request.form.getlist('assign_type[]')
        
        for i, user_id in enumerate(assign_to):
            if assign_type[i] == 'user' and user_id:
                assignment = TaskAssignment(
                    task_id=task.id,
                    user_id=int(user_id),
                    assigned_by_id=current_user.id
                )
                db.session.add(assignment)
            elif assign_type[i] == 'department' and user_id:
                # Assign to all members of department
                dept = Department.query.get(int(user_id))
                if dept:
                    for member in dept.members:
                        assignment = TaskAssignment(
                            task_id=task.id,
                            user_id=member.id,
                            assigned_by_id=current_user.id
                        )
                        db.session.add(assignment)
        
        db.session.commit()
        flash('Task created successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    departments = Department.query.all()
    users = User.query.filter(User.role.in_(['department_head', 'team_member'])).all()
    return render_template('admin/create_task.html', departments=departments, users=users)

@admin_bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        task.task_name = request.form.get('task_name')
        task.description = request.form.get('description', '')
        task.priority = request.form.get('priority')
        task.department_id = request.form.get('department_id')
        task.client_name = request.form.get('client_name', '')
        task.remark = request.form.get('remark', '')
        deadline_str = request.form.get('deadline', '')
        
        if deadline_str:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        else:
            task.deadline = None
        
        db.session.commit()
        flash('Task updated successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    departments = Department.query.all()
    return render_template('admin/edit_task.html', task=task, departments=departments)

@admin_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/tasks/<int:task_id>/assign', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        # Remove existing assignments
        TaskAssignment.query.filter_by(task_id=task_id).delete()
        
        # Add new assignments
        assign_to = request.form.getlist('assign_to[]')
        assign_type = request.form.getlist('assign_type[]')
        
        for i, user_id in enumerate(assign_to):
            if assign_type[i] == 'user' and user_id:
                assignment = TaskAssignment(
                    task_id=task.id,
                    user_id=int(user_id),
                    assigned_by_id=current_user.id
                )
                db.session.add(assignment)
            elif assign_type[i] == 'department' and user_id:
                dept = Department.query.get(int(user_id))
                if dept:
                    for member in dept.members:
                        assignment = TaskAssignment(
                            task_id=task.id,
                            user_id=member.id,
                            assigned_by_id=current_user.id
                        )
                        db.session.add(assignment)
        
        db.session.commit()
        flash('Task assignments updated successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    departments = Department.query.all()
    users = User.query.filter(User.role.in_(['department_head', 'team_member'])).all()
    current_assignments = [a.user_id for a in task.assignments]
    return render_template('admin/assign_task.html', 
                         task=task, 
                         departments=departments, 
                         users=users,
                         current_assignments=current_assignments)

@admin_bp.route('/tasks/<int:task_id>/reassign', methods=['GET', 'POST'])
@login_required
@admin_required
def reassign_task(task_id):
    task = Task.query.get_or_404(task_id)
    
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
        flash('Task reassigned to departments successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    departments = Department.query.all()
    current_dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task_id).all()
    current_dept_ids = {a.department_id for a in current_dept_assignments}
    
    return render_template('admin/reassign_task.html', 
                         task=task, 
                         departments=departments,
                         current_dept_ids=current_dept_ids)

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Task statistics
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='COMPLETED').count()
    pending_tasks = Task.query.filter_by(status='PENDING').count()
    assigned_tasks = Task.query.filter_by(status='ASSIGNED').count()
    urgent_tasks = Task.query.filter_by(priority='URGENT').count()
    important_tasks = Task.query.filter_by(priority='IMPORTANT').count()
    daily_tasks = Task.query.filter_by(priority='DAILY TASK').count()
    
    # Department statistics
    departments = Department.query.all()
    dept_stats = []
    for dept in departments:
        dept_tasks = Task.query.filter_by(department_id=dept.id).count()
        dept_completed = Task.query.filter_by(department_id=dept.id, status='COMPLETED').count()
        dept_stats.append({
            'name': dept.name,
            'total': dept_tasks,
            'completed': dept_completed
        })
    
    # User statistics
    total_users = User.query.count()
    admins = User.query.filter_by(role='admin').count()
    dept_heads = User.query.filter_by(role='department_head').count()
    team_members = User.query.filter_by(role='team_member').count()
    
    return render_template('admin/analytics.html',
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         assigned_tasks=assigned_tasks,
                         urgent_tasks=urgent_tasks,
                         important_tasks=important_tasks,
                         daily_tasks=daily_tasks,
                         dept_stats=dept_stats,
                         total_users=total_users,
                         admins=admins,
                         dept_heads=dept_heads,
                         team_members=team_members)

