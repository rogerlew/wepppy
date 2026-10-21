# Retained commands and replay procedure

Working repository: `/workdir/wepppy`. Python is
`/workdir/wepppy/.venv/bin/python`, with `PYTHONPATH=/workdir/wepppy`.
Scripts below live in this artifact directory. Use new destination directories;
preparation intentionally refuses an existing attempt. The actual baseline,
off and on paths are enumerated in `parity.json`.

## Build and input lineage

Native source copies are retained at
`/wc1/holdouts/watershed-channel-routing-closure-20261021/{baseline-source,instrumented-source}`.
Their source manifests and executable hashes are in `provenance.json`.
The baseline has the captured source; candidate differs only by
`native_observation.patch`. In each isolated `src/`, the watershed build command is:

    make FC=/usr/bin/gfortran LDFLAGS='-mcmodel=medium -no-pie -lz' wepp

Both isolated copies also built `wepp_hill` with the same flags; scientific comparisons use `wepp` for both
hillslope and watershed cards. No alternate hill executable is mixed into replay.
The default build initially failed to link zlib; the failed log is retained.
The same explicit linker flags were used for baseline and candidate.

The controlled source deck is `/wc1/runs/wb/wb34-impoundment-cohort/wepp/runs`.
`replay_controlled.py` records generated geometry, clones management/soil through
existing WEPPpy builders, and sets 44 years. All input bytes are manifested.
Real projects were copied with `wepppy.rq.project_rq_fork.prepare_fork_run`,
`undisturbify=False`, full run/output copying, actual NoDb controller classes,
and local status logging. No source project was modified. Complete isolated
forks and fork logs are retained at:

- `/wc1/holdouts/watershed-channel-routing-closure-20261021/real-project`
  and `project-fork.log`: `lt_202012_0_Near_Burton_Creek_PrescFire`.
- `/workdir/watershed-channel-routing-closure-20261021/real-project-second`
  and `project-fork-second.log`: `tight-orthodontist`.

## Replay commands

Run each command with baseline binary and a new baseline destination, then with
candidate binary and new off/on destinations. Only on receives `--observe`.
Both binary paths end in `src/wepp` under the retained source roots above.

    python replay_controlled.py --root NEW_CONTROLLED_ROOT --binary BINARY [--observe]
    python replay_project.py --source RETAINED_PROJECT_FORK --root NEW_PROJECT_ROOT --binary BINARY [--observe]
    python replay_extensions.py --root NEW_EXTENSION_ROOT --mode prepare
    python replay_extensions.py --root NEW_EXTENSION_ROOT --mode baseline --binary BASELINE_BINARY
    python replay_extensions.py --root NEW_EXTENSION_ROOT --mode off --binary CANDIDATE_BINARY
    python replay_extensions.py --root NEW_EXTENSION_ROOT --mode on --binary CANDIDATE_BINARY

The scripts retain complete stdin cards, stdout/stderr, input hashes, executable
hashes, output hashes, elapsed time, and successful-completion checks. The current
project harness includes explicit legacy-to-HBP prompt migration matching
`wepp_runner/wepp_runner.py::_watershed_prompt_contract_lines`. Earlier rejected
prompt attempts are retained as `*.failed-card.*`, `execution.failed-card.json`,
`deck-correction.json`, and `failed-prompt-artifacts/`. Empty `delete.me` scratch
files from rejected attempts were retained there, not excluded from parity rules.

Observations use `wepp_observe.on`, with frost filtering absent, and existing
`WB33_M1A_BAL_DIAG=1` / `WB33_M7_PUBLISH_TRACE=1` diagnostics with per-attempt CSV
paths. Hillslope logs in project/topology cases are retained separately; standalone
hill element 1 maps to its `pN.run` filename. Baseline/off do not set these flags.
An early NFS observation run was interrupted because per-record open/close I/O
was slow; `controlled-on/interruption.json` retains that attempt. Complete on
runs use the local filesystem. Timing therefore includes filesystem differences
and must not be interpreted as a controlled instrumentation benchmark.

## Readback and diagnostic verification

    python audit_workbook.py /wc1/holdouts/watershed-channel-routing-closure-20261021/Water_Balance_S_Shape_0.6_0.4_Corrected.xlsx workbook_audit.json
    python audit_replays.py --root /workdir/watershed-channel-routing-closure-20261021/controlled-on --output /workdir/watershed-channel-routing-closure-20261021/audit
    python finalize_evidence.py

The final command regenerates package receipts and the full channel ledger at
`/workdir/watershed-channel-routing-closure-20261021/audit-complete/`.
Readback uses the independently installed native HBP interchange parser; its
extension identity is in provenance. Missing/duplicate/nonfinite diagnostic
records must reject before residual grading. Positive controls mutate copied
CSV data only. No full-domain conservation claim is generated.

## Checks executed

From `/workdir/wepp-forest`:

    fortitude check src/wshpas.f90
    python -m pytest tests/test_wshpas_leap_day_guard.py tests/test_wshpas_trise_guard.py tests/test_wshpas_pass_metadata_guard.py tests/test_compare_wepp_outputs.py tests/test_compare_wepp_raw_outputs.py -q
    fpm test --target wshpas_router_contract
    git diff --check -- src/wshpas.f90 src/wshred.for src/wepp_observe.for docs/contracts/pass-and-output-contracts.md

Fortitude passed; 13 pytest tests passed; the router contract passed. Native test
logs are retained in the holdout root. These supplement actual replay parity.
No release/vendoring gate or production deployment was attempted.

From `/workdir/wepppy`:

    wctl doc-lint --path docs/work-packages/20261021_watershed_channel_routing_closure
    tools/check_agents_size.sh AGENTS.md
    git diff --check -- docs/work-packages/20261021_watershed_channel_routing_closure AGENTS.md PROJECT_TRACKER.md

The native contract document passed `markdown-doc lint --path
docs/contracts/pass-and-output-contracts.md` from the native repository. Passing
an absolute out-of-repository path to `wctl doc-lint` panicked in the linter;
scoping the same canonical linter to the owning repository succeeded. Smallest
tooling follow-up: reject out-of-root paths with a clear diagnostic.
