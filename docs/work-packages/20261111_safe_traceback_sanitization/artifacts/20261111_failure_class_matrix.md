# F5 traceback source and sink failure matrix

**Status**: Initial scaffold; repository-wide inventory pending
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
