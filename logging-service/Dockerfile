FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY logging_service.py .

# We'll define the port via environment variables, but let's expose a default
EXPOSE 5001
CMD ["python", "logging_service.py"]
