# Test Payloads
> Culvert batch payload fixtures for integration tests and manual verification.

This directory holds small payload fixtures for culvert integration tests.

## Available Payloads

| Payload | Path | Size | Description |
|---------|------|------|-------------|
| Santee | `santee_10m_no_hydroenforcement/payload.zip` | ~1.5 MB | 63 culverts, UTM zone 17 |

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
