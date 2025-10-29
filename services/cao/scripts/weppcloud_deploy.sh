#!/usr/bin/env bash
set -euo pipefail

# weppcloud_deploy.sh — Provision a WEPPcloud dev runner (nuc2)
#
# Idempotent setup for a local /wc1, repositories under /workdir, toolchains
# (Docker, uv, rustup, npm), optional CAO systemd service, and misc utilities.
#
# Defaults are tailored for nuc2 based on team notes. Override via env/flags.
#
# Usage examples:
#   sudo bash weppcloud_deploy.sh                      # default path/user/group
#   sudo WC_ROOT=/wc1 WORKDIR=/workdir bash weppcloud_deploy.sh
#   sudo bash weppcloud_deploy.sh --env-file /tmp/wepppy.env --with-cao
#   sudo bash weppcloud_deploy.sh --skip-node --skip-docker
#
# Flags:
#   --env-file <path>   Optional: copy to wepppy/docker/.env
#   --with-cao          Optional: install and enable CAO systemd service
#   --skip-docker       Skip Docker engine installation
#   --skip-node         Skip npm/global packages
#   --readonly-pattern <glob>  Optional: mark matching run dirs with READONLY

WC_ROOT=${WC_ROOT:-/wc1}
WORKDIR=${WORKDIR:-/workdir}
OWNER_USER=${OWNER_USER:-roger}
OWNER_GROUP=${OWNER_GROUP:-docker}

ENV_FILE=""
WITH_CAO=0
SKIP_DOCKER=0
SKIP_NODE=0
READONLY_GLOB=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"; shift 2;;
    --with-cao)
      WITH_CAO=1; shift;;
    --skip-docker)
      SKIP_DOCKER=1; shift;;
    --skip-node)
      SKIP_NODE=1; shift;;
    --readonly-pattern)
      READONLY_GLOB="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "==> Settings"
echo "WC_ROOT=$WC_ROOT"
echo "WORKDIR=$WORKDIR"
echo "OWNER=$OWNER_USER:$OWNER_GROUP"
echo "ENV_FILE=${ENV_FILE:-<none>}"
echo "WITH_CAO=$WITH_CAO SKIP_DOCKER=$SKIP_DOCKER SKIP_NODE=$SKIP_NODE"
echo "READONLY_GLOB=${READONLY_GLOB:-<none>}"

require_root() {
  if [[ $(id -u) -ne 0 ]]; then
    echo "This script must run as root (use sudo)." >&2
    exit 1
  fi
}

ensure_group() {
  local grp="$1"
  if ! getent group "$grp" >/dev/null; then
    echo "==> Creating group $grp"
    groupadd "$grp"
  fi
}

ensure_user_in_group() {
  local user="$1" grp="$2"
  if id -nG "$user" | tr ' ' '\n' | grep -qx "$grp"; then
    return
  fi
  echo "==> Adding $user to $grp"
  usermod -aG "$grp" "$user"
}

apt_install() {
  echo "==> apt update && install base packages"
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git curl ca-certificates build-essential pkg-config \
    python3 python3-venv python3-pip \
    ripgrep \
    nfs-common \
    jq \
    unzip
}

maybe_install_docker() {
  if [[ "$SKIP_DOCKER" == "1" ]]; then
    echo "==> Skipping Docker installation (per flag)"
    return
  fi
  if command -v docker >/dev/null 2>&1; then
    echo "==> Docker already installed"
  else
    echo "==> Installing docker.io and docker-compose-plugin"
    DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-plugin
    systemctl enable --now docker
  fi
  ensure_group "$OWNER_GROUP"
  ensure_user_in_group "$OWNER_USER" "$OWNER_GROUP"
}

prepare_dirs() {
  echo "==> Ensuring $WC_ROOT and geodata exist"
  mkdir -p "$WC_ROOT/geodata"
  chown -R "$OWNER_USER":"$OWNER_GROUP" "$WC_ROOT"
  chmod 775 "$WC_ROOT" "$WC_ROOT/geodata"

  echo "==> Ensuring $WORKDIR exists"
  mkdir -p "$WORKDIR"
  chown -R "$OWNER_USER":"$OWNER_GROUP" "$WORKDIR"
}

clone_or_update() {
  local url="$1" dest="$2"
  if [[ -d "$dest/.git" ]]; then
    echo "==> Updating $(basename "$dest")"
    git -C "$dest" fetch --all -q || true
    git -C "$dest" pull --ff-only || true
  else
    echo "==> Cloning $url into $dest"
    sudo -u "$OWNER_USER" git clone "$url" "$dest"
  fi
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    echo "==> uv already installed"
  else
    echo "==> Installing uv (Python package manager)"
    sudo -u "$OWNER_USER" bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    export PATH="/home/$OWNER_USER/.local/bin:$PATH"
  fi
}

install_rustup() {
  if command -v rustup >/dev/null 2>&1; then
    echo "==> rustup already installed"
  else
    echo "==> Installing rustup"
    sudo -u "$OWNER_USER" bash -lc "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
    export PATH="/home/$OWNER_USER/.cargo/bin:$PATH"
  fi
}

