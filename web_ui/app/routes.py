from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from . import db, User, Record
from .utils import admin_required, check_owner

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

@records_bp.route('/records/new', methods=['GET', 'POST'])
@login_required
def create_record():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        new_record = Record(title=title, description=description, owner_id=current_user.id)
        db.session.add(new_record)
        db.session.commit()
        flash('Record created successfully!', 'success')
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
        record.title = request.form.get('title')
        record.description = request.form.get('description')
        db.session.commit()
        flash('Record updated successfully!', 'success')
        return redirect(url_for('records.list_records'))
    return render_template('records/form.html', record=record, action="Edit")

@records_bp.route('/records/<int:id>/delete', methods=['POST'])
@login_required
def delete_record(id):
    record = Record.query.get_or_404(id)
    if not check_owner(record):
        abort(403)
    db.session.delete(record)
    db.session.commit()
    flash('Record deleted successfully!', 'success')
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
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('admin.create_user'))
            
        new_user = User(email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', action="Create")

@admin_bp.route('/admin/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/admin/users/<int:id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f'User {"activated" if user.is_active else "deactivated"} successfully!', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/admin/users/<int:id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    new_password = request.form.get('new_password')
    if new_password:
        user.set_password(new_password)
        db.session.commit()
        flash('Password reset successfully!', 'success')
    else:
        flash('Password cannot be empty.', 'danger')
    return redirect(url_for('admin.list_users'))
