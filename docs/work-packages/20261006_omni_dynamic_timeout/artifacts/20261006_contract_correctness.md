# WRT-02 independent contract correctness review

Reviewer: independent Codex reviewer agent. Date: 2026-10-06.
Scope: preimplementation WRT-02 contract checkpoint. No implementation files
were reviewed or edited.

## Initial verdict

Hold with two medium findings and two low wording corrections.

1. The pre-enqueue guarantee did not prevent affected parent child-id metadata
   from being saved before malformed workload rejection, and contrast admission
   could occur after hillslope rerun.
2. The plan permitted captured queue-stub arguments in place of real RQ
   serialization.
3. The package understated the Omni default change as no parameterization/default
   change.
4. The checkpoint claimed outputs remained byte-for-byte unchanged even though
   longer execution may complete outputs that were previously partial or absent.

## Disposition

The contract, checkpoint and plan now require calculation before affected child
id allocation, parent metadata/save, Redis connection, enqueue, and contrast
hillslope rerun. Invalid-workload evidence must assert zero affected queue calls
and parent metadata/save mutation. Disposable real-Redis queued-and-fetched
scenario and contrast leaves plus `job_info` inspection and verified cleanup are
mandatory. The package and ADR now classify the change as a workflow-scope
default/parameterization application with unchanged numeric policy. Artifact
wording now preserves formats/scientific logic without claiming output byte
identity.

## Final verdict

Approved for standalone checkpoint commit and implementation. No blocking
findings remain. Residual whole-leaf overhead, aggregate worker occupancy, and
deployment/retry separation are explicitly retained. The reviewer confirmed
`git diff --check` passed and that no implementation/test files had been edited.