install_node_tools() {
  if [[ "$SKIP_NODE" == "1" ]]; then
    echo "==> Skipping Node/npm tooling (per flag)"
    return
  fi
  echo "==> Installing npm and global tools"
  DEBIAN_FRONTEND=noninteractive apt-get install -y npm
  # npx is included with npm >=5.2; install explicitly per notes
  npm install -g npx @openai/codex || true
}

install_wctl() {
  local wc_repo="$WORKDIR/wepppy"
  if command -v wctl >/dev/null 2>&1; then
    echo "==> wctl already installed"
    return
  fi
  if [[ -x "$wc_repo/wctl/install.sh" ]]; then
    echo "==> Installing wctl"
    (cd "$wc_repo" && sudo -u "$OWNER_USER" bash -lc './wctl/install.sh')
  else
    echo "==> wctl installer not found; skipping"
  fi
}

touch_js_files() {
  local wc_repo="$WORKDIR/wepppy"
  local p1="$wc_repo/wepppy/weppcloud/static/js/controllers.js"
  local p2="$wc_repo/wepppy/weppcloud/static/js/unitizer_map.js"
  echo "==> Touching JS files for live-reload expectations"
  sudo -u "$OWNER_USER" touch "$p1" "$p2"
  chmod 777 "$p1" "$p2" || true
}

copy_env_if_provided() {
  if [[ -n "$ENV_FILE" ]]; then
    echo "==> Copying env file to wepppy/docker/.env"
    install -o "$OWNER_USER" -g "$OWNER_GROUP" -m 640 "$ENV_FILE" "$WORKDIR/wepppy/docker/.env"
  fi
}

install_cao_service() {
  local wc_repo="$WORKDIR/wepppy"
  echo "==> Setting up CAO virtualenv (via uv if available)"
  if [[ -x "$wc_repo/services/cao/scripts/setup_venv.sh" ]]; then
    (cd "$wc_repo/services/cao/scripts" && sudo -u "$OWNER_USER" bash -lc './setup_venv.sh')
  else
    # Fallback: create venv and install project if pyproject exists
    if [[ -f "$wc_repo/services/cao/pyproject.toml" ]]; then
      sudo -u "$OWNER_USER" bash -lc "python3 -m venv '$wc_repo/services/cao/.venv' && \
        source '$wc_repo/services/cao/.venv/bin/activate' && \
        pip install --upgrade pip && \
        pip install -e '$wc_repo/services/cao' || true"
    fi
  fi

  if [[ -f "$wc_repo/services/cao/systemd/cao-server.service" ]]; then
    echo "==> Installing CAO systemd service"
    install -m 644 "$wc_repo/services/cao/systemd/cao-server.service" /etc/systemd/system/cao-server.service
    systemctl daemon-reload
    systemctl enable cao-server.service
    systemctl restart cao-server.service || systemctl start cao-server.service
  else
    echo "==> CAO systemd unit not found; skipping"
  fi
}

mark_readonly_runs() {
  local pattern="$1"; local base="$(pwd)"
  [[ -z "$pattern" ]] && return
  echo "==> Marking READONLY for dirs matching '$pattern' under $base"
  find "$base" -maxdepth 1 -type d -name "$pattern" | while read -r dir; do
    local dname
    dname="$(basename "$dir")"
    echo "   - $dname"
    sudo -u "$OWNER_USER" touch "$dir/READONLY" || true
  done
}

main() {
  require_root
  apt_install
  maybe_install_docker
  prepare_dirs

  echo "==> Cloning/updating repositories"
  clone_or_update https://github.com/rogerlew/wepppy         "$WORKDIR/wepppy"
  clone_or_update https://github.com/wepp-in-the-woods/peridot   "$WORKDIR/peridot"
  clone_or_update https://github.com/wepp-in-the-woods/wepppy2   "$WORKDIR/wepppy2"
  clone_or_update https://github.com/wepp-in-the-woods/wepppyo3  "$WORKDIR/wepppyo3"
  clone_or_update https://github.com/rogerlew/rosetta        "$WORKDIR/rosetta"
  clone_or_update https://github.com/rogerlew/weppcloud-wbt  "$WORKDIR/weppcloud-wbt"
  clone_or_update https://github.com/rogerlew/markdown-extract   "$WORKDIR/markdown-extract"
  clone_or_update https://github.com/rogerlew/rq-dashboard   "$WORKDIR/rq-dashboard"

  install_uv
  install_rustup
  install_node_tools
  install_wctl
  touch_js_files
  copy_env_if_provided

  if [[ "$WITH_CAO" == "1" ]]; then
    install_cao_service
  fi

  if [[ -n "$READONLY_GLOB" ]]; then
    mark_readonly_runs "$READONLY_GLOB"
  fi

  echo "==> Done. You may now run:"
  echo "   - cd $WORKDIR/wepppy && docker compose --env-file docker/.env -f docker/docker-compose.dev.yml up --build"
  echo "   - Or use wctl helpers: wctl up, wctl run-pytest ..."
}

main "$@"

