# Independent OSR-01 / UFS-01 contract correctness review

Reviewer: independent `reviewer` agent `/root/contract_correctness`  
Date: 2026-11-16 UTC  
Disposition: accepted after revision; both medium findings below are closed.
Post-fix read-only confirmation: 2026-11-16 19:14 UTC.

## Reviewed scope

Read the checkpoint decision, shared staging contract, Omni SBS control contract,
and amended freshness/upload contracts against current Omni UI, run admission,
scenario naming, input parser, freshness guards, and NoDb mutation behavior.
This is a contract review, not implementation or runtime acceptance. No production
files were edited and no application tests were run.

## Findings

### C-01 — Medium: child recovery association needs a basename-collision rule

`docs/ui-docs/contracts/omni-sbs-control-contract.md`, “Saved association and
two-location resolution”, selects the exact saved path but derives the child
through the existing scenario-name function. In
`wepppy/nodb/mods/omni/omni.py::_scenario_name_from_scenario_definition`, SBS names
encode only the basename, not the saved staging path. Two saved definitions at
`_limbo/00/map.tif` and `_limbo/01/map.tif` therefore resolve to the same child
`disturbed/map.tif`. The UI permits multiple SBS rows, and the input parser does
not reject this pair. Unique new staging directories do not disambiguate children.

A new child-recovery path could silently restore the wrong raster when the
requested definition's staged file has been consumed. The contract's general
“ambiguous saved associations” wording does not define this concrete collision.
Add an explicit collision rule for child recovery and retain a scoped regression
with two different saved paths sharing one basename. A bounded rejection of
ambiguous recovery avoids changing public scenario names or introducing IDs;
do not redesign the existing naming scheme under this package.

### C-02 — Medium: distinguish input acceptance from enqueue response failure

`docs/ui-docs/contracts/omni-sbs-control-contract.md`, “UI and transport”, says
failure leaves the accepted association intact. “Failures, compatibility, and
cleanup” likewise broadly promises old definitions on failed replacements.
However, `wepppy/microservices/rq_engine/omni_routes.py::_run_omni` commits
`omni.parse_scenarios(...)` before submitting the job. `RqSubmissionConflict`
then returns 409, and other enqueue errors return 500; a response can fail after
the replacement has already become accepted state. Network loss can do the same.

Define the preservation guarantee at the input-validation/state-commit boundary.
For postcommit or uncertain submission errors, the normal saved-state reader must
reconcile the displayed current map without claiming rollback or clearing the
original submission error. Add a scoped persist-success/enqueue-failure case.
Do not expand this repair into a queue/state transaction redesign merely to meet
an overly broad UI promise.

## Strengths and residual risks

The two-location rule, unchanged public keys, isolated replacements, contained
fork/restore resolution, and explicit separation of input availability from
output freshness are coherent and fit the user-approved scope. Shared staging
adoption is bounded to Omni; no legacy receipt migration is required.

Real acceptance still needs a native-produced child map, not only a pristine
raster fixture: current raster validation rejects adjacent companions and the
freshness contract explicitly leaves native companion behavior limited. Verify
that a normal successful child supplies the recoverable file intended here.
Also exercise saved-definition drift under the actual commit lock; the existing
validator currently checks reused byte identities but not saved association drift.
These are required implementation evidence, not additional design findings.

No conclusion about browser presentation, generated raster/model correctness,
or production readiness is supported by this read-only review.

## Post-fix disposition

**C-01 closed:** The revised “Saved association and two-location resolution”
section explicitly rejects recovery when distinct saved references map to one
child, including equal basenames. Exact staged selection remains supported.
The checkpoint state matrix includes this case. Public names remain unchanged.

**C-02 closed:** “UI and transport” now separates validation/precommit failure
from enqueue failure or timeout after commit. It requires normal-reader
reconciliation while preserving the original submission error/status. The
remaining replacement-preservation sentence is limited to validation/precommit
failures, and the checkpoint matrix includes enqueue error/timeout after commit.

The amended contracts are implementable within the bounded scope. No unresolved
medium/high correctness finding remains at the contract stage. The residual
runtime/native-copy and commit-boundary evidence requirements above remain
implementation acceptance obligations.
