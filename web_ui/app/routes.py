from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from . import db, User, Record
from .utils import admin_required, check_owner, publish_task

auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)
records_bp = Blueprint('records', __name__)
admin_bp = Blueprint('admin', __name__)

# --- Auth Routes ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash('Your account is deactivated.', 'warning')
            return redirect(url_for('auth.login'))
        login_user(user, remember=remember)
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# --- Main Routes ---
@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@main_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# --- Records CRUD ---
@records_bp.route('/records')
@login_required
def list_records():
    if current_user.role == 'admin':
        records = Record.query.all()
    else:
        records = Record.query.filter_by(owner_id=current_user.id).all()
    return render_template('records/list.html', records=records)

import uuid

@records_bp.route('/records/new', methods=['GET', 'POST'])
@login_required
def create_record():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Prepare data for RabbitMQ - including owner and correlation ID
        # No DB write here!
        task_data = {
            'operation': 'record_create',
            'request_id': str(uuid.uuid4()),
            'owner_id': current_user.id,
            'title': title,
            'description': description
        }
        
        if publish_task(task_data):
            flash('Record creation request accepted!', 'info')
            return redirect(url_for('records.list_records'))
        else:
            flash('Failed to submit task to queue.', 'danger')
            return redirect(url_for('records.list_records'))
            
    return render_template('records/form.html', action="Create")

@records_bp.route('/records/<int:id>')
@login_required
def view_record(id):
    record = Record.query.get_or_404(id)
    if not check_owner(record):
        abort(403)
    return render_template('records/view.html', record=record)

@records_bp.route('/records/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_record(id):
    record = Record.query.get_or_404(id)
    if not check_owner(record):
        abort(403)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Mark as updating locally
        record.status = 'updating'
        db.session.commit()
        
        task_data = {
            'operation': 'record_update',
            'record_id': id,
            'request_id': str(uuid.uuid4()),
            'requested_by': current_user.email,
            'patch': {
                'title': title,
                'description': description
            }
        }
        
        if publish_task(task_data):
            flash('Record update request accepted!', 'info')
        else:
            flash('Failed to submit update task.', 'danger')
            
        return redirect(url_for('records.list_records'))
    return render_template('records/form.html', record=record, action="Edit")

@records_bp.route('/records/<int:id>/delete', methods=['POST'])
@login_required
def delete_record(id):
    record = Record.query.get_or_404(id)
    if not check_owner(record):
        abort(403)
    
    # Mark as deleting locally
    record.status = 'deleting'
    db.session.commit()
    
    task_data = {
        'operation': 'record_delete',
        'record_id': id,
        'request_id': str(uuid.uuid4()),
        'requested_by': current_user.email
    }
    
    if publish_task(task_data):
        flash('Record deletion request accepted!', 'info')
    else:
        flash('Failed to submit deletion task.', 'danger')
        
    return redirect(url_for('records.list_records'))

# --- Admin Routes ---
@admin_bp.route('/admin/users')
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Check locally for immediate feedback (optional but good)
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        task_data = {
            'operation': 'user_create',
            'request_id': str(uuid.uuid4()),
            'requested_by': current_user.email,
            'user': {
                'email': email,
                'password': password,  # Note: Hashing will happen in worker
                'role': role
            }
        }
        
        if publish_task(task_data):
            flash('User creation request accepted!', 'info')
        else:
            flash('Failed to submit user creation task.', 'danger')
            
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', action="Create")

@admin_bp.route('/admin/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role')
        
        task_data = {
            'operation': 'user_update',
            'user_id': id,
            'request_id': str(uuid.uuid4()),
            'requested_by': current_user.email,
            'patch': {
                'email': email,
                'role': role
            }
        }
        
        if publish_task(task_data):
            flash('User update request accepted!', 'info')
        else:
            flash('Failed to submit user update task.', 'danger')
            
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/admin/users/<int:id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
    else:
        task_data = {
            'operation': 'user_update',
            'user_id': id,
            'request_id': str(uuid.uuid4()),
            'requested_by': current_user.email,
            'patch': {
                'is_active': not user.is_active
            }
        }
        if publish_task(task_data):
            flash('User update request accepted!', 'info')
        else:
            flash('Failed to submit user update task.', 'danger')
            
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/admin/users/<int:id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    new_password = request.form.get('new_password')
    if new_password:
        task_data = {
            'operation': 'user_update',
            'user_id': id,
            'request_id': str(uuid.uuid4()),
            'requested_by': current_user.email,
            'patch': {
                'password': new_password
            }
        }
        if publish_task(task_data):
            flash('User password reset request accepted!', 'info')
        else:
            flash('Failed to submit password reset task.', 'danger')
    else:
        flash('Password cannot be empty.', 'danger')
    return redirect(url_for('admin.list_users'))
