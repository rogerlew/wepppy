# M3 Run prepares missing sources


## Purpose


Make the ordinary Run M3 button produce probabilities for a fresh eligible basin,
without an operator manually preparing soil inputs. This is faithful wiring of
the existing bounded reader, not a surrogate scientific pipeline. Completion
requires generated outputs from the real worker and native binary on
/wc1/runs/ov/overpriced-sprawl, not only mocked tests.


## Progress


- [x] Diagnosed attempt 5cd64c185a9843abaac662ec4b90f637: absent source pointer,
  zero valid cells and zero probabilities; rainfall and terrain available.
- [ ] Ratify canonical Run-preparation amendment with two independent reviews
  and standalone ancestor commit.
- [ ] Implement bounded acquisition/activation with attempt-safe snapshot rebasing.
- [ ] Add unit and real-boundary regressions and run canonical tests.
- [ ] Rerun normal browser/RQ workflow; verify probabilities and protected hashes.
- [ ] Complete security review, docs, evidence and closeout.


## Context and plan


production.execute_m3 currently consumes soil_inputs.prepared_sources but never
calls source_acquisition.acquire_sources. Add a small run_preparation helper
after initial attempt/prerequisite validation. Only absent metadata triggers
delivery. Use production_soils.activate_sources with a caller authority callback
inside its existing locked promotion. Keep network outside locks. Rebase only
the attempt-owned prepared inventory, pin candidate hash and reject concurrent
changes to all other inputs. Existing pointers, including empty schema-v1, are
not refreshed. Read the canonical production_m3_runtime.md amendment and contract
decision for normative details and complete runtime-state matrix.

Tests use tests/nodb/mods/test_postfire_debris_flow_runtime_m3.py real owner,
native terrain and activation fixtures; mock only remote acquisition. Add unit
tests for inventory normalization and malformed state. Preserve previously
accepted results on failures. Use wctl run-pytest for targeted modules and
wctl run-pytest tests --maxfail=1, plus docs lint and changed exception checks.

Before live work hash soils/RUSLE/wepp/runs via the existing closed-package
audit_protected_inputs.py (read/run unchanged). Reload only idle development
workers if necessary. Execute its live_browser.cjs against
https://wc.bearhive.duckdns.org, overpriced-sprawl, config, M3, with a fresh
module-owned validation directory. Do not pre-acquire sources. Verify actual
event/design probabilities with verify_live_results.py and inspect receipt
provenance and current public state. Preserve all failed/intermediate artifacts.


## Validation and acceptance


Absent-pointer tests must fail before the fix and pass afterward, retaining
actual source activation and NoDb writes. Tests cover different basins/keys,
present-empty/populated reuse, acquisition failure, malformed pointer, replaced
attempt, source/WAL drift and pointer substitution. The real basin must finish
with available probabilities, verified mask and unchanged protected inputs.
No production rollout, soil rebuild, shared cache mutation or formula change.


## Idempotence and recovery


Each acquisition keeps fresh receipt/transcript directories. Retry reuses a
valid promoted pointer. A superseded or failed attempt never replaces accepted
results; valid sources can remain for the next explicit Run. Do not delete old
outputs or roll back pointers over concurrent work.


## Surprises & Discoveries


Prior acceptance used manually prepared sources; it did not prove the first-use
Run workflow. The real basin's 27,450 event rows were all unavailable.
The first protected-input audit detected a changing wepp/runs/tc_out.txt;
existing job 4d845387-25f3-4365-b71e-4e72657a8ffe is performing watershed
interchange on this basin. Leave it running and retake the baseline when idle.


## Decision Log


2026-09-15: Treat Run as authorization for bounded missing-source acquisition,
not state refresh. Preserve present-empty semantics and existing acquisition
budgets. No scientific parameter change or new service is needed.


## Outcomes & Retrospective


Pending implementation and live validation.
