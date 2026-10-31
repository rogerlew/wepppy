# Replaying the retained native failures

These are diagnostic fixtures, not accepted output baselines. A successful replay
means the released binary reproduced the known failure or passing control exactly.
The original soil/climate/management/runtime inputs are bundled; private run paths
are not required. Use a fresh output root for each invocation.

```bash
wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/replay_daily_coupling.py --root /tmp/roads-daily-coupling-replay

wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/replay_daily_coupling.py --fixture /workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts/broad-failure-fixture --root /tmp/roads-broad-failure-replay
```

The script checks the archive, exact input bytes and pinned `wepp_261029` SHA256,
then compares native exit status and all seven native output hashes. A different
binary is deliberately rejected; future ablations need an explicit new declaration,
not an overwritten receipt. Archives are read member-by-member using flat manifest
filenames; nothing is extracted by trusting an archive pathname.

The first archive contains Birmingham generated roles (expected native stop) and
its matching capped control (expected completion). The second contains Charleston
capped material 53949 (expected native stop) and site capped material 53949
(expected native completion with **invalid sediment accounting**). Completion of
the latter does not pass the physical gate. The known mismatch and physical audit
are preserved in its manifest; use the production interchange readers and the
continuation auditor to independently analyze any new behavioral candidate.

Retained receipts record exact output equality. Independent implementation review
also replayed all four cases in fresh roots and confirmed those hashes. Raw GDB
commands and authoritative logs are retained beside the fixtures, with derived
budgets in `unmet-budget-v1.json`, `paired-daily-coupling-v1.json` and
`charleston-cap-budget-v1.json`. Old GDB commands use forest's retained container
loader/runtime path; the normal fixture replay uses the binary inside the current
WEPPcloud container and does not need that debugger runtime path.
