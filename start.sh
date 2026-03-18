#!/bin/bash

echo "Starting Decentralized ML Hub Services..."

# 1. Start the gRPC Server in the background (&)
python app/grpc_server.py &

# 2. Start the Celery Worker in the background (&)
celery -A app.worker.celery_app worker --loglevel=info &

# 3. Start the FastAPI Hub in the foreground (This keeps the container alive)
# Koyeb dynamically assigns a $PORT variable, so we must bind to it
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1