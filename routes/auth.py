from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from extensions import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            user = User.query.filter_by(email=email, is_active=True).first()
        except Exception as e:
            # Handle database connection errors
            from sqlalchemy.exc import OperationalError
            if isinstance(e, OperationalError) and 'gone away' in str(e).lower():
                # Try to reconnect
                from extensions import db
                db.session.rollback()
                user = User.query.filter_by(email=email, is_active=True).first()
            else:
                flash('Database connection error. Please try again.', 'error')
                return render_template('auth/login.html')
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'department_head':
                return redirect(url_for('dept_head.dashboard'))
            elif user.role == 'team_member':
                return redirect(url_for('team_member.dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

