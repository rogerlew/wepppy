# Publication staleness receipt review

The postrepair repository suite stopped at
`tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`
after 7,230 passes and 189 skips. The publication was already explicitly stale;
its reviewed source-delta receipt still named the pre-repair Roads source.

The correction to `tests/roads/analysis_staleness_current.json` changes only the
current Roads source hash and appends the reviewed `tc_out.txt` isolation change.
The original stale status, notice, rationale, recorded source identities,
provenance, historical matrix, report and vendored report remain unchanged.
This follows the stale-evidence rule in
`docs/schemas/roads-validation-suite-contract.md` (publication provenance);
it does not refresh historical scientific results.

Independent reviewer `/root/mipa_contract_correctness` verified the old source
hash at `d0d0fb8c7`, `30c77fc10` and `56d16dc7c^`, and verified that commit
`56d16dc7c` changes the production file only by the diagnostic exclusion and
its comment. Both referenced isolation and fresh-context reviews were rehashed.
Review outcome: PASS; no freshness laundering. All three publication tests pass.

- Previous Roads SHA256: `5beb3be8d69728c90a0a4b910656cbec80776fe7533a0970b5c071b9e4124f6b`.
- Current Roads SHA256: `7aa5cd95f17b493e1f3543b607b2d67b717edced1fb8c574c5c516ebb2fa74df`.
- Corrected receipt SHA256: `8d2430dcbc0e2310fb3bf469445aa2c75f208561db4253e617090b4e10420a17`.

The reviewer accepted exact-node continuation after this metadata-only change,
provided the original failure and subsequent rerun remain visible. Combined
coverage must not be described as an uninterrupted full-suite pass.
