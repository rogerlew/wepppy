# Tracker

2026-09-11 UTC: closed: implementation, browser validation, full Python
suite and independent reviews complete. Checkpoint ancestor aa30e637e;
owner explicitly granted authority with “authority is granted”.

Delivered: comparison/header, M1/M3 selector, conditional requirements and dNBR,
immutable model/frequency identity, model-aware admission/freshness/preflight,
dedicated M3 task and persistent integration_pending failure. Preserve prior
M1 results, published files, all intermediate records and legacy compatibility.
SSURGO validity assessment and ADR-0066 record subsequent scientific work.

Compatibility: absent legacy model means M1; no GET persistence, result relabeling
or automatic scientific migration. M1 no longer independently requires WEPP Soils;
M3 excludes K/dNBR and enforces configured 10 m ned13/2022. Mod dependencies stay.

Validation: browser dispatched both dedicated tasks and retained M3 failure/M1
files after reload. Delayed state restore and recorder-enabled busy recovery
passed, NOAA selection preserved, downloads200 and live preflight stream verified.
Real Redis preference/phase/publication contention passed at UID 1000/GID 993.
Frontend111 suites/872 tests and lint passed; Go preflight passed; RQ graph and
stub checks passed. Source correctness/security reviews accepted. See artifacts/
validation.md and implementation_reviews.md for evidence and closed findings.

Full-suite fixture fixes: assertions read durable state after singleton refresh;
publication fixtures reacquire controllers before direct writes. Focused route 30,
production 51, publication 13 and migration 24 passed. Final full sweep: 8,468 passed, 103 skipped (971.50s).

Remaining scope: M3 soil/terrain composition, valid-support scalar aggregation,
coverage GeoTIFF, and reports/dashboard. This wiring package does not complete
roadmap stage6 or claim M3 probabilities.
