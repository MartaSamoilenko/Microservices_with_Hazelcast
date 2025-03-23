from fastapi import FastAPI
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("message-service")

MESSAGE_SERVICE_PORT = int(os.environ.get("MESSAGE_SERVICE_PORT", 8000))

messages_app = FastAPI()

@messages_app.get("/message")
async def get_static_message():
    logger.info("Static message requested")
    return {"message": "Hello, I'm a static message from the containerized service!"}

@messages_app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "message-service"}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting message service on port {MESSAGE_SERVICE_PORT}")
    uvicorn.run(messages_app, host="0.0.0.0", port=MESSAGE_SERVICE_PORT)