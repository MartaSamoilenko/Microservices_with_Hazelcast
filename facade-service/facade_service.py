from fastapi import FastAPI, HTTPException, Request
import httpx
import uuid
import random
import asyncio
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("facade-service")

FACADE_SERVICE_PORT = int(os.environ.get("FACADE_SERVICE_PORT", 8000))
MESSAGE_SERVICE_URL = os.environ.get("MESSAGE_SERVICE_URL", "http://message-service:8000")

LOGGING_SERVICES = os.environ.get(
    "LOGGING_SERVICES", 
    "http://logging-service-1:8000,http://logging-service-2:8000,http://logging-service-3:8000"
).split(",")

facade_app = FastAPI()

async def choose_logging_service():
    services = LOGGING_SERVICES.copy()
    random.shuffle(services)
    
    logger.info(f"Testing logging services in order: {services}")
    
    for service_url in services:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=2.0)
                if response.status_code == 200:
                    logger.info(f"Selected logging service: {service_url}")
                    return service_url
        except Exception as e:
            logger.warning(f"Service {service_url} is unavailable: {str(e)}")
            continue
    
    logger.error("All logging services are unavailable")
    raise HTTPException(status_code=503, detail="All logging services are unavailable")

@facade_app.post("/send")
async def send_message(request: Request):
    data = await request.json()
    msg = data.get("msg")
    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    msg_id = str(uuid.uuid4())
    logger.info(f"Received message: {msg} (ID: {msg_id})")
    
    try:
        logging_service_url = await choose_logging_service()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{logging_service_url}/log", 
                json={"id": msg_id, "msg": msg},
                timeout=5.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to log message: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to log message")
            
            result = response.json()
            logger.info(f"Message logged successfully via {result.get('instance_id', 'unknown')} using {result.get('storage', 'unknown')} storage")
        
        return {
            "uuid": msg_id, 
            "message": msg, 
            "service": logging_service_url,
            "result": result
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@facade_app.get("/get")
async def get_messages():
    try:
        logging_service_url = await choose_logging_service()
        
        async with httpx.AsyncClient() as client:
            log_task = client.get(f"{logging_service_url}/logs", timeout=5.0)
            msg_task = client.get(f"{MESSAGE_SERVICE_URL}/message", timeout=5.0)
            
            results = await asyncio.gather(log_task, msg_task, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error retrieving data: {str(result)}")
                    raise HTTPException(status_code=500, detail=f"Failed to retrieve data: {str(result)}")
            
            log_response, msg_response = results
        
        if log_response.status_code != 200:
            logger.error(f"Failed to get logs: {log_response.text}")
            raise HTTPException(status_code=500, detail="Failed to get logs")
        
        if msg_response.status_code != 200:
            logger.error(f"Failed to get static message: {msg_response.text}")
            raise HTTPException(status_code=500, detail="Failed to get static message")
        
        logs = log_response.json()
        static_message = msg_response.json().get("message", "")
        
        messages = logs.get("messages", [])
        storage_type = logs.get("storage", "unknown")
        instance_id = logs.get("instance_id", "unknown")
        
        logger.info(f"Retrieved {len(messages)} messages from {instance_id} using {storage_type} storage")
        
        return {
            "logs": messages, 
            "static_message": static_message, 
            "service": logging_service_url,
            "instance_id": instance_id,
            "storage_type": storage_type
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")

@facade_app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MESSAGE_SERVICE_URL}/health", timeout=2.0)
            if response.status_code != 200:
                return {"status": "degraded", "details": "Message service is unavailable"}
    except Exception:
        return {"status": "degraded", "details": "Message service is unavailable"}
    
    try:
        await choose_logging_service()
    except HTTPException:
        return {"status": "degraded", "details": "All logging services are unavailable"}
    
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting facade service on port {FACADE_SERVICE_PORT}")
    logger.info(f"Configured logging services: {LOGGING_SERVICES}")
    logger.info(f"Configured message service: {MESSAGE_SERVICE_URL}")
    uvicorn.run(facade_app, host="0.0.0.0", port=FACADE_SERVICE_PORT)