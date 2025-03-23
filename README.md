# Microservices_with_Hazelcast

## Project Structure

```
distributed-logging-system/
├── docker-compose.yml
├── facade-service/
│   ├── Dockerfile
│   ├── facade_service.py
│   └── requirements.txt
├── logging-service/
│   ├── Dockerfile
│   ├── logging_service.py
│   └── requirements.txt
├── message-service/
│   ├── Dockerfile
│   ├── message_service.py
│   └── requirements.txt
└── README.md
```

## Building and Running
```bash
docker-compose up -d
```

To view logs for all services:

```bash
docker-compose logs -f
```

## Testing the System :)

### 1. Writing Messages

```bash
curl -X POST http://localhost:8000/send -H "Content-Type: application/json" -d '{"msg":"Hello, I am message 1"}'

curl -X POST http://localhost:8000/send -H "Content-Type: application/json" -d '{"msg":"Hello, I am message 2"}'

# send what you want tbh ...
```

SEND MESSAGES IN FOR LOOP !!!!
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/send -H "Content-Type: application/json" -d "{\"msg\":\"mesage bro $i\"}"
  echo ""
done
```

### 2. Checking Message Distribution (is it Normal?)

```bash
docker-compose logs logging-service-1 logging-service-2 logging-service-3
```

### 3. Retrieving Messages 


```bash
curl http://localhost:8000/get
```

### 4. Testing Resilience !!!


```bash
docker-compose stop logging-service-1

docker-compose stop logging-service-1 logging-service-2
```
Then run :
```bash
curl http://localhost:8000/get
```

### 5. Testing Hazelcast Resilience


```bash
docker-compose stop hazelcast-1
```

## Shutting Down

To stop and remove all services:

```bash
docker-compose down
```
