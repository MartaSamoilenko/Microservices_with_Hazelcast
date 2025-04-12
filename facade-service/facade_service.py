from flask import Flask, request, jsonify
import requests
import random
import os
import sys
from kafka import KafkaProducer

app = Flask(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9092,kafka3:9092")
TOPIC_NAME = os.environ.get("TOPIC_NAME", "test-topic")

producer = None

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(",")
    )
except Exception as e:
    print("ERROR: Could not connect to Kafka. Reason:", e)
    sys.exit(1)

LOGGING_SERVICE_URLS = [
    "http://logging-service1:5001/logs",
    "http://logging-service2:5002/logs",
    "http://logging-service3:5003/logs",
]

MESSAGES_SERVICE_URLS = [
    "http://messages-service1:6001/messages",
    "http://messages-service2:6002/messages",
]

@app.route('/submit', methods=['POST'])
def submit_message():
    """Handle POST requests: Produce the given messages to Kafka."""
    data = request.json
    if not data or "messages" not in data:
        return jsonify({"error": "Expected JSON with key 'messages'"}), 400
    
    messages = data["messages"]
    for msg in messages:
        producer.send(TOPIC_NAME, value=msg.encode('utf-8'))
    
    producer.flush()
    return jsonify({"status": "Messages produced to Kafka."}), 200

@app.route('/retrieve', methods=['GET'])
def retrieve_messages():
    """Handle GET requests: 
       1. Gather logs from all logging-service instances.
       2. Pick a random messages-service instance and gather messages from it.
       3. Return combined result.
    """
    logs_collected = []
    for log_url in LOGGING_SERVICE_URLS:
        try:
            resp = requests.get(log_url, timeout=3)
            logs_collected.append({"service_url": log_url, "logs": resp.json()})
        except Exception as e:
            logs_collected.append({"service_url": log_url, "error": str(e)})
    
    chosen_messages_url = random.choice(MESSAGES_SERVICE_URLS)
    messages_collected = []
    try:
        resp = requests.get(chosen_messages_url, timeout=3)
        messages_collected = resp.json()
    except Exception as e:
        messages_collected = {"error": str(e)}
    
    return jsonify({
        "logs": logs_collected,
        "messages_from_random_instance": messages_collected
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
