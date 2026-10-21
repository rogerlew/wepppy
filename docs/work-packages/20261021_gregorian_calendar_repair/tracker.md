# Repair tracker

2026-10-21: Complete (source/local validation). User authorized repair. Both release ASCII and current HBP
source paths identified; previous dirty work preserved. Implementation underway.

Implementation: shared Gregorian calendar wired into loops/readers, complete-record
EOF handling, all-kind ASCII header checks, explicit HBP policy/digest evolution.
62 focused tests and PS05 pass; primary correctness and secondary QA source reviews
approve. Both final candidate pairs built. Full 200-year replays and downstream
interchange are running; compact 400-year ASCII and HBP replays complete. All 104
ASCII hillslope water/PASS sequences match 73,048 climate dates and precipitation.
Broader fpm has preexisting water-balance failures; two policy-dependent fixture
expectations were corrected and targeted checks are being rerun. No deployment.

Full ASCII recovery completed with 73,048 watershed days and 105 aligned PASS
sequences (104 hills + master); interchange emits 7,596,992 hillslope rows with
valid dates. Both 400-year model paths complete; Gregorian HBP interchange now
emits exactly 146,097 unique daily rows after policy-specific padding removal.
Rust converter tests: 109 pass. Fresh pre-calendar source comparison preserves
all nine common 44-year text outputs and all decoded serialized HBP values.
Observability on/off preserves ten 400-year outputs. Full HBP project is beyond
year 150; remaining acceptance is its completion and downstream audit.

Final acceptance: full HBP 200-year watershed and downstream audit pass. Both full
project paths have 7,596,992 unique daily PASS keys, day indexes 1–73,048, and zero
invalid dates. All required local repair work is complete. Native/Rust source
patches, candidate hashes, audits and review records retained. No release vendoring,
production deployment or original-project regeneration was performed. Known broad
gate limitations remain documented; rollout is a separate action.
