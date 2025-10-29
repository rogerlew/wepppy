#!/usr/bin/env bash
set -euo pipefail

# ci_samurai_dryrun.sh — Orchestrate a CI Samurai dry run across nuc1/nuc2/nuc3
#
# Runs triage on nuc1 (NoDb + WEPP pytest), validates on nuc2, and exercises
# flaky reproduction loops on nuc3. Collects artifacts locally then publishes
# them into nuc1:/wc1/ci-samurai/logs/<timestamp>/.
#
# Usage:
#   bash services/cao/scripts/ci_samurai_dryrun.sh
#   bash services/cao/scripts/ci_samurai_dryrun.sh --nuc1 hostA --nuc2 hostB --nuc3 hostC
#   bash services/cao/scripts/ci_samurai_dryrun.sh --nodb-only
#
# Flags:
#   --nuc1 <host>       SSH host for triage (default: nuc1)
#   --nuc2 <host>       SSH host for validation (default: nuc2)
#   --nuc3 <host>       SSH host for flake loops (default: nuc3)
#   --repo <path>       Repo path on remote hosts (default: /workdir/wepppy)
#   --wc1 <path>        WC root on nuc1 (default: /wc1)
#   --loops <n>         Flake loop count on nuc3 (default: 10)
#   --nodb-only         Only run tests/nodb
#   --wepp-only         Only run tests/wepp
#

NUC1=${NUC1:-nuc1}
NUC2=${NUC2:-nuc2}
NUC3=${NUC3:-nuc3}
REPO=${REPO:-/workdir/wepppy}
WC1=${WC1:-/wc1}
LOOPS=${LOOPS:-10}
RUN_NODB=1
RUN_WEPP=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --nuc1) NUC1="$2"; shift 2;;
    --nuc2) NUC2="$2"; shift 2;;
    --nuc3) NUC3="$2"; shift 2;;
    --repo) REPO="$2"; shift 2;;
    --wc1)  WC1="$2"; shift 2;;
    --loops) LOOPS="$2"; shift 2;;
    --nodb-only) RUN_WEPP=0; shift;;
    --wepp-only) RUN_NODB=0; shift;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

TS=$(date +%F_%H-%M-%S)
LOCAL_OUT=$(mktemp -d "/tmp/ci-samurai-${TS}-XXXX")
DEST_REMOTE_DIR="${WC1}/ci-samurai/logs/${TS}"

echo "==> Config"
echo "NUC1=$NUC1 NUC2=$NUC2 NUC3=$NUC3"
echo "REPO=$REPO WC1=$WC1 LOOPS=$LOOPS"
echo "LOCAL_OUT=$LOCAL_OUT"

run_remote() {
  local host="$1"; shift
  ssh "$host" "$@"
}

copy_from_remote() {
  local host="$1" src="$2" dest="$3"
  scp -q "${host}:${src}" "$dest" || true
}

echo "==> Triage on $NUC1"
run_remote "$NUC1" "bash -lc 'cd $REPO && wctl up -d --wait || true'" || true

if [[ "$RUN_NODB" == "1" ]]; then
  run_remote "$NUC1" "bash -lc 'cd $REPO && wctl run-pytest tests/nodb --tb=short --maxfail=20 | tee /tmp/triage_nodb.txt'"
  copy_from_remote "$NUC1" "/tmp/triage_nodb.txt" "$LOCAL_OUT/triage_nodb.txt"
fi

if [[ "$RUN_WEPP" == "1" ]]; then
  run_remote "$NUC1" "bash -lc 'cd $REPO && wctl run-pytest tests/wepp --tb=short --maxfail=20 | tee /tmp/triage_wepp.txt'"
  copy_from_remote "$NUC1" "/tmp/triage_wepp.txt" "$LOCAL_OUT/triage_wepp.txt"
fi

echo "==> Extract first failing test from nuc1 logs"
FIRST_FAIL=""
if [[ -f "$LOCAL_OUT/triage_nodb.txt" ]]; then
  FIRST_FAIL=$(grep -Eo 'tests/nodb/[^ ]+::[A-Za-z0-9_]+' "$LOCAL_OUT/triage_nodb.txt" | head -n1 || true)
fi
if [[ -z "$FIRST_FAIL" && -f "$LOCAL_OUT/triage_wepp.txt" ]]; then
  FIRST_FAIL=$(grep -Eo 'tests/wepp/[^ ]+::[A-Za-z0-9_]+' "$LOCAL_OUT/triage_wepp.txt" | head -n1 || true)
fi
echo "First failing test: ${FIRST_FAIL:-<none>}"

if [[ -n "$FIRST_FAIL" ]]; then
  echo "==> Single rerun on $NUC1 to check for flake"
  run_remote "$NUC1" "bash -lc 'cd $REPO && wctl run-pytest -q ${FIRST_FAIL} || true'"
  run_remote "$NUC1" "bash -lc 'cd $REPO && printf "%s\n" "${FIRST_FAIL}" > /tmp/first_fail.txt'"
  copy_from_remote "$NUC1" "/tmp/first_fail.txt" "$LOCAL_OUT/first_fail.txt"
fi

echo "==> Validation on $NUC2"
run_remote "$NUC2" "bash -lc 'cd $REPO && git reset --hard origin/master && git clean -xfd'" || true
if [[ -n "$FIRST_FAIL" ]]; then
  run_remote "$NUC2" "bash -lc 'cd $REPO && wctl run-pytest -q ${FIRST_FAIL} | tee /tmp/validate_first.txt'" || true
  copy_from_remote "$NUC2" "/tmp/validate_first.txt" "$LOCAL_OUT/validate_first.txt"
else
  # fallback minimal validation
  run_remote "$NUC2" "bash -lc 'cd $REPO && wctl run-pytest tests/nodb -q --maxfail=1 | tee /tmp/validate_min.txt'" || true
  copy_from_remote "$NUC2" "/tmp/validate_min.txt" "$LOCAL_OUT/validate_min.txt"
fi

if [[ -n "$FIRST_FAIL" ]]; then
  echo "==> Flake loop on $NUC3 ($LOOPS runs)"
  run_remote "$NUC3" "bash -lc 'cd $REPO && for i in \\$(seq 1 $LOOPS); do echo RUN \\${i}; wctl run-pytest -q ${FIRST_FAIL} || true; done | tee /tmp/flake_loop.txt'" || true
  copy_from_remote "$NUC3" "/tmp/flake_loop.txt" "$LOCAL_OUT/flake_loop.txt"
fi

echo "==> Publish artifacts to $NUC1:$DEST_REMOTE_DIR"
run_remote "$NUC1" "mkdir -p '$DEST_REMOTE_DIR'"
scp -q "$LOCAL_OUT"/* "${NUC1}:${DEST_REMOTE_DIR}/" || true

echo "==> Local artifacts: $LOCAL_OUT"
echo "==> Remote artifacts: ${NUC1}:${DEST_REMOTE_DIR}"
echo "Done."

