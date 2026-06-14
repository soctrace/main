#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/soctrace-web"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
UVI_BIN="$VENV_DIR/bin/uvicorn"
BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5173"
BACKEND_PID=""

log() {
  printf '[soctrace-dev] %s\n' "$1"
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    log "Stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

ensure_venv() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    log "Creating virtualenv in .venv"
    python3 -m venv "$VENV_DIR"
  fi
}

ensure_backend_deps() {
  if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, psycopg, sqlalchemy" >/dev/null 2>&1; then
    log "Installing backend dependencies"
    "$PIP_BIN" install -r "$BACKEND_DIR/requirements.txt"
  fi
}

ensure_frontend_env() {
  if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
    log "Creating soctrace-web/.env from example"
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
  fi
}

ensure_frontend_deps() {
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    log "Installing frontend dependencies"
    (
      cd "$FRONTEND_DIR"
      npm install
    )
  fi
}

ensure_backend_env() {
  if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    log "Creating backend/.env from example"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  fi
}

start_backend() {
  log "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
  (
    cd "$BACKEND_DIR"
    exec "$UVI_BIN" app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) &
  BACKEND_PID="$!"
}

wait_for_backend() {
  log "Waiting for backend healthcheck"
  for _ in {1..30}; do
    if curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/health" >/dev/null 2>&1; then
      log "Backend is healthy"
      return 0
    fi

    if [[ -n "$BACKEND_PID" ]] && ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      log "Backend exited before becoming healthy"
      return 1
    fi

    sleep 1
  done

  log "Backend did not become healthy in time"
  return 1
}

start_frontend() {
  log "Starting frontend on http://$FRONTEND_HOST:$FRONTEND_PORT"
  cd "$FRONTEND_DIR"
  exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
}

ensure_venv
ensure_backend_deps
ensure_backend_env
ensure_frontend_env
ensure_frontend_deps
start_backend
wait_for_backend
start_frontend
