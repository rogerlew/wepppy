# Implementation review: scheduling-only amendment

**Accepted. No implementation blocker to concurrent native diagnostic runs.**
This supersedes only the execution-order condition in the prior installed-release
and factorial implementation review. The full application suite remains a
mandatory release-handoff gate and is not counted as passed.

Compared the preserved declaration
`65e11c3ef78795e4faae29d7ac3951bc5c654b4f2f1f8e74574e8cce2d72d781`
with the amended declaration
`830cb7a8d49189ad0c2decc02e788ab55cce8fa2265c0f875cff29bf411c522c`.
Only `plan_sha256` and the explicit `scheduling_amendment` changed. All 928 tasks,
the executable identity, harness script, direct dependencies, and 70 effective
dependencies are identical. Public and execution declarations match bytewise.

The prior accepted plan hash was reproduced exactly by undoing only the opening
scheduling paragraph and removing the appended scheduling clarification. This
independently confirms there were no factor, input, analysis, or scientific
acceptance changes. The amended plan hash is
`408f20a61ad686ddea49e97281690cbfec46ed39d08af6dd8d820244d61eadeb`;
the unchanged harness hash is
`30340616218f23dc354e306e97a746dab3de79c67f0a11ecc6406fede66b6194`.

The previously verified installed-byte and actual selected-workflow gates support
this isolated native experiment. It uses separate study folders and cannot
establish release-handoff or parameter acceptance. Existing full-period,
physical, particle, control-regression, withheld-material, and human UI gates
remain intact. The complete input inventory was not rerun for this metadata-only
scheduling review; its prior verified evidence remains applicable.
