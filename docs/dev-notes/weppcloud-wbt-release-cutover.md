# weppcloud-wbt Release Cutover Reference

Use this note when WEPPpy starts failing on WBT tool lookups after a
`weppcloud-wbt` release.

## Canonical Build/Install Runbook

- Upstream source of truth:
  `https://github.com/rogerlew/weppcloud-wbt/blob/master/docs/release-build-install.md`

## Fast Runtime Verification (from WEPPpy)

```bash
cd /workdir/wepppy
wctl exec weppcloud bash -lc 'cd /workdir/weppcloud-wbt/WBT && ./whitebox_tools --listtools | grep -E "IterativeFirstOrderLinkPrune|RemoveShortStreams"'
```

## Known Failure Signature

If the binary is stale, RQ jobs can fail with:

- `WhiteboxAppError: Unrecognized tool name IterativeFirstOrderLinkPrune`

When that appears, run the full `weppcloud-wbt` release runbook and re-check
from the container runtime before retrying the failed job.
