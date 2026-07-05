#!/bin/zsh
# Double-click to start the Cascade Precision cash flow demo:
# backend on :8000, frontend on :5173, then open the browser.
cd "$(dirname "$0")"

echo "Starting backend (uvicorn, port 8000)..."
python3 -m uvicorn backend.server:app --port 8000 > /tmp/cashflow-backend.log 2>&1 &
BACKEND_PID=$!

echo "Starting frontend (vite, port 5173)..."
cd frontend
npm run dev > /tmp/cashflow-frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 3
open http://localhost:5173

echo ""
echo "Demo running:  http://localhost:5173"
echo "Logs:          /tmp/cashflow-backend.log  /tmp/cashflow-frontend.log"
echo "Press Ctrl+C to stop both servers."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
