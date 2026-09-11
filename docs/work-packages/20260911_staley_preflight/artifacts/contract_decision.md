# Staley preflight completion

Starting revision: c145e73ce49193f06518401b356d8d705b061a89.

Operator authorization: “let's wire it into preflight. use 🌋 as the TaskEnum emoji”.
This authorizes the bounded Python/Go/browser task wiring and required contract
checkpoint, preserving prior unrelated work. Intended enhancement, not a model change.

Canonical delta: production_m1.md, section “Preflight completion task”. Shared
controller-contract.md, NoDb persistence/concurrency contract, and RQ response
contract remain unchanged. No queue edges, authentication, model parameters,
NoDb schema or generated model files change. Add one Redis task timestamp and
one boolean checklist key, preserving existing clients and the legacy debris task.

Implementation boundary: RedisPrep enum; PFDF production notification; Go
checklist; run-page anchor mapping; static preflight selector mapping. Existing
completed runs may be explicitly reconciled using verified current durable state
and their original completion time; no automatic model rerun or invented date.

State matrix: absent/empty has no marker; published current complete or partial
has marker; rejected first run has none; failed retry retains a still-valid prior
publication; accepted replacement dNBR or changed persisted rainfall selection
clears marker. Upstream timestamps invalidate the Go checklist. Malformed task
or dependency timestamps fail closed. Detailed artifact freshness remains the
authenticated state endpoint's responsibility, as for other preflight tasks.

Regression evidence: publication/partial/retry/replacement/absence Python cases;
Go task, upstream mutation, missing and malformed values, legacy independence;
browser mapping and live existing completed run after service rebuild. Full
Python suite remains on operator hold. No sensitive details enter the public
preflight payload. Review correctness and security independently before coding.

Review clarification: strict timestamp ties remain incomplete. Serialize the
projection read/write with a short run-scoped Redis lock; preserve best-effort
post-commit RedisError logging. No authenticated GET writes or implicit backfill.
