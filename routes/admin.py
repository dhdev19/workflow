from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Department, Task, TaskAssignment, Subtask, TaskDepartmentAssignment, DepartmentTaskCompletion, TaskApprovalRequest
from extensions import bcrypt
from utils import admin_required
from datetime import datetime
from sqlalchemy import or_
import json

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
    priority = request.args.get('priority', '')
    
    if task_name:
        tasks_query = tasks_query.filter(Task.task_name.ilike(f'%{task_name}%'))
    if status:
        tasks_query = tasks_query.filter(Task.status == status)
    if department_id:
        tasks_query = tasks_query.filter(Task.department_id == department_id)
    if client_name:
        tasks_query = tasks_query.filter(Task.client_name.ilike(f'%{client_name}%'))
    if priority:
        tasks_query = tasks_query.filter(Task.priority == priority)
    
    tasks = tasks_query.order_by(Task.created_at.desc()).all()
    departments = Department.query.all()
    
    # Analytics data
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='COMPLETED').count()
    pending_tasks = Task.query.filter_by(status='PENDING').count()
    
    # Pending approvals count
    pending_approvals = TaskApprovalRequest.query.filter_by(status='PENDING').count()
    urgent_tasks = Task.query.filter_by(priority='URGENT').count()
    
    return render_template('admin/dashboard.html', 
                         tasks=tasks, 
                         departments=departments,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         urgent_tasks=urgent_tasks,
                         pending_approvals=pending_approvals,
                         filters={
                             'task_name': task_name,
                             'status': status,
                             'department_id': department_id,
                             'client_name': client_name,
                             'priority': priority
                         })

@admin_bp.route('/departments')
@login_required
@admin_required
def departments():
    departments = Department.query.all()
    # Get department heads separately since the head relationship is viewonly with complex join
    dept_heads = {}
    for dept in departments:
        head = User.query.filter_by(department_id=dept.id, role='department_head').first()
        if head:
            dept_heads[dept.id] = head
    return render_template('admin/departments.html', departments=departments, dept_heads=dept_heads)

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

