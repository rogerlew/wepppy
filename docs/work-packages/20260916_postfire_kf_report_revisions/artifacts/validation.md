# Implementation validation

Date: 2026-09-16 UTC. Host: forest. Contract ancestor: `9395f4722`.

## Automated gates

| Gate | Result |
| --- | --- |
| Postfire module sweep | 633 passed, 1,047 unrelated deselected, 196.44s |
| Routes and actual rendered controls | 250 passed, 14.73s |
| Final Kf source/curve checks | 17 passed, 10.57s; includes late field/units/aggregation rejection assertions |
| Canonical archive regression | 1 passed, 21 unrelated deselected |
| Full frontend suite | 112 suites / 899 tests passed, final tree, 7.664s |
| Final report controller | 22 passed |
| Frontend lint | Passed |
| Go preflight | All three packages passed |
| Facade stubtest | Success, one module |
| Stub hygiene | Passed |
| RQ graph | Current; no enqueue dependency edges changed |
| Broad exception enforcement | Passed; zero new broad production catches |
| Full repository pytest | 8,693 passed, 103 skipped, 3,135 warnings, 1,109.71s (18:29) |
| Scoped Markdown and authored-code whitespace | Passed; raw evidence exemptions below |

Commands and full outputs are retained under `logs/`. The focused Kf assertions
added after full-suite startup are covered by the final 17-test run. Existing
warnings are retained, including Python's multiprocessing-fork deprecation; no
warning suppression or unrelated dependency upgrade was added.

## Generated outputs and independent checks

- [Forest restart and recovery](forest_restart_validation.md): real services,
  compiled preflight image, rebuilt UI bundle, idle queues and normal uid/gid.
- [nervous-mesquite](nervous_mesquite_e2e.md): actual UI/RQ job, Kf schema 3,
  8,067 probabilities, three P50 values and all exported curve points checked.
- [Generic fixture and M3](generic_e2e.md): actual source/worker with absent RUSLE,
  immediate/two-reload removal regression, different basin size/source Kf,
  synthetic climate limitation explicitly recorded, saved M3 compatibility.
- Native KFFACT mean and T/F independently recomputed from retained rasters.
  All source request and scientific artifact SHA-256s match their manifests.
- Canonical archive/restore retained 137 and 62 actual generated files on isolated
  copies, including native source windows, HTTP bodies, source metadata and masks.
- Scientific inputs and prior attempts are preserved. One serialized NoDb
  timestamp changed without changing climate settings; this is explicitly
  distinguished from byte equality in the preservation evidence.

## Review and retained failures

Contract reviews passed before implementation at the standalone ancestor.
Final correctness, security and dedicated UX dispositions all PASS with zero
unresolved findings.
Implementation correctness/security/UX reviews and final disposition are retained
alongside this record. Code findings were fixed, tested and re-reviewed.
The initial preflight startup exit, fixture setup errors and browser-harness
mismatches remain inspectable. They were not silently discarded or reported as
successful tests. Recovery did not alter scientific formulas or shared builders.

The report uses the existing Unitizer display factor 0.0393701 for mm/hour to
in/hour. Numerical export checks honor that established factor rather than
silently replacing it with another global conversion. All scientific values stay
canonical. No new dependency, queue, mutable source cache or production deployment.

Original publisher XML is retained byte-for-byte (including its embedded script's
`=======` section separators and trailing spaces). Raw command logs retain tool
whitespace, and browser CSV retains CRLF. Authored-code/Markdown whitespace checks
exclude only the raw log directory and vendored publisher XML and enable Git's
`cr-at-eol` handling for CSV. These are evidence-format exceptions, not hidden
merge-conflict markers or source-code whitespace waivers.
