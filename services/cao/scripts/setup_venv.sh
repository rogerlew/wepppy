#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=${VENV_DIR:-.venv}
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "[CAO] Using root dir: $ROOT_DIR"

if [[ ! -d "$ROOT_DIR/$VENV_DIR" ]]; then
  echo "[CAO] Creating venv at $ROOT_DIR/$VENV_DIR"
  uv venv "$ROOT_DIR/$VENV_DIR"
fi

source "$ROOT_DIR/$VENV_DIR/bin/activate"
echo "[CAO] Python: $(python --version)"

echo "[CAO] Installing Python dependencies (uv sync)"
uv sync

echo "[CAO] Ensuring maturin is available"
if ! command -v maturin >/dev/null 2>&1; then
  echo "[CAO] maturin not found in venv; installing..."
  uv pip install maturin
fi

MARKDOWN_EXTRACT_MANIFEST=${MARKDOWN_EXTRACT_MANIFEST:-/workdir/markdown-extract/crates/markdown_extract_py/Cargo.toml}
if [[ -f "$MARKDOWN_EXTRACT_MANIFEST" ]]; then
  echo "[CAO] Building markdown-extract Python bindings via maturin"
  maturin develop --manifest-path "$MARKDOWN_EXTRACT_MANIFEST" --release
else
  echo "[CAO] WARNING: markdown-extract manifest not found at $MARKDOWN_EXTRACT_MANIFEST"
  echo "        Set MARKDOWN_EXTRACT_MANIFEST to the path of Cargo.toml and rerun."
fi

echo "[CAO] Done. Try: cao --version && cao-server --help"

