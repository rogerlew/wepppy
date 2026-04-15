#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/run_migrations_container.sh [options]

Run WEPPpy migrations in a standalone Docker container (outside docker compose / RQ).
The container writes checkpoint files so runs can be resumed safely.

Options:
  --run-root PATH              Host directory that contains run directories.
                               Default: /geodata/wc1/runs (or /wc1/runs if available)
  --run-pattern GLOB           Glob for run directory names when using pattern discovery.
                               Default: *
  --run-list FILE              File containing run targets (one per line).
                               Line formats:
                                 - runid (example: lt_202012_0_Near_Burton_Creek_CurCond)
                                 - relative path from run root (example: lt/lt_202012_...)
                                 - absolute path under --run-root
  --find-maxdepth N            Max depth for pattern discovery.
                               Default: 2
  --max-runs N                 Limit run count after selection (0 = no limit).
                               Default: 0
  --state-root PATH            Host directory for migration state/checkpoints.
                               Default: <run-root>/_migration_state
  --token TOKEN                Explicit state token for a new run set.
                               Default: UTC timestamp
  --resume-token TOKEN         Resume an existing run set token.
  --image IMAGE                Docker image/tag to run.
                               Default: ${WEPPCLOUD_IMAGE:-wepppy:latest}
  --container-name NAME        Docker container name.
                               Default: migrations-<token>
  --data-mount-src PATH        Host mount source for run data.
                               Default: /geodata/wc1 (or /wc1)
  --data-mount-dst PATH        Container mount destination for run data.
                               Default: /wc1
  --container-run-root PATH    Run root path inside the container.
                               Default: derived from run root + mount mapping
  --env-file PATH              Optional env file for docker run.
                               Default: docker/defaults.env when present
  --redis-password-file PATH   Optional redis_password file to mount as /run/secrets/redis_password.
                               Default: docker/secrets/redis_password when present
  --archive-before             Pass --archive-before to migration runner.
  --dry-run                    Pass --dry-run to migration runner.
  --force                      Pass --force to migration runner.
  --only NAME                  Pass --only NAME (repeatable).
  --sleep-secs N               Sleep between runs.
                               Default: 0
  --no-write-version           Do not stamp nodb.version after successful migration.
  --no-detach                  Run foreground (attached) instead of detached.
  -h, --help                   Show this help.

Examples:
  scripts/run_migrations_container.sh \
    --run-root /geodata/wc1/runs \
    --run-pattern 'lt_202012_*' \
    --find-maxdepth 2 \
    --archive-before

  scripts/run_migrations_container.sh --resume-token 20260414T183000Z
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

require_numeric() {
  local value="$1"
  local label="$2"
  if ! [[ "${value}" =~ ^[0-9]+$ ]]; then
    die "${label} must be a non-negative integer: ${value}"
  fi
}

contains_nodb_files() {
  local directory="$1"
  find "${directory}" -maxdepth 1 -type f -name '*.nodb' -print -quit | grep -q .
}

resolve_abs() {
  local path="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath -m "${path}"
  else
    python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "${path}"
  fi
}

timestamp_utc() {
  date -u +%Y%m%dT%H%M%SZ
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

default_data_mount_src=""
if [[ -d "/geodata/wc1" ]]; then
  default_data_mount_src="/geodata/wc1"
elif [[ -d "/wc1" ]]; then
  default_data_mount_src="/wc1"
fi

RUN_ROOT_DEFAULT=""
if [[ -n "${default_data_mount_src}" ]]; then
  RUN_ROOT_DEFAULT="${default_data_mount_src}/runs"
fi

RUN_ROOT="${RUN_ROOT:-${RUN_ROOT_DEFAULT}}"
RUN_PATTERN="${RUN_PATTERN:-*}"
RUN_LIST_FILE=""
FIND_MAXDEPTH="${FIND_MAXDEPTH:-2}"
MAX_RUNS="${MAX_RUNS:-0}"

STATE_ROOT=""
STATE_TOKEN=""
RESUME_TOKEN=""

IMAGE="${IMAGE:-${WEPPCLOUD_IMAGE:-wepppy:latest}}"
CONTAINER_NAME=""
DATA_MOUNT_SRC="${DATA_MOUNT_SRC:-${default_data_mount_src}}"
DATA_MOUNT_DST="${DATA_MOUNT_DST:-/wc1}"
CONTAINER_RUN_ROOT="${CONTAINER_RUN_ROOT:-}"

ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/docker/defaults.env}"
REDIS_PASSWORD_FILE="${REDIS_PASSWORD_FILE:-${PROJECT_DIR}/docker/secrets/redis_password}"

