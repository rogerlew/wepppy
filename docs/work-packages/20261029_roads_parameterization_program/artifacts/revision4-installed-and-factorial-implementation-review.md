# Independent installed-release and factorial implementation review

**No remaining implementation blocker.** The installed release readback passes.
The declared factorial is suitable for diagnostic execution after the required
application gate. Full application-suite acceptance remains pending in this
review; completed delivery and a completed broad suite are different claims.

## Installed release

The watershed/hillslope binaries and sidecars in both native `release/` and
WEPPpy `wepp_runner/bin/` equal the reviewed hashes and the corresponding Git
blobs in native release commit `1959d8f619068dbbbc8e0043fc1d37f83ddf0129`.
Native HEAD and its remote-default tracking reference name that commit.

All eight delivery-log hashes match. Their retained results support system
provenance, two host smokes, two container smokes, eight targeted tests, the
selected workflow, and artifact policy. Independently rehashed the selected
workflow's 20 generated inputs, 13 native outputs, two runner logs, and the
generator at its committed source identity. Readback confirms 731 finite,
nonnegative native channel rows, the complete 1980–1981 calendar including leap
day, exact equality of the 22 projected fields in the Rust-generated parquet,
and 731 finite event rows with nonnegative runoff/peak/sediment values.
No production deployment is inferred.

Machine evidence: `/tmp/revision4-installed-independent-review.json`.

## Factorial implementation

Reviewed `combined_hydraulics_r4.py` SHA-256
`30340616218f23dc354e306e97a746dab3de79c67f0a11ecc6406fede66b6194`,
with declaration SHA-256
`65e11c3ef78795e4faae29d7ac3951bc5c654b4f2f1f8e74574e8cce2d72d781`.

Independently verified all 116 case keys have exactly the eight combinations of
road off/on, fill original/fixed, and buffer original/capped: 928 unique cells,
464 new executions, and 464 exact-U12 reuses. The panel has five climates and
seven development materials, 96 original misses and 20 controls.

Rehashed **11,136** staged input files and **3,248** reused native output files,
including their frozen source copies. For every case, independently reconstructed
the complete expected soil text from the baseline and the three factors. This
checks both parsed native fields and appended soil columns. Every staged soil
matches; all non-soil inputs match the case baseline. Below-200-mm horizons,
unaffected role records, geometry, references, and group assignments remain
unchanged. New simulation output directories were empty; reused outputs occupy
separate new directories and do not mutate the frozen U12 archive.

The updated runtime preflight passed inside the intended WEPPcloud container:
all 70 effective dependency hashes match, including dynamically loaded audit
helpers, lazy Python/Rust readers, and the resolved calendar manifest. Script,
plan, binary, and direct helper hashes also match. Every preserved pre-execution
declaration has an identical task list, confirming that reporting/dependency
revisions did not alter the reviewed inputs.

The initial reporting gap is closed: current `report()` retains per-lane
recoveries/control regressions, meaningful/small counts, all five strata,
paired cells, and conditional finite differences of every order. The contrast
signs and background enumeration implement the stated factorial differences.
Physical-audit outcomes and strict particle flags remain visible, and summary
language explicitly withholds reviewed physical/candidate acceptance.

Residual limits: new-run outputs and particle certificates still require their
declared checks after execution. The coupled road treatment does not separate
pore and conductivity causality. Neither this selected-panel implementation
review nor a successful diagnostic result establishes broad parameterization
success, withheld-material acceptance, or UI approval.

Machine evidence: `/tmp/combined-hydraulics-r4-input-review.json`.
Independent reconstruction probe: `/tmp/review_combined_hydraulics_r4_inputs.py`.
