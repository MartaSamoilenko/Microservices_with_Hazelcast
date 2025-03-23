from fastapi import FastAPI, HTTPException
from typing import Dict, List
import hazelcast
import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("logging-service")

LOGGING_SERVICE_PORT = int(os.environ.get("LOGGING_SERVICE_PORT", 8000))
INSTANCE_ID = os.environ.get("INSTANCE_ID", "logging-service-default")
HAZELCAST_NODES = os.environ.get("HAZELCAST_NODES", "hazelcast-1:5701").split(",")

logging_app = FastAPI()

client = None
log_storage = None

@logging_app.on_event("startup")
async def startup_event():
    global client, log_storage
    max_retries = 10
    retry_delay = 5
    
    logger.info(f"Starting {INSTANCE_ID} on port {LOGGING_SERVICE_PORT}")
    logger.info(f"Configured Hazelcast nodes: {HAZELCAST_NODES}")
    
    for retry in range(max_retries):
        try:
            logger.info(f"Attempt {retry+1}/{max_retries} to connect to Hazelcast...")
            
            try:
                client = hazelcast.HazelcastClient(
                    cluster_members=HAZELCAST_NODES,
                    cluster_name="dev"
                )
            except TypeError:
                logger.info("Falling back to older Hazelcast API...")
                config = hazelcast.ClientConfig()
                config.network_config.addresses = HAZELCAST_NODES
                config.group_config.name = "dev"
                client = hazelcast.HazelcastClient(config)
            
            log_storage = client.get_map("log_storage").blocking()
            
            logger.info(f"{INSTANCE_ID} successfully connected to Hazelcast cluster")
            break
        except Exception as e:
            logger.error(f"Failed to connect to Hazelcast: {str(e)}")
            if retry < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Hazelcast after {max_retries} attempts")
               

    if not client or not log_storage:
        logger.warning("Using local storage as fallback")
        logging_app.state.local_storage = {}

@logging_app.on_event("shutdown")
async def shutdown_event():
    global client
    if client:
        client.shutdown()
        logger.info(f"{INSTANCE_ID} disconnected from Hazelcast")

@logging_app.post("/log")
async def log_message(data: Dict[str, str]):
    global log_storage, client
    
    msg_id = data.get("id")
    msg = data.get("msg")
    
    if not msg_id or not msg:
        raise HTTPException(status_code=400, detail="Message ID and content are required")
    
    if not client or not log_storage:
        # Fall back to local storage
        if not hasattr(logging_app.state, "local_storage"):
            logging_app.state.local_storage = {}
        
        logging_app.state.local_storage[msg_id] = msg
        logger.info(f"{INSTANCE_ID} logged message locally: {msg} (ID: {msg_id})")
        return {"status": "success", "instance_id": INSTANCE_ID, "storage": "local"}
    
    try:
        log_storage.put(msg_id, msg)
        logger.info(f"{INSTANCE_ID} logged message in Hazelcast: {msg} (ID: {msg_id})")
        return {"status": "success", "instance_id": INSTANCE_ID, "storage": "hazelcast"}
    except Exception as e:
        logger.error(f"Error logging message: {str(e)}")
        
        if not hasattr(logging_app.state, "local_storage"):
            logging_app.state.local_storage = {}
        
        logging_app.state.local_storage[msg_id] = msg
        logger.info(f"{INSTANCE_ID} logged message locally after Hazelcast failure: {msg} (ID: {msg_id})")
        return {"status": "success", "instance_id": INSTANCE_ID, "storage": "local_fallback"}

@logging_app.get("/logs")
async def get_logs():
    global log_storage, client
    
    try:
        if client and log_storage:
            all_logs = log_storage.values()
            logger.info(f"{INSTANCE_ID} retrieved {len(all_logs)} logs from Hazelcast")
            return {"messages": list(all_logs), "instance_id": INSTANCE_ID, "storage": "hazelcast"}
        
        if hasattr(logging_app.state, "local_storage"):
            local_logs = list(logging_app.state.local_storage.values())
            logger.info(f"{INSTANCE_ID} retrieved {len(local_logs)} logs from local storage")
            return {"messages": local_logs, "instance_id": INSTANCE_ID, "storage": "local"}
        
        logger.warning(f"{INSTANCE_ID} has no logs available")
        return {"messages": [], "instance_id": INSTANCE_ID, "storage": "none"}
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        
        if hasattr(logging_app.state, "local_storage"):
            local_logs = list(logging_app.state.local_storage.values())
            logger.info(f"{INSTANCE_ID} retrieved {len(local_logs)} logs from local storage after Hazelcast failure")
            return {"messages": local_logs, "instance_id": INSTANCE_ID, "storage": "local_fallback"}
        
        logger.warning(f"{INSTANCE_ID} has no logs available after error")
        return {"messages": [], "instance_id": INSTANCE_ID, "storage": "error"}

@logging_app.get("/health")
async def health_check():
    storage_type = "unknown"
    if client and log_storage:
        try:
            test_key = "health_check_key"
            test_value = "health_check_value"
            log_storage.put(test_key, test_value)
            retrieved = log_storage.get(test_key)
            log_storage.remove(test_key)
            
            if retrieved == test_value:
                storage_type = "hazelcast"
            else:
                storage_type = "hazelcast_error"
        except Exception:
            storage_type = "hazelcast_error"
    elif hasattr(logging_app.state, "local_storage"):
        storage_type = "local"
    
    return {
        "status": "healthy", 
        "instance_id": INSTANCE_ID,
        "storage_type": storage_type
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(logging_app, host="0.0.0.0", port=LOGGING_SERVICE_PORT)