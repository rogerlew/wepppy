# Tenderfoot calibration tracker

Updated: 2026-10-09 00:29 UTC.

Baseline diagnosis complete: 4,142 matched days, outlet bias −69.73%, NSE −0.038; 1993–2015 modeled P/ET/Q approximately 774/647/127 mm/year. Observations and daily outlet conversion verified. PAT-authenticated API discovery succeeds. Existing run has no blocking readiness issues.

Blocked: both fork jobs failed at task import with `FileNotFoundError` for `/workdir/weppcloud2/weppcloud2/discord_bot/.bot_token`. Intended `kcb=0.80` destination `overall-thruster`, job `2b10aba6-39c4-46a9-94e2-e40984b69c45`; intended `kcb=0.65` destination `tacky-seeking`, job `7ededfcb-38d3-401b-b76b-ccfee1e43652`. Neither destination directory exists. Receipts and failure traces are retained with baseline diagnostics in `trial_jobs.json` and the two `*-fork-jobinfo.json` files.

Readback verified unchanged baseline hashes for `wepp.nodb`, `soils.nodb`, `climate.nodb`, `wepp/runs/pmetpara.txt`, and `observed/observed.csv`. No coefficient mutation or model execution occurred. Next: restore the existing fork-worker notification credential/configuration through the established deployment mechanism, then retry the isolated trials under the [active plan](prompts/active/tenderfoot_calibration_execplan.md). Infrastructure repair remains outside this API-operator attempt.

User correction, 2026-10-08: Discord is optional; provisioning its credential is not the required fix. The bounded [import repair](artifacts/20261008_discord_import_conformance.md) supersedes the recovery recommendation above. Four RQ modules now match existing core WEPP handling. The regression reproduced the production failure before patching; initial focused validation passed 54 tests with 26 skips. Independent static correctness review found no blocking findings. Final test isolation/full-suite checks and production deployment validation remain pending; calibration forks remain unexecuted.

Validation completed 2026-10-09 00:29 UTC: all three isolated import cases pass; stub completeness and docs checks pass. Full suite: 10,284 passed, 126 skipped, one failure at the unchanged TTL/catalog p95 timing test (61.1 ms overhead versus 50 ms limit). Its isolated recheck also fails; no claim of a green full suite. Import repair remains local; deployment and the real fork retry are still required before incident closure. No unrelated performance or PRISM code was changed by this repair.
