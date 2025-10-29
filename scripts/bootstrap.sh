#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
APP_ENV="${ROOT_DIR}/app/.env"
EXAMPLE_ENV="${ROOT_DIR}/app/.env.example"

log_info() { printf '\033[1;34m[INFO]\033[0m %s\n' "$*"; }
log_warn() { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
log_error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

SUDO_CMD=()
if [[ ${EUID} -ne 0 ]]; then
  if command_exists sudo; then
    SUDO_CMD=(sudo)
  fi
fi

require_privileged_install() {
  if [[ ${#SUDO_CMD[@]} -eq 0 && ${EUID} -ne 0 ]]; then
    log_error "Installing dependencies requires root or sudo privileges."
    exit 1
  fi
}

install_docker_with_apt() {
  require_privileged_install
  log_info "Installing Docker engine and Compose plugin via apt-get..."
  "${SUDO_CMD[@]}" apt-get update -y
  "${SUDO_CMD[@]}" apt-get install -y docker.io docker-compose-plugin
  if command_exists systemctl; then
    "${SUDO_CMD[@]}" systemctl enable --now docker >/dev/null 2>&1 || true
  fi
}

ensure_docker() {
  if command_exists docker; then
    return
  fi

  if command_exists apt-get; then
    install_docker_with_apt
  else
    log_error "Docker is required but could not be installed automatically. Please install Docker manually and re-run this script."
    exit 1
  fi

  if ! command_exists docker; then
    log_error "Docker installation did not succeed."
    exit 1
  fi
}

ensure_compose_plugin() {
  if command_exists docker && docker compose version >/dev/null 2>&1; then
    return
  fi

  if command_exists apt-get; then
    install_docker_with_apt
  else
    log_error "Docker Compose plugin is required but automatic installation is unsupported on this system."
    exit 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    log_error "Docker Compose plugin installation did not succeed."
    exit 1
  fi
}

ensure_env_file() {
  if [[ -f "${APP_ENV}" ]]; then
    return
  fi

  if [[ -f "${EXAMPLE_ENV}" ]]; then
    log_info "${APP_ENV} not found. Copying from .env.example."
    cp "${EXAMPLE_ENV}" "${APP_ENV}"
  else
    log_error "${APP_ENV} not found and no example file is available."
    exit 1
  fi
}

ensure_docker
ensure_compose_plugin

# Determine whether docker commands require sudo
DOCKER_CMD=(docker)
if ! docker info >/dev/null 2>&1; then
  if [[ ${#SUDO_CMD[@]} -gt 0 ]]; then
    if "${SUDO_CMD[@]}" docker info >/dev/null 2>&1; then
      DOCKER_CMD=("${SUDO_CMD[@]}" docker)
    else
      log_error "Docker daemon is not running or accessible."
      exit 1
    fi
  else
    log_error "Docker daemon is not running or accessible."
    exit 1
  fi
fi

if ! "${DOCKER_CMD[@]}" compose version >/dev/null 2>&1; then
  if command_exists apt-get; then
    install_docker_with_apt
  fi
  if ! "${DOCKER_CMD[@]}" compose version >/dev/null 2>&1; then
    log_error "Docker Compose plugin is still unavailable after installation attempt."
    exit 1
  fi
fi

ensure_env_file

log_info "Building and starting containers..."
(
  cd "${ROOT_DIR}"
  "${DOCKER_CMD[@]}" compose up --build
)
