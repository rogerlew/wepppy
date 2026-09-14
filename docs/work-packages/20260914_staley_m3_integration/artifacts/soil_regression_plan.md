# SSURGO/STATSGO nonregression plan

Status: required execution evidence, not yet run. Owner explicitly requires
preservation of existing soil-building workflows. This is a downstream M3
consumer increment, not permission to repair or simplify shared soil code.

## Protected surface

Preserve `wepppy/soils/ssurgo/ssurgo.py`, `wepppy/nodb/core/soils.py`, associated
builders/spatializers and their runtime semantics: horizon validity and property
estimation, first usable component, restrictive-layer clipping, substitutions,
SSURGO/STATSGO source routing, cache acquisition/schema/refresh, soil metadata,
NoDb inventory and `.sol` generation. Keep RUSLE inputs and outputs untouched.
Any necessary shared-code edit requires evidence and a separately approved delta.

## Before/after evidence

Record base and candidate revisions, dependency/native binary identities, source
fixture hashes and actual tested source modes. On isolated copies, exercise the
existing SSURGO and STATSGO builders with identical frozen inputs before and
after the patch. Compare selected components, substitutions, profile horizons,
parameter values, `.sol` bytes and downstream `wepp/runs/*` soil references and
generated files. Permit only explicitly documented incidental timestamp/path
differences; never normalize numerical fields away. Include a WEPP-invalid but
depth-valid horizon so M3 eligibility cannot leak into WEPP selection.

Snapshot a prepared project's `soils.nodb`, soil maps, soil files, cache schemas
and logical table contents, metadata/substitution records, RUSLE inputs and
generated WEPP inputs. Exercise M3 success, unavailable source, malformed input,
failed publication and retry. Prove no M3-origin write or schema migration to
these upstream records. Where quiescent, compare byte hashes as well. For an
active WAL cache, compare a consistent logical snapshot including committed WAL
rows; do not mistake journal housekeeping for content identity or copy an
incomplete main database. Test actual SQLite read boundaries without mocks.

Do not build or clear live project soils for these comparisons. Use isolated
copies for builder execution and failure injection. Simulate a concurrent source
update in an isolated database; require stale publication refusal without
blocking or corrupting the existing soil writer. Do not clear another task's lock.

## Required cases

| Case | M3 expectation | Protected WEPP expectation |
| --- | --- | --- |
| Normal raw SSURGO inventory | Derived audited thickness | Same builder output and source files |
| Existing STATSGO-built project | Explicitly identified sources; original THICK is distinct | Existing STATSGO builder still works |
| WEPP donor/substitution | Resolve original spatial provenance; disclose any fallback | Same donor selection and assignments |
| Custom/legacy inventory without raw cache | Explicit readiness/fallback outcome under ratified contract | Remains a valid existing WEPP project |
| Missing texture with valid depth | Thickness policy may accept | Existing WEPP validity stays unchanged |
| Paired horizon, gaps, conflicting duplicate, R/Cr/O | Policy-specific audit and tests | No changes to layer filtering or clipping |
| Missing/overfull component weights | Explicit policy and component completeness | No changes to WEPP component ordering |
| Missing/corrupt/WAL cache; cache changes mid-job | Explicit reason or stale failure; no implicit refresh | No cache creation, clearing or migration |
| Repeated M3 run, cancellation/failure/retry | Visible attempts; preserved accepted results | No upstream soil or WEPP input mutations |

Run `wctl run-pytest tests/soils tests/nodb/test_soils_ssurgo_cache.py --maxfail=1`
and the existing NoDb soil tests identified with `rg --files tests/nodb`.
This covers fallback, cache, serialization and masked-valid precedents; retain
exact selected tests in validation.md. Run postfire focused tests, then required
full pytest/npm gates at closeout. Passing tests alone do not replace generated
soil-file parity and real source-write-boundary evidence.
