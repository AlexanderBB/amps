import os
import json
import pika
from functools import wraps
from flask import abort
from flask_login import current_user

def publish_task(task_data):
    rabbit_host = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbit_host))
        channel = connection.channel()
        channel.queue_declare(queue='task_queue', durable=True)
        message = json.dumps(task_data)
        channel.basic_publish(
            exchange='',
            routing_key='task_queue',
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        return True
    except Exception as e:
        print(f"Failed to publish task: {e}")
        return False

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
