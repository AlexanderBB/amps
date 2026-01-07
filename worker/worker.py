import pika
import time
import os
import json
import psycopg2

DB_USER = os.environ.get('POSTGRES_USER', 'admin')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'securepassword')
DB_HOST = os.environ.get('POSTGRES_HOST', 'db')
DB_NAME = os.environ.get('POSTGRES_DB', 'appdb')

from datetime import datetime

def create_record_in_db(owner_id, title, description):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        # INSERT the record only after processing
        cur.execute(
            "INSERT INTO records (owner_id, title, description, status, processed_at, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (owner_id, title, description, 'completed', datetime.utcnow(), datetime.utcnow(), datetime.utcnow())
        )
        record_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return record_id
    except Exception as e:
        print(f"Error creating record in DB: {e}")
        return None

def update_record_in_db(record_id, patch):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        
        # Build dynamic UPDATE query
        set_clause = []
        params = []
        for key, value in patch.items():
            set_clause.append(f"{key} = %s")
            params.append(value)
        
        set_clause.append("status = %s")
        params.append('completed')
        set_clause.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        params.append(record_id)
        
        query = f"UPDATE records SET {', '.join(set_clause)} WHERE id = %s"
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating record in DB: {e}")
        return False

def delete_record_from_db(record_id):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM records WHERE id = %s", (record_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting record from DB: {e}")
        return False

from werkzeug.security import generate_password_hash

def is_admin(email):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row and row[0] == 'admin'
    except Exception:
        return False

def create_user_in_db(user_data):
    try:
        email = user_data['email']
        password = user_data['password']
        role = user_data.get('role', 'user')
        password_hash = generate_password_hash(password)
        
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password_hash, role, is_active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (email, password_hash, role, True, datetime.utcnow(), datetime.utcnow())
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return user_id
    except Exception as e:
        print(f"Error creating user in DB: {e}")
        return None

def update_user_in_db(user_id, patch):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        
        set_clause = []
        params = []
        for key, value in patch.items():
            if key == 'password':
                set_clause.append("password_hash = %s")
                params.append(generate_password_hash(value))
            else:
                set_clause.append(f"{key} = %s")
                params.append(value)
        
        set_clause.append("updated_at = %s")
        params.append(datetime.utcnow())
        
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(set_clause)} WHERE id = %s"
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating user in DB: {e}")
        return False

def callback(ch, method, properties, body):
    data = json.loads(body)
    operation = data.get('operation', 'record_create')
    request_id = data.get('request_id')
    requested_by = data.get('requested_by')
    
    print(f"Processing {operation} request {request_id} by {requested_by}")
    time.sleep(5)  # Simulate work
    
    # Permission check for admin operations
    if operation.startswith('user_') and not is_admin(requested_by):
        print(f"Unauthorized access attempt by {requested_by} for {operation}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    success = False
    if operation == 'record_create':
        owner_id = data.get('owner_id')
        title = data.get('title')
        description = data.get('description', '')
        record_id = create_record_in_db(owner_id, title, description)
        success = record_id is not None
    elif operation == 'record_update':
        record_id = data.get('record_id')
        patch = data.get('patch', {})
        success = update_record_in_db(record_id, patch)
    elif operation == 'record_delete':
        record_id = data.get('record_id')
        success = delete_record_from_db(record_id)
    elif operation == 'user_create':
        user_data = data.get('user', {})
        success = create_user_in_db(user_data) is not None
    elif operation == 'user_update':
        user_id = data.get('user_id')
        patch = data.get('patch', {})
        success = update_user_in_db(user_id, patch)
    
    if success:
        print(f"Operation {operation} completed successfully for request {request_id}")
    else:
        print(f"Operation {operation} failed for request {request_id}")
        
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    rabbit_host = os.environ.get('RABBITMQ_HOST', 'rabbitmq')
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbit_host))
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ not ready, retrying...")
            time.sleep(2)

    channel = connection.channel()
    channel.queue_declare(queue='task_queue', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='task_queue', on_message_callback=callback)

    print('Worker waiting for messages...')
    channel.start_consuming()

if __name__ == '__main__':
    main()
