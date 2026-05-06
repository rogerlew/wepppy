# wepp_runner/AGENTS.md
> Agent guide for vendoring and maintaining WEPP binaries used by `wepp_runner`.

## Authorship
**This document and all AGENTS.md documents are maintained by GitHub Copilot / Codex which retain full authorship rights for all AGENTS.md content revisions. Agents can author AGENTS.md document when and where they see fit.**

## Purpose
`wepp_runner` wraps WEPP executable invocation for hillslope, flowpath, and watershed runs.  
This guide defines the required vendoring workflow for binaries in `wepp_runner/bin`.

## Scope
Applies to:
- `wepp_runner/wepp_runner.py`
- `wepp_runner/bin/*`
- `wepp_runner/templates/*`

## Binary Naming Contract
- Vendor binaries as `wepp_<tag>` and `wepp_<tag>_hill` (example: `wepp_260324`).
- Do not rename or remove existing historical binaries unless explicitly requested.
- Keep `wepp` / `latest` behavior stable unless the task explicitly requires changing defaults.

## Required Quality Gate Before Vendoring (Must)
Before copying any new binary into `wepp_runner/bin`, manual tests in `/workdir/wepp-forest` must pass.

From `/workdir/wepp-forest/src`:
```bash
make clean
make all
```

From `/workdir/wepp-forest`:
```bash
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill
python tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/src/wepp_hill
pytest
```

If any command fails, do not vendor.

## Vendoring Procedure
From `/workdir/wepppy`:
```bash
install -m 0755 /workdir/wepp-forest/src/wepp wepp_runner/bin/wepp_<tag>
install -m 0755 /workdir/wepp-forest/src/wepp_hill wepp_runner/bin/wepp_<tag>_hill
```

## Post-Vendor Validation (Must)
From `/workdir/wepppy`:
```bash
tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_<tag> wepp_runner/bin/wepp_<tag>_hill
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>
tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_<tag>_hill
pytest tests/wepp_runner/test_run_hillslope_retries.py tests/wepp/test_wepp_runner_outputs.py
```

Provenance gate policy (enforced by `tools/check_wepp_binary_provenance.sh`):
- required interpreter: `/lib64/ld-linux-x86-64.so.2`
- reject Homebrew/Conda loader and runtime paths
- reject unexpected non-system `RPATH/RUNPATH` and non-system `libgfortran` sources

Canonical reference:
- `docs/binary-lifecycle.md`

Optional when container is running:
```bash
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_<tag>
tools/smoke_wepp_binary_in_container.sh wepp_runner/bin/wepp_<tag>_hill
```

## Watershed Stall Debugging (Observability)
Use these steps when a watershed run appears stuck or hits RQ timeout.

1. Enable phase logging in the run directory:
```bash
touch /wc1/runs/<project>/<scenario>/wepp/runs/wepp_observe.on
```
2. Re-run the watershed binary from that run directory.
3. Inspect `wepp_observe.log` for the last completed phase marker.
4. Remove the flag for normal/parity timing runs:
```bash
rm -f /wc1/runs/<project>/<scenario>/wepp/runs/wepp_observe.on
```

Notes:
- `wepp_observe.on` is an opt-in runtime flag; no flag means no phase log.
- Logging adds overhead; keep it off for performance or parity timing checks.

## Runner Traceability Fields
Continuous `run_hillslope` and `run_watershed` stderr logs begin with runner context for incident triage.

- `run_hillslope`: `wepp_id`, `runs_dir`, `run_file`, `err_file`, `cmd`, `timeout`, and `timeout_retries`.
- `run_watershed`: `runs_dir`, `run_file`, `err_file`, `cmd`, and `attempt=1/1`.
- Both in-scope runners emit `binary_identity` with `binary_path`, `binary_sha256`, `binary_size_bytes`, `binary_mtime_ns`, `binary_identity_status`, and `binary_identity_error`.
- `binary_identity_status=unavailable` means the run continued but the hash or file metadata could not be read; inspect `binary_identity_error`.
- Watershed close-path I/O failures emit `close_path_failure` with `stream`, `path`, `classification`, `errno`, and `error`. `classification=stale_file_handle` identifies the NFS stale-handle signature.

## D-State Watchdog Telemetry
`run_hillslope` and `run_watershed` start a Linux best-effort watchdog for prolonged uninterruptible sleep (`D`) process state. It only writes telemetry and never signals or kills the WEPP process.

Environment controls:
- `WEPP_RUNNER_DSTATE_WATCHDOG_ENABLED`: default enabled on Linux when `/proc` exists; set `0`, `false`, `no`, or `off` to disable.
- `WEPP_RUNNER_DSTATE_WATCHDOG_INTERVAL_S`: poll interval, default `30.0`, minimum `0.1`.
- `WEPP_RUNNER_DSTATE_WATCHDOG_THRESHOLD_S`: continuous D-state duration before logging, default `180.0`.
- `WEPP_RUNNER_DSTATE_WATCHDOG_MAX_EVENTS`: maximum log lines per process, default `3`; set `0` to suppress emissions.

Watchdog lines look like `[run_watershed] dstate_watchdog ...` and include `pid`, `duration`, `threshold`, `interval`, run paths, and command text.

## Debug/Parity Tools
Use these tools from `/workdir/wepp-forest` when triaging binary behavior:

- Progress/stall observer (run cwd + PID aware):
```bash
python3 tools/observe_wepp_progress.py --run-dir /wc1/runs/<project>/<scenario>/wepp/runs --stall-seconds 180
```
- Host smoke gate for candidate binaries:
```bash
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp
tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/src/wepp_hill
```
- Raw output parity compare (baseline vs candidate outputs):
```bash
python3 /workdir/wepp-forest/tools/compare_wepp_raw_outputs.py \
  --baseline /tmp/wepp-parity-baseline \
  --candidate /tmp/wepp-parity-candidate \
  --json-out /tmp/wepp_parity_raw.json \
  --abs-tol 1e-6 --rel-tol 0
```

## Implementation Notes
- `wepp_runner.wepp_runner.get_linux_wepp_bin_opts()` auto-discovers `wepp_*` files in `wepp_runner/bin`.
- `_hill` variants are invoked automatically for hillslope/flowpath runs when present.
- Prefer explicit failures to silent fallback behavior in binary selection and process execution paths.
- Watershed run-file tail prompts are binary-contract aware:
  - legacy contract (no sidecar): includes initial-condition filename placeholder and omits impoundment output/data prompts.
  - modern contract (`features.hbp_supported=true` sidecar): omits initial-condition placeholder and includes impoundment output/data prompts (`pw0.imp`).
- Prompt-contract selection is sidecar-driven and must remain deterministic:
  sidecar absence defaults to legacy behavior.
