# Reproduce the compact whole-hillslope response report

The complete native execution evidence is private and retained separately.
This source-free command only reads the restored accepted dataset and the
independent full readback; it does not run or rebuild WEPP. Use the repository
virtual environment with the bound dependencies. The exact inputs and source
identities are recorded in `summary.json`, `readback-receipt.json` and the
independent full readback.

From the WEPPpy root, choose a new destination. Existing destinations fail
before any output file is written:

```bash
(
  set -e
  packet=docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-hillslope-response-r4
  study=out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2
  replay=out/roads-parameterization-program-20261031/buffer-roughness-hillslope-interpretation-r4/publication-replay
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B "$packet/summarize_response.py" \
    --root "$study" \
    --independent docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-hillslope-response-r4-u2-independent-full-readback.json \
    --out "$replay"
)
```

The annual table and all numerical summary values must reproduce exactly.
The script's recorded path binding changes when executing the exact script copy
from the public packet instead of its original private analysis directory;
compare the numerical payload separately from this explicit location binding.
All original input hashes must still match. Preserve every replay and failure.

For derived Parquet revalidation, use fresh copies as specified by the
[verifier amendment](../buffer-roughness-hillslope-response-r4-verifier-amendment.md).
Compare exact table/schema/metadata values and separately verify the retained
artifact hashes. The canonical conversion audit rewrites its output Parquets;
do not run it against an immutable accepted case merely to check it.
