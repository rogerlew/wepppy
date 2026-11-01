# Reproduce the physical-capacity review

Use the repository root and fresh output directories. These original readers
consume retained artifacts; they do not rebuild or run WEPP, fetch new soil
values, or write accepted evidence. The prior storage-ownership packet and
private accepted u2 histories must be restored with their recorded hashes.

```bash
python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-capacity-physical-review-r4/read_capacity.py \
  --source docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4 \
  --out out/roads-parameterization-program-20261031/physical-capacity-replay-new

python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-capacity-physical-review-r4/read_infiltration.py \
  --accepted out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2 \
  --packet docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4 \
  --out out/roads-parameterization-program-20261031/infiltration-capacity-replay-new

python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-capacity-physical-review-r4/audit_rfg_basis.py \
  --repo . \
  --out out/roads-parameterization-program-20261031/rfg-basis-replay-new
```

Expect five capacity CSVs (586 initialization layers, 556 consumed rows, 152
connected calls, 36 target rows and six owner/role summary rows), one 216-row
INFPAR CSV and one 108-row emitted-RFG CSV. All seven tables must reproduce
byte-for-byte. Receipts separately bind invoked reader identity and input paths.
Existing destinations fail before output writes.

Capacity checks preserve native rounding residuals and classify raw versus
rounding-separated excess. The 1e-15 m explanatory double-summation bound is
not a physical acceptance tolerance; native INFPAR equality is exact float32.
Controls test dry-coordinate invariance, zero-rock identity, rock monotonicity,
units, duplicate/support errors and the actual missing-owner join. The input
inventory must retain exact bytes, sizes and mtimes during every readback.

RFG readback parses actual version-9002 horizon rows with all 18 columns,
compares ordered profile/layer counts, depth and RFG against the accepted
readback, then follows the retained source horizon across the normalized 200 mm
split. It reads only the four selected materials. The original raw sieve
measurements are unavailable; no field-data recomputation is asserted.

The numeric table in the findings uses the mode-1, consumer-OFE-3 rows in
`target-physical-basis.csv`: display `1000 * initialized_bulk_occupied_excess_m`,
rounded to three decimals, paired by case and lane. This is length-weighted
positive local excess, not runoff or a signed aggregate storage difference.

Earlier reader versions and tightened validation attempts remain private in the
raw archive. Canonical source, native inputs/outputs and full traces remain
private. Public code, compact derived observations and primary-reference URLs
contain no legacy native source or patch. The retained USDA/NRCS PDFs and their
hashes support the source interpretation; model arithmetic and field validation
remain distinct.
