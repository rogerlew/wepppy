# Run-page export presentation tracker

2026-11-24 05:02 UTC. Scoped from local master acbafe0bc. Baseline route tests started. Implementation and candidate verification pending.

2026-11-24 05:04 UTC. All 60 remaining blueprint functions, including request handlers, are syntax-tree identical to the baseline. The 26 extracted functions split evenly between source column discovery and presentation. Only the two catalog loader failure paths differ in their logging. Both preserve their existing fallback payload. The changed-code broad-exception check passed.

## Local validation

2026-11-24 05:06 UTC. The route, rendering and payload comparison run passed 456 cases with 15 skips. Receipt `da5d04c599354b71be07ff409c3b5e52` tested candidate `d8ffdfbe6`. Both payload entry points were invoked through the blueprint against the actual 27-layer catalog, first in an empty directory, then with a Landuse Parquet containing a new measure, a Roads output directory and an Omni scenario. The normalized JSON catalog and bootstrap pairs matched the baseline byte for byte. The empty SHA-256 was `0390ce979203bb9dee298ebcf3560d5317671835d8862d582890f6ab1067fa3d`. The populated SHA-256 was `a3670c98c53097b547dccaa1478880b13c1c5e2fd9f51a6624b5d09d9f0d36c2`.

The broad suite passed runtime checks and exercised the previous failure first with `--failed-first --maxfail=1`. It stopped at `test_adduser_errors_when_user_unknown` because the response spells WEPPcloud differently from the assertion. The same test failed on unchanged local master with the same runtime. Baseline receipt `b1a2aa01eb864c618139023bd9fcd1b2` and broad candidate receipt `6c4cef19a15b4735bae5409deb8a0be7` record the failure. Full-suite validation remains incomplete.
