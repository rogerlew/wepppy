# Stream message inventory and regression fixtures

Status: proposed M0 transformation contract; executable proof pending.
Date: 2026-11-11 UTC. No captured private message bodies or credentials retained.
All examples below are synthetic fixtures tied to observed producer categories.

## Boundary and consumers

`wepppy/nodb/status_messenger.py` owns direct `publish`, `publish_command`, and
`StatusMessengerHandler.emit`. NoDb logger records flow through that handler;
therefore arbitrary log message arguments reach status even without a direct
publish call at the producer. The expanded failure matrix names discovered
producer families. Go status also needs an outbound guard because operator
Redis publication bypasses Python. No unrelated file logging policy changes.

Consumers are StatusStream (text, lifecycle, TRIGGER, EXCEPTION/job-info),
command-bar (command progress), run-sync dashboard (COMPLETE and EXCEPTION_JSON),
ag-fields (structured scheme/field/sub-field failures), and channel delineation
(DIAGNOSTICS_V1). Preflight renders the typed checklist, supported lock icons and
last-modified timestamp; its raw Redis hash is not a browser contract.

## Required transformations and fixtures

| Observed producer category | Synthetic input / test setup | Expected behavior |
| --- | --- | --- |
| land_and_soil/project workspace paths | `Processing /wc1/runs/ab/example/soils/input.sol` | Keep progress verb; replace entire absolute path with `[path]` |
| Windows/UNC path defensive cases | Absolute drive path or UNC share in progress | Same replacement; do not expose drive/user/share |
| nodb_setter positional/keyword arguments | `Ron.set_option -> {'token':'fixture-secret'}` | Keep controller/setter identity; replace argument value with `[redacted]` |
| project option maps | `POLARIS job options: {"password":"fixture-secret"}` and analogous RUSLE/other options | Fixed safe option-count/summary; never map values |
| batch/raw exceptions | `rq:fixture-job EXCEPTION ValueError: /private/input` plus traceback lines | Preserve job ID and EXCEPTION; fixed safe failure summary, no exception string/traceback |
| run-sync structured failure | EXCEPTION_JSON with error/message/stacktrace/path | Preserve marker, emit safe message/error summary, drop trace/path/detail and unknown fields |
| ag-fields structured failure | EXCEPTION_JSON with scheme/field_id/sub_field_id/filename/message | Preserve validated identifiers and safe basename; replace arbitrary exception message with safe summary; drop unknown detail/options |
| Lifecycle | `rq:fixture-job STARTED operation(example)` and ENQUEUED/STATUS/COMPLETED variants | Preserve tokens and job identity |
| run-sync completion | `rq:fixture-job COMPLETE run_sync_rq(example, cfg)` | Preserve parser-compatible run/config pair |
| Trigger | `rq:fixture-job TRIGGER wepp WEPP_RUN_TASK_COMPLETED` | Preserve final controller/event tokens |
| Conditioning diagnostics | DIAGNOSTICS_V1 base64url object with operation_id/method/elevation_unit/maximum_raise/maximum_cut/summary | Decode/validate bounded known fields; preserve finite numbers and safe text; reject extra path/credential fields without dropping final trigger |
| Command | Manifest/interchange progress and completion from project_rq publish_command sites | Preserve event/progress semantics; sanitize text as above |
| Ordinary NoDb/model progress | `Building soils: 50%` | Preserve useful text, including percent |
| Credential-shaped text | Bearer/JWT, password/token/key assignment with synthetic values | Replace credential; never log input during redaction errors |
| Preflight | Raw prep hash with timestamps, attrs, arbitrary options and locked fields | Emit only existing typed checklist, known boolean lock fields, optional integral timestamp |
| Preflight hostile lock key | `locked:/private/path` or unrecognized secret-like suffix | Omit field; do not change backing lock storage |
| Preflight log | Raw prep includes a synthetic secret option | No raw prep hash emitted at any configured logging level |

Malformed structured data produces a safe generic status summary, preserving
recognizable lifecycle/trigger tokens when valid. Do not expose parser errors.
Unknown ordinary progress is retained with targeted redaction; this contract
claims removal of confirmed paths/options/exceptions/credential classes, not
perfect detection of arbitrary secrets hidden in natural language.

## Acceptance

Implement focused tests at the shared producer/service boundary and the
consumer parsers. Retain source IDs and sanitized assertions, not raw runtime
messages. Existing job-info authorization remains responsible for detailed
failure inspection; F4 does not change that HTTP response contract. Forest
acceptance must prove both normal progress and completion behavior, not just
one successful handshake. Review the final transformation code independently.