ARCHIVE_BEFORE=false
DRY_RUN=false
FORCE=false
WRITE_VERSION=true
DETACH=true
SLEEP_SECS="${SLEEP_SECS:-0}"
ONLY_MIGRATIONS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-root)
      RUN_ROOT="$2"
      shift 2
      ;;
    --run-pattern)
      RUN_PATTERN="$2"
      shift 2
      ;;
    --run-list)
      RUN_LIST_FILE="$2"
      shift 2
      ;;
    --find-maxdepth)
      FIND_MAXDEPTH="$2"
      shift 2
      ;;
    --max-runs)
      MAX_RUNS="$2"
      shift 2
      ;;
    --state-root)
      STATE_ROOT="$2"
      shift 2
      ;;
    --token)
      STATE_TOKEN="$2"
      shift 2
      ;;
    --resume-token)
      RESUME_TOKEN="$2"
      shift 2
      ;;
    --image)
      IMAGE="$2"
      shift 2
      ;;
    --container-name)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --data-mount-src)
      DATA_MOUNT_SRC="$2"
      shift 2
      ;;
    --data-mount-dst)
      DATA_MOUNT_DST="$2"
      shift 2
      ;;
    --container-run-root)
      CONTAINER_RUN_ROOT="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --redis-password-file)
      REDIS_PASSWORD_FILE="$2"
      shift 2
      ;;
    --archive-before)
      ARCHIVE_BEFORE=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --only)
      ONLY_MIGRATIONS+=("$2")
      shift 2
      ;;
    --sleep-secs)
      SLEEP_SECS="$2"
      shift 2
      ;;
    --no-write-version)
      WRITE_VERSION=false
      shift
      ;;
    --no-detach)
      DETACH=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

require_numeric "${FIND_MAXDEPTH}" "find-maxdepth"
require_numeric "${MAX_RUNS}" "max-runs"
require_numeric "${SLEEP_SECS}" "sleep-secs"

if [[ -z "${RUN_ROOT}" ]]; then
  die "run root is not set and no default could be inferred; pass --run-root"
fi

RUN_ROOT="$(resolve_abs "${RUN_ROOT}")"
[[ -d "${RUN_ROOT}" ]] || die "run root does not exist: ${RUN_ROOT}"

if [[ -z "${DATA_MOUNT_SRC}" ]]; then
  die "data mount source could not be inferred; pass --data-mount-src"
fi
DATA_MOUNT_SRC="$(resolve_abs "${DATA_MOUNT_SRC}")"
[[ -d "${DATA_MOUNT_SRC}" ]] || die "data mount source does not exist: ${DATA_MOUNT_SRC}"

if [[ -z "${STATE_ROOT}" ]]; then
  STATE_ROOT="${RUN_ROOT}/_migration_state"
fi
STATE_ROOT="$(resolve_abs "${STATE_ROOT}")"
mkdir -p "${STATE_ROOT}"

