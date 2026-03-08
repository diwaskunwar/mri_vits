#!/bin/bash

echo "Starting Candor Dust locally without Docker..."

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    echo "All services stopped."
}
trap cleanup EXIT

# 1. Start Model Service
echo "Starting Model Service (Ray Serve on port 8001)..."
cd model
uv sync
# Run serve.py using uv. Start ray serve
uv run python serve.py > model_service.log 2>&1 &
MODEL_PID=$!
cd ..

# Wait for model service to be healthy
echo "Waiting for Model Service to be healthy..."
max_retries=30
count=0
while ! curl -s http://localhost:8001/health > /dev/null; do
    count=$((count+1))
    if [ $count -ge $max_retries ]; then
        echo "❌ Model Service failed to start after 30 seconds. Check model/model_service.log"
        exit 1
    fi
    sleep 1
done
echo "✅ Model Service is healthy!"

# 2. Start Backend Service
echo "Starting Backend Service (FastAPI on port 8000)..."
cd backend
uv sync
uv run uvicorn src:app --host 0.0.0.0 --port 8000 --reload > backend_service.log 2>&1 &
BACKEND_PID=$!
cd ..

# 3. Start Frontend Service
echo "Starting Frontend Service (Vite on port 3000)..."
cd frontend
npm install > /dev/null 2>&1
npm run dev -- --port 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================================"
echo " ✅ Candor Dust is running!"
echo " - Frontend:     http://localhost:3000"
echo " - Backend API:  http://localhost:8000"
echo " - Model API:    http://localhost:8001"
echo ""
echo " Logs:"
echo " - Model:   tail -f model/model_service.log"
echo " - Backend: tail -f backend/backend_service.log"
echo "========================================================"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait indefinitely until interrupted
wait
