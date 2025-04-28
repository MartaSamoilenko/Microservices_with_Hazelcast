from flask import Flask, request, jsonify
import requests
import random
import os
import sys
from kafka import KafkaProducer
from consul_helper import register, instances, kv

app = Flask(__name__)
app.add_url_rule("/health", "health", lambda: ("OK", 200))

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

def log_urls():
    return [u + "/logs" for u in instances("logging-service")]

def msg_urls():
    return [u + "/messages" for u in instances("messages-service")]


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
    for log_url in log_urls():
        try:
            resp = requests.get(log_url, timeout=3)
            logs_collected.append({"service_url": log_url, "logs": resp.json()})
        except Exception as e:
            logs_collected.append({"service_url": log_url, "error": str(e)})
    
    urls = msg_urls()

    if not urls:
        return jsonify({"error": "no messages-service instances alive"}), 503
    chosen_messages_url = random.choice(urls)

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
    register("facade-service", 5000)
    app.run(host='0.0.0.0', port=5000)
