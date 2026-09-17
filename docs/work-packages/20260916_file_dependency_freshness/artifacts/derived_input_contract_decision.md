# Derived input byte verification checkpoint

Starting revision: `984023c18`, with prior reviewed implementation waves in the
working tree. Owner authorization is execution of this package and its confirmed
consumer fixes. C01 baseline now exercises actual PRISM/RAP finalizers with real
same-size/restored-mtime writes: `derived_build_baseline_probe.py` and `.log`
(two defect-characterization cases pass). Numerical collection is injected,
not claimed as end-to-end native acceptance.

## Normative delta and rationale

Canonical authority is the NoDb persistence/concurrency contract, Long-running
collect-then-finalize pattern plus new Derived input byte verification section.
A main-file byte digest supplements existing transaction metadata, not replaces
it. Add an uncached bounded read with descriptor/path checks; preserve explicit
filesystem failures and existing finalization/publication contracts. Retain
metadata-only transaction conflicts as conservative existing behavior. No
accepted result cache or new polling hash is introduced.

## Reviewed scope correction

The original proposal added a flat GDAL file-list snapshot and rejected nonlocal
members. Independent real probes showed two defects in that proposal: nested
VRT member lists are not transitive, and a local ZIP-backed VSI raster is valid
existing input. Do not implement that proposal or add its path restriction.
Retain both review probes and original findings as evidence.

Split this wave to add uncached byte verification for the existing main-path
set only. No new GDAL reads, format restrictions, dependency traversal or changes
to numerical readers. Raster dependency closure remains explicitly OPEN under
C01 as well as C03/C04/C05/C06; package closure is blocked until a separately
reviewed recursive/VSI-compatible design and native acceptance address it. This
split fixes the reproduced main-file defect without pretending that a one-level
list is complete. Shared raster handling is now justified by multiple concrete
consumers but needs its own compatibility/performance checkpoint.

## Compatibility and valid-state matrix

| State | Expected result |
| --- | --- |
| Existing ordinary local CLI/raster | Existing build result; collection and finalization bytes agree |
| Equal-size/restored-time changed bytes | Explicit superseded conflict; no new output published |
| Missing or unreadable required input | Existing explicit failure; no publication |
| Empty plain input | Digest allowed; consumer retains its validation |
| Malformed raster | Existing numerical validation; byte signature adds no format policy |
| Same-byte replacement before collection | Normal build |
| Mtime change during collection | Existing conservative conflict retained |
| Hard-link creation without mtime change | Digest unchanged; no new transaction conflict |
| Added/removed/changed indirect raster dependency | Separate OPEN closure wave; no claim from this main-file change |
| Legacy persisted NoDb | Unchanged; signatures are transaction-local only |

## Performance and validation

No new dependency: hashlib is from the standard library.
Retained cold hash baseline is 0.089 seconds for 26.4 MB on the representative
run mount. Budget: one uncached signature pass at most twice that measured cost
for that file, excluding one-time module import, and exactly collection/finalizer
passes rather than per-band or per-pixel hashing. Hashing occurs under the existing finalization lock; the file benchmark does
not bound full multi-year RAP lock occupancy. Measure complete representative
RAP sets before closure and retain lock duration. The budget for an operational
set is at most 10 seconds of hash work within finalization, subject to evidence;
if it fails, revise the design before shipping, not silently enlarge the budget.
Do not claim polling performance from this build-only path. No numerical formula/default change or new cache heuristic is proposed.

Add real restored-time transaction regressions, bounded growth/descriptor drift
checks and rollback preservation coverage. Native VRT/aux/VSI closure fixtures
belong to the explicitly open follow-up wave.
Run derived-builder suites plus full sanity. Final restarted native build and
archive acceptance remains required. Separate correctness/security reviews and
a docs-only checkpoint ancestor are required before implementation.
