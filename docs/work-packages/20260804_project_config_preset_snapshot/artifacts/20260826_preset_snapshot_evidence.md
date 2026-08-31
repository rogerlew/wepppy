# WP04 Preset Snapshot Evidence

## Result

WP04 implements a dormant, default-off named-preset writer on the existing
rq-engine creation boundary. The checked-in policy corpus covers all 128
non-default shared presets. Generated temporary-run fixtures prove canonical
flattened bytes, manifest digest/parent-chain integrity, sanitizer acceptance,
WP02 reopen without shared fallback, source independence, atomic pair cleanup,
and overwrite refusal.

The enabled route writes `<preset>.cfg` and `config-manifest.json` before Ron,
uses the stable preset token, and applies a 24-hour Redis idempotency contract.
The absent/false flag retains the legacy query-suffixed Ron input.

## Verification

- Focused snapshot/idempotency/route: 43 passed.
- Interfaces/create rendering: 12 passed, 139 deselected.
- NoDb plus microservices: 3,013 passed, 30 skipped.
- Exact full suite: 6,882 passed, 63 skipped.
- Stubtest: both new modules passed; repository stub check passed.
- Broad-exception changed-file enforcement: passed, net delta zero.
- `git diff --check`: passed.

WP05 owns adding stable capability IDs and making them authoritative. WP04 does
not assign the continental-US capability profile to international or otherwise
incompatible legacy presets by inference.

Implementation revision: `140354fde`.
