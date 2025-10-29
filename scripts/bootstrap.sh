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
  log_info "Installing Docker Engine via Docker's apt repository..."

  if ! command_exists curl; then
    log_info "Installing prerequisite packages (curl, ca-certificates, gnupg)..."
    "${SUDO_CMD[@]}" apt-get update -y
    "${SUDO_CMD[@]}" apt-get install -y curl ca-certificates gnupg >/dev/null
  else
    "${SUDO_CMD[@]}" apt-get update -y
    "${SUDO_CMD[@]}" apt-get install -y ca-certificates gnupg >/dev/null
  fi

  local keyring_dir="/etc/apt/keyrings"
  "${SUDO_CMD[@]}" install -m 0755 -d "${keyring_dir}"
  if [[ ! -f "${keyring_dir}/docker.gpg" ]]; then
    local distro_id
    distro_id=$(. /etc/os-release && echo "${ID}")
    log_info "Adding Docker GPG key for ${distro_id}..."
    curl -fsSL "https://download.docker.com/linux/${distro_id}/gpg" |
      "${SUDO_CMD[@]}" gpg --dearmor -o "${keyring_dir}/docker.gpg"
  fi

  local codename
  codename=$(. /etc/os-release && echo "${VERSION_CODENAME:-${UBUNTU_CODENAME:-stable}}")
  local arch
  arch="$(dpkg --print-architecture)"
  local repo_line="deb [arch=${arch} signed-by=${keyring_dir}/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "${ID}") ${codename} stable"
  echo "${repo_line}" | "${SUDO_CMD[@]}" tee /etc/apt/sources.list.d/docker.list >/dev/null

  "${SUDO_CMD[@]}" apt-get update -y

  local packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
  if ! "${SUDO_CMD[@]}" apt-get install -y "${packages[@]}"; then
    log_warn "Docker CE packages unavailable from repository. Attempting to install distro docker.io package instead."
    "${SUDO_CMD[@]}" apt-get install -y docker.io || true
  fi

  if command_exists systemctl; then
    "${SUDO_CMD[@]}" systemctl enable --now docker >/dev/null 2>&1 || true
  fi
}

install_compose_standalone() {
  require_privileged_install
  local version="${DOCKER_COMPOSE_VERSION:-v2.24.6}"
  local dest="/usr/local/lib/docker/cli-plugins/docker-compose"
  local system
  system="$(uname -s)"
  local machine
  machine="$(uname -m)"
  local url="https://github.com/docker/compose/releases/download/${version}/docker-compose-${system}-${machine}"

  log_info "Installing Docker Compose standalone binary (${version})..."
  "${SUDO_CMD[@]}" mkdir -p "$(dirname "${dest}")"
  if ! curl -fsSL "${url}" -o /tmp/docker-compose; then
    log_error "Failed to download Docker Compose from ${url}."
    exit 1
  fi
  "${SUDO_CMD[@]}" mv /tmp/docker-compose "${dest}"
  "${SUDO_CMD[@]}" chmod +x "${dest}"
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
    if docker compose version >/dev/null 2>&1; then
      return
    fi
    log_warn "Docker Compose plugin not available via apt. Falling back to standalone binary."
    install_compose_standalone
  else
    log_warn "apt-get not available. Attempting standalone Docker Compose installation."
    install_compose_standalone
  fi

  if ! docker compose version >/dev/null 2>&1; then
    log_error "Docker Compose installation did not succeed."
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
  ensure_compose_plugin
fi

ensure_env_file

log_info "Building and starting containers..."
(
  cd "${ROOT_DIR}"
  "${DOCKER_CMD[@]}" compose up --build
)
