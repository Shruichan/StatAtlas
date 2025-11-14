#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

function cleanup() {
  if [[ -n "${BACK_PID:-}" ]]; then
    kill "$BACK_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${FRONT_PID:-}" ]]; then
    kill "$FRONT_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cd "$ROOT_DIR"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACK_PID=$!
echo "Backend running at http://localhost:8000 (PID: $BACK_PID)"

cd "$FRONTEND_DIR"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONT_PID=$!
echo "Frontend running at http://localhost:5173 (PID: $FRONT_PID)"

wait "$BACK_PID" "$FRONT_PID"
