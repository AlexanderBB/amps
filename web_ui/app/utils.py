from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin' or not current_user.is_active:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def check_owner(record):
    if current_user.role == 'admin':
        return True
    return record.owner_id == current_user.id
