#!/bin/bash

# ==============================================================================
# Maestro UI Startup Script
# Starts both the FastAPI backend and the React frontend.
# Logs all output for debugging and telemetry.
# ==============================================================================

# Ensure we are in the project root
cd "$(dirname "$0")" || exit

LOG_FILE="maestro_ui.log"
BACKEND_DIR="maestro_ui/backend"
FRONTEND_DIR="maestro_ui/frontend"

# Clear previous log
> "$LOG_FILE"

echo "[*] Starting Maestro UI Pipeline..." | tee -a "$LOG_FILE"
echo "[*] All terminal output will be logged to $LOG_FILE"

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "[!] Caught termination signal. Shutting down servers..." | tee -a "$LOG_FILE"
    # Kill process group or specific PIDs
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    echo "[*] Shutdown complete." | tee -a "$LOG_FILE"
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# 1. Start the FastAPI Backend
echo "[1/2] Starting FastAPI Backend on port 8000..." | tee -a "$LOG_FILE"
if [ ! -d "$BACKEND_DIR" ]; then
    echo "[!] Error: Backend directory '$BACKEND_DIR' not found." | tee -a "$LOG_FILE"
    exit 1
fi

cd "$BACKEND_DIR" || exit
# Run uvicorn, log output, and send to background
python3 -m uvicorn app.main:app --reload --port 8000 >> "../../$LOG_FILE" 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait briefly to ensure backend starts without immediate crash
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "[!] Error: Backend failed to start. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    exit 1
fi

# 2. Start the Vite Frontend
echo "[2/2] Starting React Frontend on port 5173..." | tee -a "$LOG_FILE"
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "[!] Error: Frontend directory '$FRONTEND_DIR' not found." | tee -a "$LOG_FILE"
    cleanup
fi

cd "$FRONTEND_DIR" || exit
# Run npm dev, log output, and send to background
npm run dev >> "../../$LOG_FILE" 2>&1 &
FRONTEND_PID=$!
cd ../..

# Wait briefly to ensure frontend starts
sleep 2
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "[!] Error: Frontend failed to start. Check $LOG_FILE for details." | tee -a "$LOG_FILE"
    cleanup
fi

echo "====================================================================="
echo "✅ Maestro UI is live!"
echo "📡 Backend API: http://localhost:8000"
echo "🖥️  Frontend UI: http://localhost:5173"
echo "📄 Log file:   $PWD/$LOG_FILE"
echo "🛑 Press Ctrl+C to stop both servers."
echo "====================================================================="

# Keep script running and wait for user interrupt
wait $BACKEND_PID $FRONTEND_PID
