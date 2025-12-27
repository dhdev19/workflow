from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Task, TaskAssignment, Subtask, TaskDepartmentAssignment, DepartmentTaskCompletion
from datetime import datetime

team_member_bp = Blueprint('team_member', __name__)

@team_member_bp.route('/dashboard')
@login_required
def dashboard():
    # Get tasks assigned to current user
    assigned_task_ids = [a.task_id for a in TaskAssignment.query.filter_by(user_id=current_user.id).all()]
    
    if not assigned_task_ids:
        tasks = []
    else:
        tasks_query = Task.query.filter(Task.id.in_(assigned_task_ids))
        
        # Apply filters
        task_name = request.args.get('task_name', '')
        status = request.args.get('status', '')
        priority = request.args.get('priority', '')
        client_name = request.args.get('client_name', '')
        
        if task_name:
            tasks_query = tasks_query.filter(Task.task_name.ilike(f'%{task_name}%'))
        if status:
            tasks_query = tasks_query.filter(Task.status == status)
        if priority:
            tasks_query = tasks_query.filter(Task.priority == priority)
        if client_name:
            tasks_query = tasks_query.filter(Task.client_name.ilike(f'%{client_name}%'))
        
        tasks = tasks_query.order_by(Task.created_at.desc()).all()
    
    return render_template('team_member/dashboard.html', 
                         tasks=tasks,
                         filters={
                             'task_name': request.args.get('task_name', ''),
                             'status': request.args.get('status', ''),
                             'priority': request.args.get('priority', ''),
                             'client_name': request.args.get('client_name', '')
                         })

@team_member_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if not current_user.department_id:
        flash('You are not assigned to any department', 'error')
        return redirect(url_for('team_member.dashboard'))
    
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
            department_id=current_user.department_id,
            created_by_id=current_user.id,
            client_name=client_name,
            deadline=deadline,
            remark=remark
        )
        db.session.add(task)
        db.session.commit()
        flash('Task created successfully', 'success')
        return redirect(url_for('team_member.dashboard'))
    
    return render_template('team_member/create_task.html')

@team_member_bp.route('/tasks/<int:task_id>/update-status', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Verify user is assigned to this task
    assignment = TaskAssignment.query.filter_by(task_id=task_id, user_id=current_user.id).first()
    if not assignment:
        flash('You are not assigned to this task', 'error')
        return redirect(url_for('team_member.dashboard'))
    
    new_status = request.form.get('status')
    
    task.status = new_status
    
    # If task has department assignments and status is COMPLETED,
    # note that department completion logic may override this
    dept_assignments = TaskDepartmentAssignment.query.filter_by(task_id=task_id).all()
    if dept_assignments and new_status == 'COMPLETED':
        # Check if all departments have completed
        all_depts_completed = True
        for dept_assignment in dept_assignments:
            completion = DepartmentTaskCompletion.query.filter_by(
                task_id=task_id,
                department_id=dept_assignment.department_id
            ).first()
            if not completion or not completion.is_completed:
                all_depts_completed = False
                break
        
        if not all_depts_completed:
            flash('Task marked as complete. Note: This task involves multiple departments. The overall completion status will be updated when all departments finish their work.', 'info')
        else:
            flash('Task status updated successfully', 'success')
    else:
        flash('Task status updated successfully', 'success')
    
    db.session.commit()
    return redirect(url_for('team_member.dashboard'))

