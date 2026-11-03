# MIPA-02 supplementary test-isolation QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. **PASS for the bounded fixture repair.**
Reviewed `tests/test_managements_module.py` and the retained reproduction logs
under `/wc1/holdouts/mipa-native-r6-20261102`. No production change is involved.

The old fixture replaced the canonical management module in `sys.modules`, then
removed that entry during teardown. Already imported consumers retained the old
classes while later imports created distinct `SectionType` and reference-class
identities. In the failing alias test, the enum comparison skipped reference
renaming; serialization then rejected the stale `Corn` reference before reaching
`pmetpara_prep`. This is an import-isolation failure in the test setup.

The replacement uses `importlib.import_module` and preserves the canonical
module identity. Removing the package stubs, custom loader, and destructive
teardown reduces complexity without changing test assertions or coverage.
The repository's canonical container supplies the normal import dependencies.

| Retained evidence | Result |
| --- | --- |
| `alias-target-before.log` | Identity module alone: 28 passed. |
| `alias-order-before.log` | Management tests followed by identity tests: 1 failed, 33 passed before stopping. |
| `alias-order-after.log` | Same ordered selection after fixture repair: 43 passed. |
| `alias-order-qa.log` | Independent QA rerun of that order: 43 passed in 10.11 seconds. |

Independent command:

```sh
wctl run-pytest tests/test_managements_module.py tests/wepp/management/test_mofe_input_identity.py --maxfail=1
```

`wctl check-test-stubs` also passes. The reviewed fixture file has SHA256
`44e11deba8d0c1ac571095401660b3a9974a91485013b7f4bc2ec826c1b6e05e`.
The before, after, and independent ordered-run log hashes are respectively:

```text
72ae9a7f9205d2813f9a818755d4fb60f8112c19b2655a4dcb33b8e37d0d8ec1
0199fe8d3313cc71eff95dc5664636086c6c8bc6aa322aeae054ead5ddf6de50
27ee949b5f2808455cb209135da4aff0e9da24b32b6f0d907cf90fbae20e92f7
```

The retained broad run `wepppy-pytest-v1.log` stopped at this failure after
9,899 passed and 422 skipped. A separate continuation is in progress at this
review. These targeted passes do not establish an uninterrupted green broad
suite or prove that every possible test order is isolated. No blocking finding
remains for this fixture change; broader validation remains separately tracked.
The frozen PDF and hash-bound full-context QA artifact are unchanged.
