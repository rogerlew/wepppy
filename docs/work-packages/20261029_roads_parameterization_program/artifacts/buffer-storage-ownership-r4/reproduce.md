# Reproduce the consumed-storage readback

The readers are original analysis code. Native sources, instrumentation patches,
full state traces and inputs remain in private retention. This packet reports
selected-event arithmetic and executed ownership, not a parameter promotion.

## Retained observations

From the WEPPpy repository root, use a new destination:

```bash
python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4/read_retained.py \
  --study out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2 \
  --inventory out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/original-inventory.json \
  --out out/roads-parameterization-program-20261031/buffer-storage-reproduction-new
```

Expect 152 exact native storage calculations, 556 consumed layer rows, 432
structural rows and 64 explicitly unavailable GRNA groups across 36 histories.
All five CSV tables must match the retained readback exactly. The receipt binds
the invoked script path/hash and immutable input bytes, sizes and timestamps.
Running into an existing destination fails before writing output.

The current-profile conductivity reconstruction in this first reader is labeled
as arithmetic agreement. It is not the initialization-producer proof; the
separate initialization readback supplies that evidence.

## Initialization and hydraulic context

With the new private study restored and verified, use two additional fresh destinations:

```bash
python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4/read_initialization.py \
  --probe out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe \
  --retained out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/readback-v3 \
  --count 36 \
  --out out/roads-parameterization-program-20261031/buffer-storage-init-reproduction-new

python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4/read_context.py \
  --response docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-hillslope-response-r4/summary.json \
  --response-manifest docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-hillslope-response-r4/manifest.json \
  --out out/roads-parameterization-program-20261031/buffer-storage-context-reproduction-new
```

Expect 586 initialization layers, 556 consumed-layer joins and 152 connected
calls, with all native arithmetic exact. The explanatory double-component
identity has a separately declared 1e-15 m summation bound; it does not relax
native equality. Expect 36 context rows. All four initialization CSVs and the
context CSV must reproduce exactly. Reader controls reject missing, duplicate,
misordered and changed support; input hashes and original nonmutation are
checked separately. Independent reviewers rehash actual native output parity.

The context table uses the already reviewed response publication. Its final IRS
boundaries, lengths and durations differ in temporal support from GRNA entry
storage; hourly local and upstream depths retain their separate spatial support.
No complete water closure or annual causal partition is inferred.

## Headline contrasts

The original contrast arithmetic sums weighted pore/dry components in retained
layer-row order, subtracts lane values in meters, then converts to mm. Reproduce
all 18 both-mode rows, including the nine shown in the findings:

```bash
python -B docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-storage-ownership-r4/read_contrasts.py \
  --retained out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/readback-v3 \
  --out out/roads-parameterization-program-20261031/buffer-storage-contrasts-reproduction-new
```

Expect byte-identical `target-contrasts.csv`. Publication revision 2 adds this
retained generator and command; the first reviewed packet and its review remain
private in `publication-v1/`. Numerical tables and scientific findings are
unchanged. This closes reproduction coverage of all 11 published CSV tables.

## Restoring private evidence

The original response archive and the new study archive have separate retention
receipts. Verify each archive SHA256, companion manifest and every member before
using restored evidence. Do not substitute earlier response attempt-u1 histories
for accepted u2. Raw evidence contains legacy native source and is private.

The original inventory records nanosecond modification times. Archive extraction
may reproduce bytes without exactly preserving those times. For a restored tree,
first verify its complete file inventory, sizes and SHA256 against the original
manifest, then record a separate restored-metadata inventory with the restored
modification times. Bind that new inventory explicitly when invoking the reader;
retain the original inventory unchanged. This is a restoration metadata binding,
not permission to accept changed data or waive nonmutation during readback.

Do not invoke canonical conversion audits on accepted case directories: they
write Parquets. This study reads plain traces and does not need those converters.
Every new readback and failed attempt must use a fresh directory.
