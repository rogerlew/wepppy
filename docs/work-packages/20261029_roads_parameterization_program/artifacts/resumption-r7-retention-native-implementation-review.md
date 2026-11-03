# Paired retention native runner: independent implementation review

Date: 2026-11-03 UTC. Reviewer: `mipa_contract_scope`.
Scope: code, retained contracts and installed import/dependency inspection.
No declaration, preparation, native call or runner edit was performed by this
reviewer. Only this additive review artifact was written.

## Verdict

**Implementation review passes after the findings below were corrected.**
The runner implements the selected eight ordinary histories plus eight exact
observer replicas without altering the frozen ordinary auditors. Successful,
independently reviewed preparation and the concrete native declaration review
remain required before launch. This verdict is not execution or outcome approval.

Reviewed [runner](run_r7_retention_native.py) SHA256:
`6c427d5fbc1ff65060a78ce678b11446bc8652c7e34ebf176f43ce37a55ac76f`.
Reviewed [protocol](resumption-r7-retention-native-protocol.md) SHA256:
`241d62afef0e06e0cabb4f6229768ee2d699248fe99f78eb37fa2c88a0db543e`.
Reviewed [observation design](resumption-r7-retention-native-observation-review.md)
SHA256: `8f0edcc2d1b95e5b40effa51272a67d300977d3e1b405df71a868ce8bb8848a4`.

## Findings and closure

1. **Preparation-to-native source binding.** The draft reselected tasks from the
   seed declaration without verifying that it still matched the preparation
   declaration, and read the current r7 comparison record without retaining its
   identity. The revised declaration verifies preparation `input_files`, exact
   selected case/folder/input/auxiliary identities, and the original source
   record chain. It binds the actual r7 record and seven comparison output files
   into `reference_files`, checked before and after the campaign. The task label
   explicitly distinguishes that frozen r7 comparison from fresh default.
2. **Exception-path evidence preservation.** The draft archived a trial only if
   its native/auditor function returned normally. An assertion or parsing failure
   after execution could leave evidence only in local scratch. The revised
   `execute_retained` boundary records the exception and inventories/copies the
   partial case into durable `failures/` before re-raising. Preservation does
   not require failed companion validation to pass. Returned native/audit/parity
   failures also receive a root failure record and stop remaining calls.
3. **Actual companion-validator dependency.** Installed inspection showed that
   the original dependency traversal omitted `wepppy/soils/ssurgo/retention.py`.
   It is now explicitly bound. Readback of the installed dependency function
   confirms 83 entries including validator SHA256
   `9ac690110248b9982550eb1c887d452db8436b78e38c8037799c1fe12809d670`.
4. **Checks at each trial boundary.** The initial all-task inventory scan alone
   could precede many other calls. Each trial now verifies its entire staged
   inventory and recursively validates policy before invocation, then rechecks
   every staged file digest and policy after native/auditor work and before
   archiving. These checks are inside the retained-failure boundary.

The reviewer sent findings without editing the runner; the author implemented
the corrections and this review read them back.

## Accepted implementation boundaries

- Exact B2/B3/B4/B5 identities and both policies are inherited from the reviewed
  preparation. Fresh default and optional receive identical non-soil inputs.
  Entire case roots preserve relative source/treatment/stack/stage parents in
  service-local scratch and in the durable archive. Companions remain explicit
  workspace provenance inputs, not additional native scientific fields.
- Each ordinary/observer pair differs only by the empty existing observation
  marker. The frost filter is absent. The exact watershed r7 executable runs in
  hillslope mode, sequentially, with the existing 300-second timeout and no
  automatic retries.
- Ordinary runs use unchanged `seeds.execute` physical, full-calendar,
  completeness and strict particle auditing. The inherited working-directory
  validator derives allowed files from bound inputs, so the optional companion
  is admitted without modifying the validator. Observer runs use seven-output
  byte parity to the corresponding audited ordinary run instead of overriding
  the strict runtime audit to accept observer files.
- The declaration binds dependencies, preparation/reference artifacts, scratch
  inventories and UID/GID. Driver/protocol snapshots are retained. The campaign
  requires a separate reviewed declaration receipt and an exclusive start gate.
  Archive receipts distinguish actual execution paths from retained paths;
  original scratch is preserved and no production-mount parity is claimed.
- The runner's success ends at execution/audit/parity completion. It does not
  claim a parsed initialization inventory, observed stored HK, dynamic PERC
  operands, unique drainage/ET causality, whole-system closure or accepted
  parameterization. Those limits agree with the observation design.

## Remaining gates

The concrete preparation must pass paired invariants and fixed geometry,
including 1600 mm for each B2/B3 role. Its independently reviewed source-vintage
or builder drift must remain visible in subsequent comparisons.

After execution, independent readback must still validate the full initialization
inventory, native OFE/layer mapping, original rounded FC/UL/ratio tokens, guard
events and all eight parity pairs. A nonempty trace alone is not that scientific
gate. The outcome review must assess target response and passing/opposite-control
harm under unchanged criteria before any wider development study. No withheld
evaluation, default adoption, UI implementation or deployment follows.

Validation here comprised static code/readback, successful AST parsing and
ordinary installed imports with bytecode writing disabled to inspect dependency
bindings. The author also ran two focused offline tests via
`wctl run-pytest tests/tools/test_roads_retention_native.py`: both passed in
9.13 seconds, with two existing dependency deprecation warnings. This reviewer
read the tests and retained execution log at `/tmp/roads-retention-native-tests.log`.
The tests prove that changed staged bytes stop before invocation and that a
post-native auditor exception retains partial stdout/input plus the failure
receipt. Test-file SHA256:
`38328fc2f5624e197f698fbb53c7f83571a5ec0dd99739f909ad59127a8549c0`.
They use controlled stand-ins, not a native campaign. Actual execution and
scientific artifact gates remain outstanding.