if [[ -z "${CONTAINER_RUN_ROOT}" ]]; then
  case "${RUN_ROOT}" in
    "${DATA_MOUNT_SRC}")
      CONTAINER_RUN_ROOT="${DATA_MOUNT_DST}"
      ;;
    "${DATA_MOUNT_SRC}"/*)
      CONTAINER_RUN_ROOT="${DATA_MOUNT_DST}${RUN_ROOT#${DATA_MOUNT_SRC}}"
      ;;
    *)
      die "run root (${RUN_ROOT}) is not under data-mount-src (${DATA_MOUNT_SRC}); pass --container-run-root"
      ;;
  esac
fi

if [[ -n "${RESUME_TOKEN}" && -n "${STATE_TOKEN}" ]]; then
  die "use either --token or --resume-token, not both"
fi

if [[ -n "${RESUME_TOKEN}" ]]; then
  token="${RESUME_TOKEN}"
else
  token="${STATE_TOKEN:-$(timestamp_utc)}"
fi

RUN_STATE_DIR="${STATE_ROOT}/${token}"
ALL_RUNS_FILE="${RUN_STATE_DIR}/all_runs.txt"
DONE_FILE="${RUN_STATE_DIR}/done.txt"
FAILED_FILE="${RUN_STATE_DIR}/failed.txt"
RUNNER_LOG="${RUN_STATE_DIR}/runner.log"
INNER_SCRIPT="${RUN_STATE_DIR}/runner_inner.sh"
META_FILE="${RUN_STATE_DIR}/meta.env"

if [[ -n "${RESUME_TOKEN}" ]]; then
  [[ -d "${RUN_STATE_DIR}" ]] || die "resume token state dir not found: ${RUN_STATE_DIR}"
  [[ -f "${ALL_RUNS_FILE}" ]] || die "resume token is missing ${ALL_RUNS_FILE}"
  touch "${DONE_FILE}" "${FAILED_FILE}"
else
  mkdir -p "${RUN_STATE_DIR}"

  declare -a run_relpaths=()
  declare -A seen=()

  add_run_relpath() {
    local rel="$1"
    [[ -n "${rel}" ]] || return 0
    if [[ -z "${seen["${rel}"]+x}" ]]; then
      seen["${rel}"]=1
      run_relpaths+=("${rel}")
    fi
  }

  if [[ -n "${RUN_LIST_FILE}" ]]; then
    [[ -f "${RUN_LIST_FILE}" ]] || die "run list file not found: ${RUN_LIST_FILE}"
    while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
      line="${raw_line%%#*}"
      line="${line#"${line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
      [[ -n "${line}" ]] || continue

      target_path=""
      if [[ "${line}" = /* ]]; then
        target_path="$(resolve_abs "${line}")"
      elif [[ "${line}" == */* ]]; then
        target_path="$(resolve_abs "${RUN_ROOT}/${line}")"
      else
        mapfile -t matches < <(find "${RUN_ROOT}" -mindepth 1 -maxdepth "${FIND_MAXDEPTH}" -type d -name "${line}" | sort)
        if [[ ${#matches[@]} -eq 0 ]]; then
          die "run list entry not found under run root: ${line}"
        fi
        if [[ ${#matches[@]} -gt 1 ]]; then
          die "run list entry is ambiguous (${line}); use relative or absolute path"
        fi
        target_path="$(resolve_abs "${matches[0]}")"
      fi

      case "${target_path}" in
        "${RUN_ROOT}"/*) ;;
        *)
          die "run list target is outside run root: ${target_path}"
          ;;
      esac

      [[ -d "${target_path}" ]] || die "run list target is not a directory: ${target_path}"
      if ! contains_nodb_files "${target_path}"; then
        die "run list target is missing top-level .nodb files: ${target_path}"
      fi

      rel="${target_path#${RUN_ROOT}/}"
      add_run_relpath "${rel}"
    done < "${RUN_LIST_FILE}"
  else
    while IFS= read -r target_path; do
      [[ -n "${target_path}" ]] || continue
      if contains_nodb_files "${target_path}"; then
        rel="${target_path#${RUN_ROOT}/}"
        add_run_relpath "${rel}"
      fi
    done < <(find "${RUN_ROOT}" -mindepth 1 -maxdepth "${FIND_MAXDEPTH}" -type d -name "${RUN_PATTERN}" | sort)
  fi

  if [[ ${#run_relpaths[@]} -eq 0 ]]; then
    die "no run directories matched selection"
  fi

  if [[ "${MAX_RUNS}" -gt 0 && ${#run_relpaths[@]} -gt "${MAX_RUNS}" ]]; then
    run_relpaths=("${run_relpaths[@]:0:${MAX_RUNS}}")
  fi

  printf '%s\n' "${run_relpaths[@]}" > "${ALL_RUNS_FILE}"
  : > "${DONE_FILE}"
  : > "${FAILED_FILE}"
fi

total_runs=$(wc -l < "${ALL_RUNS_FILE}" | tr -d ' ')
done_runs=$(wc -l < "${DONE_FILE}" | tr -d ' ')
pending_runs=$((total_runs - done_runs))
if [[ "${pending_runs}" -lt 0 ]]; then
  pending_runs=0
fi

if [[ -z "${CONTAINER_NAME}" ]]; then
  CONTAINER_NAME="migrations-${token}"
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
  die "container name already exists: ${CONTAINER_NAME}"
fi

image_ref="$(docker image inspect "${IMAGE}" --format '{{.Id}}' 2>/dev/null || true)"
if [[ -z "${image_ref}" ]]; then
  die "docker image not found locally: ${IMAGE}"
fi

only_csv=""
if [[ ${#ONLY_MIGRATIONS[@]} -gt 0 ]]; then
  only_csv="$(IFS=,; echo "${ONLY_MIGRATIONS[*]}")"
fi

cat > "${INNER_SCRIPT}" <<'EOF'
#!/usr/bin/env bash

set -euo pipefail

STATE_DIR="${STATE_DIR:-/migration_state}"
ALL_RUNS_FILE="${ALL_RUNS_FILE:-${STATE_DIR}/all_runs.txt}"
DONE_FILE="${DONE_FILE:-${STATE_DIR}/done.txt}"
FAILED_FILE="${FAILED_FILE:-${STATE_DIR}/failed.txt}"
RUNNER_LOG="${RUNNER_LOG:-${STATE_DIR}/runner.log}"

CONTAINER_RUN_ROOT="${CONTAINER_RUN_ROOT:?CONTAINER_RUN_ROOT is required}"
SLEEP_SECS="${SLEEP_SECS:-0}"
ARCHIVE_BEFORE="${ARCHIVE_BEFORE:-0}"
DRY_RUN="${DRY_RUN:-0}"
FORCE="${FORCE:-0}"
WRITE_VERSION="${WRITE_VERSION:-1}"
ONLY_MIGRATIONS_CSV="${ONLY_MIGRATIONS_CSV:-}"

append_unique() {
  local file="$1"
  local value="$2"
  if ! grep -Fxq "${value}" "${file}" 2>/dev/null; then
    printf '%s\n' "${value}" >> "${file}"
  fi
}

build_migration_args() {
  MIGRATION_ARGS=()
  if [[ "${ARCHIVE_BEFORE}" == "1" ]]; then
    MIGRATION_ARGS+=("--archive-before")
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    MIGRATION_ARGS+=("--dry-run")
  fi
  if [[ "${FORCE}" == "1" ]]; then
    MIGRATION_ARGS+=("--force")
  fi

  if [[ -n "${ONLY_MIGRATIONS_CSV}" ]]; then
    IFS=',' read -r -a only_items <<< "${ONLY_MIGRATIONS_CSV}"
    for migration_name in "${only_items[@]}"; do
      [[ -n "${migration_name}" ]] || continue
      MIGRATION_ARGS+=("--only" "${migration_name}")
    done
  fi
}

run_one() {
  local rel_path="$1"
  local wd="${CONTAINER_RUN_ROOT}/${rel_path}"
  local runid
  runid="$(basename "${wd}")"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  echo "[$ts] START ${runid} (${wd})" | tee -a "${RUNNER_LOG}"
  build_migration_args

  local success=0
  if /opt/venv/bin/python -m wepppy.tools.migrations.migrate_run --wd "${wd}" "${MIGRATION_ARGS[@]}" 2>&1 | tee -a "${RUNNER_LOG}"; then
    if [[ "${WRITE_VERSION}" == "1" && "${DRY_RUN}" != "1" ]]; then
      if /opt/venv/bin/python - "${wd}" 2>&1 <<'PY' | tee -a "${RUNNER_LOG}"; then
import sys
from wepppy.nodb.version import CURRENT_VERSION, write_version

wd = sys.argv[1]
write_version(wd, CURRENT_VERSION)
print(f"Wrote nodb.version={CURRENT_VERSION} for {wd}")
PY
        success=1
      else
        echo "Failed to write nodb.version for ${wd}" | tee -a "${RUNNER_LOG}"
      fi
    else
      success=1
    fi
  fi

  if [[ "${success}" == "1" ]]; then
    append_unique "${DONE_FILE}" "${rel_path}"
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "[$ts] OK ${runid}" | tee -a "${RUNNER_LOG}"
  else
    append_unique "${FAILED_FILE}" "${rel_path}"
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "[$ts] FAIL ${runid}" | tee -a "${RUNNER_LOG}"
  fi
}

[[ -f "${ALL_RUNS_FILE}" ]] || { echo "Missing ${ALL_RUNS_FILE}" >&2; exit 2; }
touch "${DONE_FILE}" "${FAILED_FILE}" "${RUNNER_LOG}"

while IFS= read -r rel_path || [[ -n "${rel_path}" ]]; do
  [[ -n "${rel_path}" ]] || continue
  if grep -Fxq "${rel_path}" "${DONE_FILE}" 2>/dev/null; then
    continue
  fi
  run_one "${rel_path}"
  if [[ "${SLEEP_SECS}" != "0" ]]; then
    sleep "${SLEEP_SECS}"
  fi
done < "${ALL_RUNS_FILE}"

total_runs="$(wc -l < "${ALL_RUNS_FILE}" | tr -d ' ')"
done_runs="$(wc -l < "${DONE_FILE}" | tr -d ' ')"
failed_runs="$(wc -l < "${FAILED_FILE}" | tr -d ' ')"
timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[$timestamp] COMPLETE total=${total_runs} done=${done_runs} failed=${failed_runs}" | tee -a "${RUNNER_LOG}"
EOF

chmod +x "${INNER_SCRIPT}"

cat > "${META_FILE}" <<EOF
TOKEN=${token}
IMAGE_REQUESTED=${IMAGE}
IMAGE_PINNED=${image_ref}
RUN_ROOT=${RUN_ROOT}
CONTAINER_RUN_ROOT=${CONTAINER_RUN_ROOT}
RUN_PATTERN=${RUN_PATTERN}
RUN_LIST_FILE=${RUN_LIST_FILE}
FIND_MAXDEPTH=${FIND_MAXDEPTH}
MAX_RUNS=${MAX_RUNS}
ARCHIVE_BEFORE=${ARCHIVE_BEFORE}
DRY_RUN=${DRY_RUN}
FORCE=${FORCE}
WRITE_VERSION=${WRITE_VERSION}
SLEEP_SECS=${SLEEP_SECS}
DATA_MOUNT_SRC=${DATA_MOUNT_SRC}
DATA_MOUNT_DST=${DATA_MOUNT_DST}
ENV_FILE=${ENV_FILE}
REDIS_PASSWORD_FILE=${REDIS_PASSWORD_FILE}
STATE_DIR=${RUN_STATE_DIR}
EOF

docker_args=(
  run
  --rm
  --name "${CONTAINER_NAME}"
  --volume "${DATA_MOUNT_SRC}:${DATA_MOUNT_DST}"
  --volume "${RUN_STATE_DIR}:/migration_state"
  --env "STATE_DIR=/migration_state"
  --env "ALL_RUNS_FILE=/migration_state/all_runs.txt"
  --env "DONE_FILE=/migration_state/done.txt"
  --env "FAILED_FILE=/migration_state/failed.txt"
  --env "RUNNER_LOG=/migration_state/runner.log"
  --env "CONTAINER_RUN_ROOT=${CONTAINER_RUN_ROOT}"
  --env "ARCHIVE_BEFORE=$([[ "${ARCHIVE_BEFORE}" == "true" ]] && echo 1 || echo 0)"
  --env "DRY_RUN=$([[ "${DRY_RUN}" == "true" ]] && echo 1 || echo 0)"
  --env "FORCE=$([[ "${FORCE}" == "true" ]] && echo 1 || echo 0)"
  --env "WRITE_VERSION=$([[ "${WRITE_VERSION}" == "true" ]] && echo 1 || echo 0)"
  --env "SLEEP_SECS=${SLEEP_SECS}"
  --env "ONLY_MIGRATIONS_CSV=${only_csv}"
  --env "PYTHONUNBUFFERED=1"
)

if [[ -f "${ENV_FILE}" ]]; then
  docker_args+=(--env-file "${ENV_FILE}")
fi

if [[ -f "${REDIS_PASSWORD_FILE}" ]]; then
  docker_args+=(
    --volume "${REDIS_PASSWORD_FILE}:/run/secrets/redis_password:ro"
    --env "REDIS_PASSWORD_FILE=/run/secrets/redis_password"
  )
fi

if [[ "${DETACH}" == "true" ]]; then
  docker_args+=(--detach)
fi

docker_args+=(
  "${image_ref}"
  bash
  /migration_state/runner_inner.sh
)

echo "Migration container launch summary:"
echo "  token:            ${token}"
echo "  image requested:  ${IMAGE}"
echo "  image pinned:     ${image_ref}"
echo "  container name:   ${CONTAINER_NAME}"
echo "  run root (host):  ${RUN_ROOT}"
echo "  run root (ctr):   ${CONTAINER_RUN_ROOT}"
echo "  runs total:       ${total_runs}"
echo "  runs done:        ${done_runs}"
echo "  runs pending:     ${pending_runs}"
echo "  state dir:        ${RUN_STATE_DIR}"
echo "  checkpoint files: ${DONE_FILE}, ${FAILED_FILE}"
echo ""

if [[ "${DETACH}" == "true" ]]; then
  container_id="$(docker "${docker_args[@]}")"
  echo "Started container ${CONTAINER_NAME} (${container_id})"
  echo "Tail logs:"
  echo "  docker logs -f ${CONTAINER_NAME}"
  echo "State tail:"
  echo "  tail -f ${RUNNER_LOG}"
else
  docker "${docker_args[@]}"
fi
