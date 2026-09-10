# DEVAL execution identity recurrence

Fix recurring Compose report permission failures for existing and future runs.
Execute [the active plan](prompts/active/execplan.md). The user explicitly requested
a durable production correction after the second permissions repair left legacy
projects broken. Current scope is conformance with the shared-filesystem render
obligation in `docs/schemas/weppcloudr-render-execution-contract.md`.

Precedent: `20260821_weppcloudr_execution_backend_refactor` repaired shared output
groups; `20260909_deval_soils_permissions` repaired future soils publication.
Neither covers worker-owned 0600 legacy inputs. Keep those fixes, correct execution
identity, and add direct deployment evidence. No data schema or report content
changes. Security delta is low: rendering uses the trusted worker's existing
identity rather than a request-selected identity. Independent correctness and
QA reviews accepted the code and both hosts' production evidence.

Baseline: wepp1 job `2ae73acb-08a7-4894-98c3-f22559cfc336`, September 10 04:03 UTC,
failed reading valid populated `/wc1/runs/al/aliquot-shoji/soils/soils.parquet`
with errno 13. Worker UID/GID=1002:130, renderer=1000:993 with supplementary 130.
File mode 0600. Manual 0644 recovered the job at 04:09:50 UTC; that is not acceptance.

Use recurrence-triggered observation and the plan's health/danger signals.
No scheduled chmod or retry mitigation is introduced. Source backup retirement
requires the queued production canary to pass. Independent code and QA review
artifacts are required before closure.
