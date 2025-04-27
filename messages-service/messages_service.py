from flask import Flask, jsonify
import os
import sys
from kafka import KafkaConsumer
import threading

app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9092,kafka3:9092")
TOPIC_NAME = os.environ.get("TOPIC_NAME", "test-topic")

CONSUMER_GROUP = os.environ.get("CONSUMER_GROUP", "messages-group-1")

stored_messages = []

def consume_messages():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        group_id=CONSUMER_GROUP,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        api_version=(0, 11, 6)
    )
    for msg in consumer:
        decoded = msg.value.decode('utf-8')
        print(f"[Messages-Service] Received message: {decoded}")
        stored_messages.append(decoded)

@app.route('/messages', methods=['GET'])
def get_messages():
    """Return the in-memory set of messages."""
    return jsonify(stored_messages)

if __name__ == '__main__':
    t = threading.Thread(target=consume_messages, daemon=True)
    t.start()

    app.run(host='0.0.0.0', port=int(os.environ.get("MESSAGES_SERVICE_PORT", 6001)))
