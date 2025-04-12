FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY messages_service.py .

EXPOSE 6001
CMD ["python", "messages_service.py"]
