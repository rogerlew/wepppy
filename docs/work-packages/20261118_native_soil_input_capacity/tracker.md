# Native soil input capacity tracker

Status: evaluation complete, 2026-11-19 UTC.

## Progress

Native prototype committed as `fd7e0a5a6526ae217a58eb5bb2c491d75273610d`.
40 reader tests, 80 exact state comparisons, complete three-year hillslope and
sixteen-year three-OFE cases pass. Both binary smokes, provenance checks, and
all 31 watchlist cases pass. Full native pytest: 1785 passed. Twelve complete
two-year portable watershed runs pass daily/hourly coverage; original inputs
match bytewise. The larger incomplete fixture supplies 301-hillslope parity only.

## Decisions

Use fetched native default-branch source; keep `mxnsl=10` and production Python
limit unchanged. Evaluate separate `mxhzin=11`, based on the observed run-cache
maximum ten plus the mandatory 200 mm split. No deployment or vendoring.

## Validation and evidence

See [evaluation](artifacts/evaluation.md), [correctness review](artifacts/correctness-review.md),
and [build identities](artifacts/build-manifest.json). Reports retain native state,
artifact hashes, source patch, actual Zepol soil text and numerical limitations.
