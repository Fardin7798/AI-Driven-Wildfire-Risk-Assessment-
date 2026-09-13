#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================================="
echo "  WildfireRisk & CleanAir India — Development Launcher   "
echo "=========================================================="

cleanup() {
  echo ""
  echo "Shutting down servers..."
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo "All processes stopped cleanly."
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend Microservice
echo "Starting Backend Microservice on http://localhost:8000..."
cd "$BACKEND_DIR"
if [ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
  "$BACKEND_DIR/.venv/bin/uvicorn" main:app --reload --port 8000 &
else
  uvicorn main:app --reload --port 8000 &
fi
BACKEND_PID=$!

# Wait briefly for backend port to be bound
sleep 1.5

# 2. Start Frontend Single Page Application
echo "Starting Frontend SPA on http://localhost:5173..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  🚀 Both services are running!"
echo "  - Web Dashboard:  http://localhost:5173"
echo "  - Backend API:    http://localhost:8000"
echo "  - Swagger Docs:   http://localhost:8000/docs"
echo "=========================================================="
echo "Press Ctrl+C to terminate both servers."
echo ""

# Keep running until user terminates
wait
