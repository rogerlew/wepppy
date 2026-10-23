# Independent management-reference contract review

Date: 2026-10-23. Reviewer: `accounting_contract_review`.
Production source and templates were inspected read only before implementation.

**Approved for the prerequisite repair checkpoint.** No unresolved high or medium
design finding remains. Approval binds the Roads specification SHA-256
`a25c39dd5b0c3ec43e93b74d2c9af265f99ddadd5ed9046663f3ef281d2618e2`
and management decision SHA-256
`e362a2c8ef0582e78b31f5fddf293260ef6912b158fbd0c7be38bde71f8dc196`.

The smallest coherent repair retains all three source plant definitions, their
count and original indices in both reduced-OFE builders. Keep original `iresd`
and yearly plant `itype`; continue selecting and reindexing initial-condition,
yearly and OFE assignments exactly as required by the chosen profile. Remove
the two-OFE plant-3-to-plant-2 remapping when plant definitions are no longer
pruned. No legacy template, residue coefficient or scientific value needs editing.

Evidence: `wepppy/wepp/management/managements.py:882` resolves `iresd` against
`SectionType.Plant`; line 1428 does the same for yearly `itype`. They are not OFE
indices. The no-traffic template's ROAD initial state uses `iresd=2`, so retaining
only plant 1 leaves an invalid reference. The two-OFE transform deletes plant 2
and currently changes that same residue reference to the former plant 3. The
draft specification correctly distinguishes plant definitions from selected
initial/yearly scenarios and supersedes its old explicit FOREST `itype=2` rule.

Scientific caveat: FILL and FOREST plant numeric records in current
`3inslopen.man` are identical. The two-OFE reference is semantically incorrect,
but an observable numerical change cannot be claimed merely from its correction.
Preserving source definitions avoids a new choice between residue parameter sets.
The one-OFE no-traffic failure is the concrete execution defect motivating repair.

Before acceptance, verify both traffic templates through the one- and two-OFE
builders: exact retained plant blocks/count, original plant references, valid
selected initial/yearly assignments, and expected OFE order. Update the existing
tests that incorrectly require plant pruning. Run actual native cases including
no traffic, complete calendar/finite-output checks, and bounded comparisons of
previously executable high/low-traffic outputs. Confirm the three-/four-OFE paths
and full-project generated inputs preserve their existing semantics. A parser-
only or string-marker-only regression does not prove WEPP execution succeeds.

Compatibility is explicit regeneration through prepare/run; do not rewrite old
project artifacts. The validation report must identify the repaired builder and
rerun fresh cases. This review approves reference integrity, not a broader
parameterization change or a claim of field accuracy.
