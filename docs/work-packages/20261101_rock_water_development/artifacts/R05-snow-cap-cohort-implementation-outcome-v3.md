# R05 snow-cap full-cohort implementation outcome v3

Disposition: PASS for the declared actual collection, ordinary-output parity, reader/cache identity, and final integrity accounting. This is not scientific admission, canonical source integration, or release approval.

The final aggregate is `R05-snow-cap-experiment-v3/receipt.json`, SHA-256 `f55d1f591b7eafbeb1ab8861944623b427a8ad85c38051e2edfc7dd592bc785c`. It reports all 21 declared histories and all nine pair readbacks passed, with no errors. Independent verification completed only after that final aggregate existed.

## Exact evidence and independent checks

- Declaration SHA-256: `e26ce3bf652d153ba11c8c129c076d56f0cb055164b7eccc119158273ca347e5`.
- Actual build/probe receipt SHA-256: `0be0ca23fed2ff2d0574f0d0e3560024cd2cf2a5f67305d5a2bf9be88be3c546`. The prior actual-build review established four matched builds and four 26-case actual-object probes; the retained failed first probe link remains separate evidence.
- Independent verification: `R05-snow-cap-cohort-implementation-verification-v3.json`, SHA-256 `7d274f87ce59b0285f886aec1cdff5cf14d73b71dc868874a0cab0948a2dfabf`.
- Original read-only verifier: `verify_snow_cap_cohort_implementation.py`, SHA-256 `b1ce1e22b7ff47d7c2d48331fcbda1301dcd0a5f189bd36b12fde904a595f347`.

The verifier independently hashed 866 files, checked the current build inventories, binaries and runtime identities, run-approval review hashes, bounded-size declared dependencies, exact task/aggregate correspondence, pre-execution and process receipts, and actual input/output/log files. All processes exited zero without timeout or recorded error. Commands selected the declared lane binary, inputs matched the original declared physical inputs plus the exact observation-window marker, and completion markers were present. No drift was found.

The cohort contains six original-engine observer histories, six clean physical candidates, six observed physical candidates, and three retained-engine counterlane observers. Each has 17,532 daily output rows, totaling 368,172. All 147 ordinary output files were rehashed. Observed candidates match their clean candidate counterparts byte-for-byte in all seven ordinary files; the original-engine and counterlane observers match their own declared retained references. The clean candidates are behavioral references and are not claimed equal to the original engine.

All 15 observation readbacks and diagnostic readbacks match their recorded hashes. Cache contexts match schema, calendar, selected windows, OFE support, reader and helper identities. Every observation readback retains the complete 5,844-day weather census and 17,532 daily OFE opening/closing and causal water-call census; together they report 47,378,433 observed records. Diagnostic trace identities and current sizes/mtimes agree with the case receipts. The nine paired readbacks comprise six original-engine/candidate comparisons and three counterlane/original-engine comparisons. Each pair's stored structural checks agree with its two independently checked cached readbacks, and all nine file hashes match the final aggregate.

## Scope and remaining decisions

No model, compiler probe, or expensive full-trace analysis was rerun in this review. Whole-trace byte integrity uses the executed runner's retained final rehash gate; this independent review joins the trace hashes across case, diagnostic, cache and aggregate evidence and verifies their metadata. It does not claim a second full-trace hash pass. Current metadata and ordinary/readback evidence were independently checked as described above.

Successful pair parsing does not mean physical equivalence or a complete causal explanation. Behavioral differences, snowpack ownership consequences, drainage/ET response, and acceptance require the separate scientific outcome review. Permanent native regression preparation and combined snow/frost source compatibility remain separate gates. Original failed preparations and executed evidence were preserved; only new public implementation-review artifacts were written.
