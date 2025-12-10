from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template
from flask_login import login_required, current_user
from models import db, Task, Subtask
from utils import can_access_task
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/<int:task_id>/subtasks/add', methods=['POST'])
@login_required
def add_subtask(task_id):
    task = Task.query.get_or_404(task_id)
    
    if not can_access_task(current_user, task):
        flash('You do not have permission to access this task', 'error')
        return redirect(url_for('index'))
    
    subtask_name = request.form.get('subtask_name')
    description = request.form.get('description', '')
    
    subtask = Subtask(
        task_id=task.id,
        subtask_name=subtask_name,
        description=description,
        created_by_id=current_user.id
    )
    db.session.add(subtask)
    db.session.commit()
    flash('Subtask added successfully', 'success')
    
    # Redirect based on role
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'department_head':
        return redirect(url_for('dept_head.dashboard'))
    else:
        return redirect(url_for('team_member.dashboard'))

@tasks_bp.route('/subtasks/<int:subtask_id>/update-status', methods=['POST'])
@login_required
def update_subtask_status(subtask_id):
    subtask = Subtask.query.get_or_404(subtask_id)
    task = subtask.task
    
    if not can_access_task(current_user, task):
        flash('You do not have permission to access this task', 'error')
        return redirect(url_for('index'))
    
    new_status = request.form.get('status')
    subtask.status = new_status
    db.session.commit()
    flash('Subtask status updated successfully', 'success')
    
    # Redirect based on role
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'department_head':
        return redirect(url_for('dept_head.dashboard'))
    else:
        return redirect(url_for('team_member.dashboard'))

@tasks_bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if not can_access_task(current_user, task):
        flash('You do not have permission to access this task', 'error')
        return redirect(url_for('index'))
    
    return render_template('shared/task_detail.html', task=task, datetime=datetime)

