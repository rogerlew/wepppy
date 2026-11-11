# F5 traceback source and sink failure matrix

**Status**: M0 inventory expanded; implementation/evidence pending
**Date**: 2026-11-11 UTC

The broken shared assumption is that a formatted traceback is safe to copy into
multiple destinations. Sanitization must occur before the first destination.

| Producer/consumer | Current risk | Required repair/evidence |
| --- | --- | --- |
| Flask `error_factory`/`exception_factory` | raw message/stack in log, API and run file | central rendering; direct response/log/file canary readback |
| Upload factories | raw logged exception; structured response | safe formatter/message; response compatibility |
| rq-engine response helpers/callers | raw `format_exc` in API/log | central renderer; call-site matrix |
| Query-engine global handlers | raw stack in API/log | central renderer; API/log assertions |
| Query validation/not-found handlers | raw exception text/trace fields | same representation; current status/schema retained |
| Query `exceptions.log` | raw persisted trace | sanitize before append; file readback |
| Browse/download handlers | `exc_info` plus run logs | formatter/adapter and direct file/log tests |
| RQ `handle_exception` | raw superclass persistence and meta copy | sanitize before superclass/save; Redis readback |
| RQ `handle_job_failure` | raw `exc_string` for uncontrolled failures | sanitize once before persistence |
| RQ task exception decorator | logger plus `exceptions.log` | central formatter and safe file writer |
| WEPPcloudR control plane | reconciliation `logger.exception`, FastAPI/Uvicorn errors and Kubernetes client failures | process-owned Redis/control-token/private-key/service-account sources; final handler readback |
| Python dependency `logger.exception` | formatter may render raw exception | install safe formatter on every production handler |
| Process bootstrap/uncaught exception | raw interpreter or framework traceback can bypass configured handlers | inventory entry points; sanitize or prove bounded safe termination output |
| Kubernetes container stdout/stderr | pod logs retain formatter and uncaught output | production-equivalent container capture with synthetic mounted canaries |
| Status/error publications | trace may be forwarded | sanitize producer before publish; retained message test |
| Frontend stacktrace panels | compatibility consumer | same fields/content structure, canary absent |

## Secret Corpus

Use synthetic raw, percent-encoded and JSON-escaped file/env values; a
comma-delimited authorization key ring with distinct constituent canaries;
Redis-like and database URLs; Authorization and cookie fields; ordinary and
Kubernetes service-account bearer/JWT forms; PEM private-key blocks and bounded
body forms; sensitive assignments; exception notes; cause/context chains;
ExceptionGroups; replaced mounted files; and sanitizer/source failures. Never
use or retain a real secret.

## Kubernetes Source Classification

Use the process-owned matrix in
`20261111_kubernetes_secret_handling_review.md`. Tests must distinguish locally
consumed sources from downstream-only or stale environment paths. A missing
local required source fails closed; a path not owned by the selected process
profile is never opened and cannot suppress its traceback.

## Completion Rule

Re-run inventory for all traceback formatting, `exc_info`, `exc_string`,
stacktrace response fields and exception-file writes. Each confirmed sink needs
direct final-output readback. A helper unit test or full-suite pass cannot close
an untested sink. Kubernetes compatibility additionally requires synthetic
production-path/mode container evidence; live deployment remains separate.

## M0 discovery and dispositions

Retained search: `20261111_traceback_inventory.txt` (1,715 occurrence lines in
wepppy/services); explicit source search: `20261111_secret_source_inventory.txt`.
Search occurrences are discovery evidence, not a closure claim. The following
additional confirmed peers must receive direct acceptance before closure.

| Peer | Disposition |
| --- | --- |
| NoDb QueueHandler/base.py | Sanitize before prepare drops exc_info; test final file/console/status output |
| NoDb StatusMessengerHandler | Bypasses format; sanitize exceptional publication explicitly |
| NoDb batch_runner, rq/migrations_rq, security WatchedFileHandler | Safe formatter on dynamically created handlers |
| PFDF observability/source_acquisition | Direct exceptions.log/print_exc and failure JSON containing str(exc)[:2048]; sanitize before truncation/write/print |
| tools/migrations migrate_* print_exc | Invoked by RQ; sanitize direct stderr as well as migration result errors |
| rq/job_info fetch/detail exceptions | Sanitize exception-derived exc_info responses |
| rq/ag_fields_rq _publish_failure | Sanitize arbitrary exception text before status publication |
| rq/culvert_rq, batch_rq, omni_rq | Sanitize error payload before persistence/publication |
| rq/path_ce_rq set_status | Sanitize failure message before controller persistence |
| rq/run_sync_rq | Sanitize failure artifact and returned exception lines |
| elevationquery exception message helper | Sanitize existing API fields; preserve status/schema |
| browse/flow CSV/TSV preview | Use safe shared exception message helper |
| shape_converter parser subprocess | Structural sanitation on stderr; empty source profile excludes stale Redis path |
| weppcloud startup preflights | Cover print/re-raise before app logging, or retained evidence of no loaded secret |
| rq-worker-startup probe | Sanitize last_error/print(exc) and uncaught probe output |
| RQ failure callbacks/webhooks | Preserve original in-process exception semantics; audit every output boundary |
| WEPPcloudR command stdout/stderr artifacts | Disposition exceptional output before retained diagnostic write |
| Standalone developer benchmarks/examples | Not production entry points; document exclusions after invocation audit |
| Go status/preflight and Node CAP | Outside Python renderer; existing contracts remain authoritative |

Source-profile corrections include mail/OAuth aliases, model service APIs, both
JWT singular and compound settings, legacy Redis URL credential constituents,
and lazy web-app imports from browse/query authorization. Do not allow an
imported app to overwrite the owning process's logging profile. Retain current
file framing and source precedence. Historical retired-secret values cannot be
recovered by current-file snapshots; this is an explicit contract limit.


### Source ownership review disposition

The canonical source matrix supersedes the initial Kubernetes-only table.
`configuration.py:291-295` also consumes credential-bearing
`SQLALCHEMY_DATABASE_URI`/`DATABASE_URL`. Full Flask initialization includes
Redis, database, Flask key/salt, agent key and mail/OAuth. It is reachable from
rq-engine, browse, download, query, D-Tale and default/batch workers through
`helpers.py:get_run_owners_lazy/get_user_models`, query HTTP authorization,
D-Tale private-scope checks, run-sync and project deletion. Include that full
metadata set, without importing Flask into the renderer. Keep web's downstream
render token excluded; shape converter remains an empty source profile.

Correctness review additionally identified fork/archive project-commit startup
as a database consumer in postgres mode (`initialize_project_commits` ->
`run_catalog.adapter`). Select that metadata from the existing explicit mode.
D-Tale consumes verified claims rather than decoding JWTs; its profile excludes
the authorization key ring while retaining Flask-init and D-Tale sources.
