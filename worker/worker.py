import pika
import time
import os
import json
import psycopg2

DB_USER = os.environ.get('POSTGRES_USER', 'admin')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'securepassword')
DB_HOST = os.environ.get('POSTGRES_HOST', 'db')
DB_NAME = os.environ.get('POSTGRES_DB', 'appdb')

def update_db(item_id, status):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("UPDATE item SET description = %s WHERE id = %s", (status, item_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating DB: {e}")

def callback(ch, method, properties, body):
    data = json.loads(body)
    item_id = data['item_id']
    print(f"Processing item {item_id}")
    time.sleep(5)  # Simulate work
    update_db(item_id, "Processed by worker")
    print(f"Finished processing item {item_id}")
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
