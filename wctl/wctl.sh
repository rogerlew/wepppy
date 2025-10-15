#!/bin/bash

set -euo pipefail

# The absolute path to your project's root directory
PROJECT_DIR="/workdir/wepppy"
SOURCE_ENV="${PROJECT_DIR}/docker/.env"

cd "$PROJECT_DIR" || exit 1

if [[ ! -f "$SOURCE_ENV" ]]; then
  echo "Expected env file at ${SOURCE_ENV} (see readme quick-start)." >&2
  exit 1
fi

TEMP_ENV=$(mktemp -t wctl-env-XXXXXXXX)
cleanup() {
  rm -f "$TEMP_ENV"
}
trap cleanup EXIT

python - "$SOURCE_ENV" "$TEMP_ENV" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
lines = []
for raw in src.read_text().splitlines():
    if not raw or raw.lstrip().startswith("#"):
        lines.append(raw)
        continue
    if "=" not in raw:
        lines.append(raw)
        continue
    key, value = raw.split("=", 1)
    value = value.replace("$", "$$")
    lines.append(f"{key}={value}")
dst.write_text("\n".join(lines) + "\n")
PY

export WEPPPY_ENV_FILE="$TEMP_ENV"

docker compose --env-file "$TEMP_ENV" -f docker/docker-compose.dev.yml "$@"
