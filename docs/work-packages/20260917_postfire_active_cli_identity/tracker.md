# Active CLI repair tracker

Closed 2026-09-17 UTC. All acceptance and review gates complete.

- Contract checkpoint: `567eacf7d`; implementations: `2b00c4165`, `1003fe9ad`.
- Main full suite: 8,971 passed, 99 skipped. Late corrections: 107 final boundary,
  21 preparation and two final native legacy tests passed; archive regression passed.
- Final independent correctness/security reviews PASS; all findings closed.
- Restarted rq-engine/rq-worker/weppcloud; live WEPP materializer overlap passes,
  equal-size restored-mtime changed bytes reject and preserve accepted results.
- Final named recovery: job `0c3bb451-0e7a-4814-95f5-3f1d2f219d49`, accepted
  attempt `8190121c8a4b45e1952861e74d909693`. Current after reload, downloads
  verified, scientific inputs unchanged, historical records browsable and retained.
- Documentation/exception enforcement and final whitespace checks pass.

[Runtime evidence](artifacts/runtime_acceptance.md) explicitly distinguishes
full-suite coverage from the later targeted conformance checks. Failed baselines,
fixture/timestamp corrections and transient browser admission conflicts remain
recorded. Existing recorder/startup contention is a small separate UX follow-up.
The normative decision is the shared freshness contract's active CLI amendment;
this closed package is historical evidence, not living governance.
