#!/bin/bash
# Start ProctorAI Local Backend and Frontend

cd "$(dirname "$0")"
source .venv/bin/activate

echo "========================================"
echo "    Starting ProctorAI Full Stack       "
echo "========================================"

# 1. Start FastAPI Backend on Port 8000
echo "[1/2] Starting FastAPI Backend on http://localhost:8000 ..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 2. Start Frontend HTTP Server on Port 3000
echo "[2/2] Starting Frontend Dashboard on http://localhost:3000 ..."
python3 -m http.server 3000 --directory frontend &
FRONTEND_PID=$!

echo ""
echo "✅ Backend API running at: http://localhost:8000"
echo "✅ Frontend Dashboard running at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
