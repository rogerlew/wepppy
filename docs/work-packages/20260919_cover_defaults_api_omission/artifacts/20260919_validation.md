# Validation evidence

Base `1b4f9af72`; contract ancestor `acc192323`; implementation `b1e857765`.
Production code SHA-256:

- `wepppy/nodb/core/landuse.py`: `01e2cc755360a19a0690d9365a7bb3a1247920b927f631f8dc88d37f0e625ebd`.
- `wepppy/nodb/core/wepp_input_parser.py`: `97de7615d3f7b8d83eb8cbfb867d7d3ec00d2472e47fe74d56f100e13912cd12`.

## Regression evidence

Before correction: omitted kslast 0.0/0.0001 became None; configured canopy 0.0
remained 0.4 in the emitted file. Both assertions failed on the old code.
The first writer-failure test patched the pool batch helper while the fixture
used sequential execution, so it did not inject failure. Replaced with a real
directory-at-output-path `IsADirectoryError`, retaining the old file; successful
retry regenerates after overrides already equal defaults.

Expanded focused suite: 286 passed (31 warnings, 22.46 seconds), including actual initial-build and selected
modification management readback, prepared cover files, durable Wepp facade
reload, legacy/zero/None, failure/retry, canonical archive suite and seven
JSON/form transport tests through the real parser.
Broad suite: 9,079 passed, 99 skipped, 3,159 warnings in 1,477.27 seconds,
exit0 (`wctl run-pytest tests --maxfail=1`). It collected before 28 late-added
cases, covered by the final 286-test focused run. Stub completeness, changed
broad-exception gate (delta zero), scoped docs lint and diff check pass.

## Forest execution

Source: `/wc1/runs/eq/equestrian-bonheur`. The validator pins its three NoDb
hashes and reads all source managements; no source mutation is authorized.
Fork: `/wc1/runs/co/cover-defaults-validation-20260919`.
Supported fork job `763a90ea-0357-4f5c-8f4b-1e9578b0f6d2` finished at
2026-09-19 16:04:10 UTC. Skip WEPP run/output and Omni children, do not undisturb.

Fixture setup alone supplies `cover_defaults_d` for class406: canopy0.75,
interrill0.90, rill0.90 under the real NoDb lock. This is not a new production
default or claimed public setting. Normal `modify-landuse` request
`{"topaz_ids":[101],"landuse":"406"}` returned HTTP200 at 16:06:50 UTC;
all455 hillslopes/1,065 segments emitted the defaults. Existing applicability
is class-wide; selecting101 does not limit configured default application.

Workers were idle before targeted restart of rq-engine/default/batch. Running
container code hashes match the implementation above; validation identity is
UID1000/GID993, groups993. No image build or production deployment.

Normal `run-wepp` POST `{}` returned HTTP200 at 16:07:21 UTC with parent
`56d90c88-bca6-4f2f-9f3c-074bcf1f003f`. kslast is intentionally omitted;
fresh detached readback retains 0.0001. Existing `wepp_260803` remains selected
(SHA-256 `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`).
Prepared acceptance passes all455 hillslopes: 910 combined/prepared managements
have canopy0.75/interrill0.90/rill0.90; prepared soils equal source parsed objects
excluding provenance headers, climate/slope bytes match, and managements equal
source after normalizing only the intended two ground fields. No watershed or
channel-input parity claim is made. All1,065 segments retain intended covers.
The complete source910-file management manifest is unchanged before/after:
SHA-256 of sorted JSON `source_management_hashes` is
`142e5a8563dc73d53fb81d9114b1dad59479d84672a91a8199cc74e8b02bfcf0`.
All 15 jobs finished by 16:14:59 UTC. Fresh interchange contains exactly 455
unique expected hillslope IDs and finite runoff/sediment values: area-weighted
runoff 942.933781 mm/year; hillslope sediment yield 3,348.4272 tonnes/year.
These are validation outputs, not a compiler comparison or watershed-outlet total.
The 2,736-path inventory includes all 455 generated soil intermediates and
`soils.nodb`, addressing the reviewer's archive-coverage observation.

Normal Chromium project page and four downloads returned HTTP200; downloaded
bytes match disk:

| Artifact | SHA-256 |
| --- | --- |
| `landuse/hill_101.mofe.man` | `617a1aa092a3f5c4b18931b191ca86d2ac0cd415e6c1699205adf5d9e097fdd2` |
| `wepp/runs/p1.man` | `6e2102ab3609a176a3a727ca257048f8f8ecdb8e4d7fdd922db42a54e6926dbe` |
| `wepp/runs/p1.sol` | `a61254a6b9d7baebbac690f94a70d58d4d78f866469aed1d5f64e13b78a114d7` |
| `wepp/output/interchange/loss_pw0.hill.parquet` | `c82da57a03a9f82f2738643a8ca7f6a5831e0330f21c6afbbb48d3d7d2166e7d` |

Archive job `d5155a05-215f-446c-b93d-2928b218cea8` finished at 16:19:26 UTC.
Retained fork-local archive:
`archives/cover-defaults-validation-20260919.20260919T161627Z.zip`;
SHA-256 `9bc2b5ac9e27bbb04b153251fdcc18a1f05e685be518d4e0bcb1a28433d2309e`.
Archive verification passes all 2,734 model/state records exactly and requires
the two append-only logs to exist. Restore job
`eb2d87bd-75ac-416f-804c-eb7db1ab85b1` finished at 16:22:31 UTC, targeting only
the disposable fork's own archive. Post-restore validation passes: all 2,734
non-log hashes equal the pre-restore inventory and archived bytes; covers,
kslast, prepared parity, outputs and source preservation still pass. SHA-256
of the pretty-printed non-log hash mapping before and after is
`58c52ca9684411de41737b4ee2009b8708d9a191862c79eaaec2099488a9ff68`.
Normal browser and all four downloaded byte checks pass again after restore.

Discovery via canonical Forest domain passed configs/endpoints/create schema,
source pipeline/readiness and run operation docs. An initial incorrect internal
port probe refused connection before any mutation; corrected to the configured
domain. No service/config workaround was introduced.
