# MRS-01 tracker

Timezone: UTC. Started: 2026-10-30. Last updated: 2026-10-30 23:38 UTC.
Phase: checkpoint accepted; awaiting commit authority. Security impact: high.
Active plan: [repair_execplan.md](prompts/active/repair_execplan.md).
Starting revision: `e35d7a3e69497ddfd9709736af50107f56963584`.
Checkpoint ancestor: **none; commit authority not yet granted**.

## Task board

- [x] Record initial status; preserve unrelated Roads/research changes.
- [x] Reproduce shared parser fallback through real HTTP safely.
- [x] Independent source audits and consumer/state matrix.
- [x] Draft canonical amendments, checkpoint and execution plan.
- [x] Two independent exact-draft contract reviews; all medium/high findings closed.
- [x] Lint changed docs and prepare precise commit allowlist.
- [ ] Obtain authority and commit accepted checkpoint as ancestor.
- [ ] Repair all confirmed consumers and complete traced runtime coverage.
- [ ] Focused/broad/static gates and final correctness/QA/security reviews.

## Decisions and progress

2026-10-30: retained source baseline, executed read-only HTTP parser probe in the
running development weppcloud container via wctl. Both frameworks silently accept
malformed JSON as defaults and arbitrary numeric clean flags as true. No real
business route/project/queue was invoked by the probe.

2026-10-30: independent reviewers identified additional direct parsers, webhook-only
body guards, early state/source mutations and null/list compatibility exceptions.
[Consumer matrix](artifacts/consumer-matrix.md) distinguishes confirmed defects
from unresolved candidates; no static candidate is labeled verified unaffected.

2026-10-30: chose bounded shared validation plus adapters and explicit error
translation, preserving default/form/list/null behavior. Exact rationale lives in
[canonical contract](../../schemas/request-payload-contract.md) and
[decision](artifacts/20261030_contract_decision.md). No production edits before the
contract-first ancestor exists. No new infrastructure or parameterization.

## Blockers and risks

Implementation is blocked by the required reviewed ancestor checkpoint and absent
commit authority. The operator prompt expressly does not grant it. Prepare the
accepted checkpoint first, then request authority for that exact standalone commit.
Do not stage unrelated edits in PROJECT_TRACKER or other files.

Runtime coverage remains pending across direct/indirect consumers. New validation
must not be swallowed by local catches, reject legitimate lists/null clears, alter
callback digests, or consume bounded upload streams twice. Final review must verify
checkpoint ancestry and valid-state noninterference, not only error containment.

## Verification and signal log

Baseline command: `wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20261030_malformed_request_side_effects/artifacts/reproduce_parsers.py` — passed as diagnostic;
10 cases × 2 actual framework HTTP paths, retained in `parser-baseline.jsonl`.
Observed defect, not repair evidence. Source index: 429 function records.
Implementation tests/full suite: not run; implementation has not started.
No deployment, production jobs or destructive reproduction. No temporary calluses.
Post-change signal snapshot and production observation remain pending separately.

2026-10-30 23:38 UTC: both independent reviewers approved checkpoint after clipping
contract reconciliation. All eight canonical documents, package docs and root
tracker lint pass with zero warnings/errors; git diff --check passes. Spelling
preview retains only unrelated preexisting CSRF wording. Commit file scope is
[checkpoint manifest](artifacts/checkpoint-manifest.md). No implementation/test
suite has run; the production defect remains unfixed pending commit authority.