@admin_bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Check if name already exists (excluding current department)
        existing_dept = Department.query.filter_by(name=name).first()
        if existing_dept and existing_dept.id != dept_id:
            flash('Department with this name already exists', 'error')
            return redirect(url_for('admin.edit_department', dept_id=dept_id))
        
        # Update department details
        dept.name = name
        dept.description = description
        
        # Get selected member IDs
        member_ids = request.form.getlist('member_ids[]')
        selected_member_ids = {int(mid) for mid in member_ids if mid}
        
        # Get current members
        current_members = User.query.filter_by(department_id=dept_id).all()
        current_member_ids = {m.id for m in current_members}
        
        # Remove members that are unchecked
        for member in current_members:
            if member.id not in selected_member_ids:
                member.department_id = None
        
        # Add new members
        for member_id in selected_member_ids:
            if member_id not in current_member_ids:
                member = User.query.get(member_id)
                if member:
                    member.department_id = dept_id
        
        db.session.commit()
        flash('Department updated successfully', 'success')
        return redirect(url_for('admin.departments'))
    
    # Get all users for selection
    all_users = User.query.filter(User.role.in_(['department_head', 'team_member'])).all()
    current_member_ids = {m.id for m in dept.members}
    
    return render_template('admin/edit_department.html', 
                         department=dept, 
                         all_users=all_users,
                         current_member_ids=current_member_ids)

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
        
        assigned_users = []
        for i, user_id in enumerate(assign_to):
            if assign_type[i] == 'user' and user_id:
                user = User.query.get(int(user_id))
                if user:
                    assignment = TaskAssignment(
                        task_id=task.id,
                        user_id=user.id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(assignment)
                    assigned_users.append(user)
            elif assign_type[i] == 'department' and user_id:
                # Assign to department: create TaskDepartmentAssignment and auto-assign department head
                dept = Department.query.get(int(user_id))
                if dept:
                    # Create TaskDepartmentAssignment record
                    dept_assignment = TaskDepartmentAssignment(
                        task_id=task.id,
                        department_id=dept.id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(dept_assignment)
                    
                    # Initialize completion status
                    completion = DepartmentTaskCompletion(
                        task_id=task.id,
                        department_id=dept.id,
                        is_completed=False
                    )
                    db.session.add(completion)
                    
                    # Search DB for department head for this department ID, then assign to head and call FCM
                    dept_head = User.query.filter_by(department_id=dept.id, role='department_head').first()
                    if dept_head:
                        # Check if department head is already assigned (avoid duplicate assignment record)
                        existing_assignment = TaskAssignment.query.filter_by(
                            task_id=task.id,
                            user_id=dept_head.id
                        ).first()
                        if not existing_assignment:
                            assignment = TaskAssignment(
                                task_id=task.id,
                                user_id=dept_head.id,
                                assigned_by_id=current_user.id
                            )
                            db.session.add(assignment)
                        # Always add to assigned_users for FCM notification, even if already assigned
                        if dept_head not in assigned_users:
                            assigned_users.append(dept_head)
                    else:
                        # Log if no department head found
                        from flask import current_app
                        if current_app:
                            current_app.logger.info(f"Task CREATED - No department head found for Department ID: {dept.id}, Task: '{task.task_name}' (ID: {task.id})")
        
        db.session.commit()
        
        # Log task creation
        from flask import current_app
        if current_app:
            assigned_info = f", Assigned to: {len(assigned_users)} user(s)" if assigned_users else ""
            current_app.logger.info(f"Task CREATED - ID: {task.id}, Name: '{task.task_name}', Priority: {task.priority}, Department ID: {task.department_id}, Created by: {current_user.email} (ID: {current_user.id}){assigned_info}")
        
        # Send FCM notifications to assigned users
        from utils import send_task_assignment_notification
        if assigned_users:
            for user in assigned_users:
                send_task_assignment_notification(user, task, current_user)
        else:
            # Log when no users are assigned (no notifications sent)
            from flask import current_app
            if current_app:
                current_app.logger.info(f"FCM Task Assignment Notification - NO USERS ASSIGNED - Task: '{task.task_name}' (ID: {task.id}), No users assigned to receive notification")
        
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
        
        # Log task update
        from flask import current_app
        if current_app:
            current_app.logger.info(f"Task UPDATED - ID: {task.id}, Name: '{task.task_name}', Priority: {task.priority}, Status: {task.status}, Updated by: {current_user.email} (ID: {current_user.id})")
        
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
    task_name = task.task_name
    task_id = task.id
    db.session.delete(task)
    db.session.commit()
    
    # Log task deletion
    from flask import current_app
    if current_app:
        current_app.logger.info(f"Task DELETED - ID: {task_id}, Name: '{task_name}', Deleted by: {current_user.email} (ID: {current_user.id})")
    
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
        
        assigned_users = []
        for i, user_id in enumerate(assign_to):
            if assign_type[i] == 'user' and user_id:
                user = User.query.get(int(user_id))
                if user:
                    assignment = TaskAssignment(
                        task_id=task.id,
                        user_id=user.id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(assignment)
                    assigned_users.append(user)
            elif assign_type[i] == 'department' and user_id:
                # Assign to department: create TaskDepartmentAssignment and auto-assign department head
                dept = Department.query.get(int(user_id))
                if dept:
                    # Create TaskDepartmentAssignment record
                    dept_assignment = TaskDepartmentAssignment(
                        task_id=task.id,
                        department_id=dept.id,
                        assigned_by_id=current_user.id
                    )
                    db.session.add(dept_assignment)
                    
                    # Initialize completion status
                    completion = DepartmentTaskCompletion(
                        task_id=task.id,
                        department_id=dept.id,
                        is_completed=False
                    )
                    db.session.add(completion)
                    
                    # Auto-assign to department head
                    dept_head = User.query.filter_by(department_id=dept.id, role='department_head').first()
                    if dept_head:
                        # Check if department head is already assigned (avoid duplicate)
                        existing_assignment = TaskAssignment.query.filter_by(
                            task_id=task.id,
                            user_id=dept_head.id
                        ).first()
                        if not existing_assignment:
                            assignment = TaskAssignment(
                                task_id=task.id,
                                user_id=dept_head.id,
                                assigned_by_id=current_user.id
                            )
                            db.session.add(assignment)
                            assigned_users.append(dept_head)
        
        db.session.commit()
        
        # Send FCM notifications to assigned users
        from utils import send_task_assignment_notification
        for user in assigned_users:
            send_task_assignment_notification(user, task, current_user)
        
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
        assigned_users = []
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
                
                # Auto-assign to department head
                dept_head = User.query.filter_by(department_id=dept_id, role='department_head').first()
                if dept_head:
                    # Check if department head is already assigned (avoid duplicate)
                    existing_assignment = TaskAssignment.query.filter_by(
                        task_id=task.id,
                        user_id=dept_head.id
                    ).first()
                    if not existing_assignment:
                        assignment = TaskAssignment(
                            task_id=task.id,
                            user_id=dept_head.id,
                            assigned_by_id=current_user.id
                        )
                        db.session.add(assignment)
                        assigned_users.append(dept_head)
        
        # Update overall task status based on department completions
        _update_task_completion_status(task)
        
        db.session.commit()
        
        # Log task reassignment
        from flask import current_app
        if current_app:
            dept_info = f", New departments: {len(checked_dept_ids)}" if checked_dept_ids else ""
            current_app.logger.info(f"Task REASSIGNED - ID: {task.id}, Name: '{task.task_name}', Reassigned by: {current_user.email} (ID: {current_user.id}){dept_info}")
        
        # Send FCM notifications to newly assigned department heads
        from utils import send_task_assignment_notification
        for user in assigned_users:
            send_task_assignment_notification(user, task, current_user)
        
        flash('Task reassigned to departments successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    
    departments = Department.query.all()
    current_dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task_id).all()
    current_dept_ids = {a.department_id for a in current_dept_assignments}
    
    return render_template('admin/reassign_task.html', 
                         task=task, 
                         departments=departments,
                         current_dept_ids=current_dept_ids)

@admin_bp.route('/approvals')
@login_required
@admin_required
def approvals():
    """View all pending approval requests"""
    pending_requests = TaskApprovalRequest.query.filter_by(status='PENDING').order_by(TaskApprovalRequest.created_at.desc()).all()
    departments = Department.query.all()
    return render_template('admin/approvals.html', requests=pending_requests, departments=departments)

@admin_bp.route('/approvals/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_request(request_id):
    """Approve a pending request"""
    approval_request = TaskApprovalRequest.query.get_or_404(request_id)
    
    if approval_request.status != 'PENDING':
        flash('This request has already been processed', 'error')
        return redirect(url_for('admin.approvals'))
    
    task = approval_request.task
    assigned_users = []  # Track users to notify
    
    if approval_request.request_type == 'reassign':
        # Reassign task to new department head
        new_dept_head = approval_request.new_dept_head
        if not new_dept_head or new_dept_head.role != 'department_head':
            flash('Invalid department head in request', 'error')
            return redirect(url_for('admin.approvals'))
        
        # Update task department
        task.department_id = new_dept_head.department_id
        
        # Remove old assignments and assign to new department head
        TaskAssignment.query.filter_by(task_id=task.id).delete()
        assignment = TaskAssignment(
            task_id=task.id,
            user_id=new_dept_head.id,
            assigned_by_id=approval_request.requested_by_id
        )
        db.session.add(assignment)
        
    elif approval_request.request_type == 'assign_departments':
        # Get requested department IDs
        requested_dept_ids = json.loads(approval_request.requested_department_ids) if approval_request.requested_department_ids else []
        
        # Get current department assignments
        current_dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task.id).all()
        current_dept_ids = {a.department_id for a in current_dept_assignments}
        
        # Add assignments for requested departments that don't have one yet
        for dept_id in requested_dept_ids:
            if dept_id not in current_dept_ids:
                dept_assignment = TaskDepartmentAssignment(
                    task_id=task.id,
                    department_id=dept_id,
                    assigned_by_id=approval_request.requested_by_id
                )
                db.session.add(dept_assignment)
                
                # Initialize completion status
                completion = DepartmentTaskCompletion(
                    task_id=task.id,
                    department_id=dept_id,
                    is_completed=False
                )
                db.session.add(completion)
                
                # Auto-assign to department head
                dept_head = User.query.filter_by(department_id=dept_id, role='department_head').first()
                if dept_head:
                    # Check if department head is already assigned (avoid duplicate)
                    existing_assignment = TaskAssignment.query.filter_by(
                        task_id=task.id,
                        user_id=dept_head.id
                    ).first()
                    if not existing_assignment:
                        assignment = TaskAssignment(
                            task_id=task.id,
                            user_id=dept_head.id,
                            assigned_by_id=approval_request.requested_by_id
                        )
                        db.session.add(assignment)
                        assigned_users.append(dept_head)
        
        # Update overall task status based on department completions
        _update_task_completion_status(task)
    
    # Update approval request
    approval_request.status = 'APPROVED'
    approval_request.approved_by_id = current_user.id
    approval_request.approval_notes = request.form.get('notes', '')
    approval_request.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Send FCM notifications to newly assigned department heads
    if approval_request.request_type == 'assign_departments' and assigned_users:
        from utils import send_task_assignment_notification
        for user in assigned_users:
            send_task_assignment_notification(user, task, current_user)
    elif approval_request.request_type == 'reassign':
        # Send notification to new department head
        from utils import send_task_assignment_notification
        send_task_assignment_notification(approval_request.new_dept_head, task, current_user)
    
    flash('Request approved successfully', 'success')
    return redirect(url_for('admin.approvals'))

@admin_bp.route('/approvals/<int:request_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_request(request_id):
    """Reject a pending request"""
    approval_request = TaskApprovalRequest.query.get_or_404(request_id)
    
    if approval_request.status != 'PENDING':
        flash('This request has already been processed', 'error')
        return redirect(url_for('admin.approvals'))
    
    # Update approval request
    approval_request.status = 'REJECTED'
    approval_request.approved_by_id = current_user.id
    approval_request.approval_notes = request.form.get('notes', '')
    approval_request.updated_at = datetime.utcnow()
    
    db.session.commit()
    flash('Request rejected', 'info')
    return redirect(url_for('admin.approvals'))

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
        completion_rate = ((dept_completed / dept_tasks) * 100) if dept_tasks > 0 else 0
        dept_stats.append({
            'name': dept.name,
            'total': dept_tasks,
            'completed': dept_completed,
            'completion_rate': completion_rate
        })
    
    # Sort by completion rate (descending) and assign medals to top 3
    dept_stats.sort(key=lambda x: x['completion_rate'], reverse=True)
    for i, stat in enumerate(dept_stats):
        if i == 0:
            stat['medal'] = '🥇'  # Gold
        elif i == 1:
            stat['medal'] = '🥈'  # Silver
        elif i == 2:
            stat['medal'] = '🥉'  # Bronze
        else:
            stat['medal'] = ''
    
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

