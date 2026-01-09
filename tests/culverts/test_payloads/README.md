# Test Payloads
> Culvert batch payload fixtures for integration tests and manual verification.

This directory holds small payload fixtures for culvert integration tests.

## Available Payloads

| Payload | Path | Size | Description |
|---------|------|------|-------------|
| Santee | `santee_10m_no_hydroenforcement/payload.zip` | ~1.5 MB | 63 culverts, UTM zone 17 |
| Hubbard Brook | `Hubbard_Brook_subset_11/payload.zip` | ~116 MB | 11 culverts (outlet seeding, outside watershed, junction mask) |

### Hubbard Brook Edge Cases

The Hubbard Brook payload contains 11 watersheds specifically selected for edge case testing:

**Outside watershed polygon (validation failure):**
- Point_ID 7, 10, 150, 196, 207

**Outlet seeding / boundary extension required:**
- Point_ID 3, 8, 9, 26, 120

**Junction mask fallback (chnjnt):**
- Point_ID 147


### Hubbard Watersheds Under 1 Hectare Analysis

  Dataset: 528 total watersheds, 127 (24.1%) are under 1 ha

  Distribution
  ┌───────────┬───────┬──────────┐
  │ Statistic │  m²   │ Hectares │
  ├───────────┼───────┼──────────┤
  │ Min       │   0.3 │  0.00003 │
  ├───────────┼───────┼──────────┤
  │ Median    │ 382.5 │    0.038 │
  ├───────────┼───────┼──────────┤
  │ Mean      │ 1,595 │     0.16 │
  ├───────────┼───────┼──────────┤
  │ Max       │ 9,397 │     0.94 │
  └───────────┴───────┴──────────┘
  Size Breakdown
  ┌────────────────────────┬───────┬─────┬────────────┐
  │         Range          │ Count │  %  │ Cumulative │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0 - 0.01 ha (0-100 m²) │    56 │ 44% │        44% │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0.01 - 0.05 ha         │    22 │ 17% │        61% │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0.05 - 0.10 ha         │    22 │ 17% │        79% │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0.10 - 0.25 ha         │     2 │  2% │        80% │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0.25 - 0.50 ha         │     7 │  6% │        86% │
  ├────────────────────────┼───────┼─────┼────────────┤
  │ 0.50 - 1.00 ha         │    18 │ 14% │       100% │
  └────────────────────────┴───────┴─────┴────────────┘
  Key Observations

  1. 11 watersheds are single pixels (0.3 m²) - likely artifacts at pour points
  2. 44% are under 100 m² - extremely small, probably noise
  3. Same tiny watersheds appear across multiple batches (runs 3, 9, 26) - suggests systematic artifacts from specific culvert locations

  Threshold Impact (on <1 ha subset)
  ┌──────────────────┬─────────┬──────┬────────┐
  │  Min Threshold   │ Removed │ Kept │ % Kept │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 10 m²            │      11 │  116 │    91% │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 100 m² (0.01 ha) │      56 │   71 │    56% │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 500 m² (0.05 ha) │      78 │   49 │    39% │
  ├──────────────────┼─────────┼──────┼────────┤
  │ 1000 m² (0.1 ha) │     100 │   27 │    21% │
  └──────────────────┴─────────┴──────┴────────┘
  Recommendation

  A minimum threshold of 0.01 ha (100 m²) would:
  - Remove 56 micro-watersheds that are likely noise/artifacts
  - Still retain 71 small but potentially valid watersheds under 1 ha
  - Remove only ~11% of total dataset (56 of 528)

## Quick Start

```bash
# Submit to test server
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python \
  docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py \
  --payload tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip

# Or copy to a temp location first
cp tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip /tmp/
WEPPCLOUD_HOST=wc.bearhive.duckdns.org python \
  docs/culvert-at-risk-integration/dev-package/scripts/submit_payload.py \
  --payload /tmp/payload.zip
```

## Guidelines
- Keep files small (target <10 MB).
- Derive fixtures from `Santee_10m_no_hydroenforcement` where possible.
- Do not commit large rasters; store only minimal slices or downsampled data.

## See Also
- [dev-package scripts](../../../docs/culvert-at-risk-integration/dev-package/scripts/README.md) - Build and submit tools
- [weppcloud-integration.spec.md](../../../docs/culvert-at-risk-integration/weppcloud-integration.spec.md) - Payload contract
