# Roads evidence refresh

The async catalog source changes invalidated the existing Roads publication
provenance. Regeneration uses the canonical workflow in
[the Roads README](../../../../tests/roads/README.md) and
[validation contract](../../../schemas/roads-validation-suite-contract.md).
No Roads runtime, fixture, scientific interpretation, or model parameter was
changed for this refresh.

## Executed evidence

- Fresh matrix: **516 passed**, 2 dependency deprecation warnings, 378.91 seconds.
  Raw inputs, outputs, and analysis remain in the development container at
  `/tmp/roads-qcat-async-20261023/roads_matrix0`.
- Canonical native analyzer: **516 complete profile summaries validated**.
  Every full case payload exactly matches the prior published result.
- Four fresh project clones completed with 34 bare-ditch, 34 rocked-ditch,
  34 rutted, and 1 unrutted profiles. Each passed independent daily area/water
  reconciliation across 5,844 days and preserved 2,383 source files and 911
  copied baseline files. The three additive designs retain all 55 source
  features; the positive unrutted control retains the reviewed 54-feature subset.
- The retained full-upload unrutted negative control was reverified: exactly
  Topaz 271/272 fail with `failed_non_positive_top_ofe`, no current receipt,
  unchanged original source and copied baseline. This negative control was
  rechecked, not re-executed.
- Fast Roads fixture/failure contracts: **11 passed**, 2 dependency warnings.

[The retained comparison](roads_evidence_comparison.json) records exact case
equality, project field comparisons, source and native identities, and negative
control evidence. The source differences are `_roads_lifecycle.py`,
`hill_interchange.py`, and `watershed_interchange.py`. The current native extension
SHA-256 is `7908a4fa667b149f4eee5a827dfb65c39c0c080369459b659c68cec26f411811`.
The prior native SHA-256 was
`4ae01a243bebb596e6bf719626804a04e8ebdced7d9134e170f2af2a1bd31b6e`.

## Exact generation commands

Commands ran through the development `wctl` preset. Each destination was fresh;
the project runner rejects an existing destination and verifies source/baseline
hashes after execution.

```bash
wctl run-pytest tests/roads/test_roads_matrix.py --basetemp=/tmp/roads-qcat-async-20261023 -q
wctl exec weppcloud python -m tests.roads.roads_analysis /tmp/roads-qcat-async-20261023/roads_matrix0
wctl run-pytest tests/roads/test_roads_contracts.py -q
wctl exec weppcloud python -m tests.roads.roads_project /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-qcat-async-20261023-bd inslope_bd
wctl exec weppcloud python -m tests.roads.roads_project /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-qcat-async-20261023-rd inslope_rd
wctl exec weppcloud python -m tests.roads.roads_project /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-qcat-async-20261023-rutted outslope_rutted
wctl exec weppcloud python -m tests.roads.roads_project /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-qcat-async-20261023-unrutted outslope_unrutted --exclude-infeasible-unrutted
wctl exec weppcloud python -m tests.roads.roads_project /wc1/runs/cl/clogging-starch /wc1/runs/ro/roads-validation-oct23-v2-unrutted outslope_unrutted --verify-negative
wctl exec weppcloud python -m tests.roads.roads_report /tmp/roads-qcat-async-20261023/roads_matrix0 /wc1/runs/ro/roads-qcat-async-20261023-bd /wc1/runs/ro/roads-qcat-async-20261023-rd /wc1/runs/ro/roads-qcat-async-20261023-rutted /wc1/runs/ro/roads-qcat-async-20261023-unrutted --unrutted-negative /wc1/runs/ro/roads-validation-oct23-v2-unrutted
wctl run-pytest tests/roads/test_roads_publication.py -q
```

Scoped vendor synchronization used the existing API, with no generated-index
write or unrelated vendor synchronization:

```bash
wctl exec weppcloud python - <<'PY'
from dataclasses import replace
from pathlib import Path
from wepppy.weppcloud.usersum_docs.docs_contracts import load_and_validate_contracts
from wepppy.weppcloud.usersum_docs.vendor_sync import sync_vendor_docs
repo = Path('/workdir/wepppy')
contracts = load_and_validate_contracts(
    base_dir=repo / 'wepppy/weppcloud/routes/usersum', repo_root=repo,
    require_local_files=True, require_vendor_files=False)
scoped = replace(contracts, vendors={'wepppy-roads': contracts.vendors['wepppy-roads']})
print(sync_vendor_docs(scoped, repo_root=repo, write=True, clean=False))
PY
```

Host logs: `/tmp/roads-qcat-async-matrix.log`,
`/tmp/roads-qcat-analysis.log`, `/tmp/roads-qcat-contracts.log`, and
`/tmp/roads-qcat-negative.log`. Full project stdout is retained inside the
development container as `/tmp/roads-qcat-async-{bd,rd,rutted,unrutted}.log`.
Publisher and publication-test logs are `/tmp/roads-qcat-publication.log` and
`/tmp/roads-qcat-publication-tests.log` on the host.

## Publication and limits

Independent scientific review approved publication; see
[the retained independent review](roads_independent_numeric_review.json).
It independently rechecked all raw case hashes, complete PASS/WAT calendars,
all 80 project Parquet tables, daily reconciliation, preserved inventories,
and the negative control. Canonical publication completed at
`2026-10-23T21:57:58.480826+00:00`; scoped vendor synchronization completed.
The final published 516-case payload remains exactly equal to the prior payload;
the report body changes only its generated timestamp. Publication tests passed:
**3 passed**, 2 dependency warnings, 8.86 seconds. Documentation lint passed for
this artifact and the canonical report (0 errors/warnings); the vendor path is
excluded by the lint tool, and publication tests prove its byte equality.
Scoped `git diff --check` passed. The parent agent owns the final full-suite gate.
The existing `analysis_context.md` interpretation is retained because all
measured case and project scientific values match the prior evidence exactly.
Full project Parquet bytes can differ while their Arrow values and schemas
match; summary provenance metadata binds the regenerated source artifacts.

This is model verification and sensitivity evidence, not field calibration or
production deployment evidence. The source site, parent Mill Creek validation
clone, and production hosts were not mutated. The preexisting dirty Usersum
`generated/docs_index.json` is outside this task and remains untouched.
