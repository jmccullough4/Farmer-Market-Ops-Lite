#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
APP_ENV="${ROOT_DIR}/app/.env"
EXAMPLE_ENV="${ROOT_DIR}/app/.env.example"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker is required but not installed or not in PATH" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] docker compose plugin is required. Please install Docker Compose v2." >&2
  exit 1
fi

if [[ ! -f "${APP_ENV}" ]]; then
  if [[ -f "${EXAMPLE_ENV}" ]]; then
    echo "[INFO] ${APP_ENV} not found. Copying from .env.example." >&2
    cp "${EXAMPLE_ENV}" "${APP_ENV}"
  else
    echo "[ERROR] ${APP_ENV} not found and no example file available." >&2
    exit 1
  fi
fi

echo "[INFO] Building and starting containers..." >&2
(cd "${ROOT_DIR}" && docker compose up --build)
