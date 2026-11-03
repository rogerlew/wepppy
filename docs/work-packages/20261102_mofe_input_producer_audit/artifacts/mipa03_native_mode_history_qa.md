# MIPA-03 independent native mode and development-history QA

Status: PASS for the bounded checks below. This report separates the earlier
**development-history binary** from the **final watershed binary** used for the
combined execution. The final-history closure below binds the completed final
replay separately; release gates remain outside this report. Reference scientific
quirks remain unchanged.

## Actual compiled mode transitions

Native `tests/test_specialized_rap_mode.py` compiles the actual `rap_state.f90`
in a private directory, with bounds checks and floating-point traps. Nine tests
cover active continuous RAP followed by `ivers=3`, reactivation, another routing
transition, six fresh disabled cases, and explicit rejection of requested RAP
in noncontinuous, nonrouting mode. The transition cases preserve one live module
across calls and test routing with both model values; they do not infer reset
behavior from fresh processes.

A tenth test executes actual MAIN on the final watershed binary. It stages the
committed `tools/physical_water_case.py` generator and
`tests/fixtures/physical_water/{single,shared}` resources for the complete 1980
calendar. A deterministic one-year, one-OFE cover deck and the RAP/observer
markers activate the hillslope consumer. The combined run card selects
`ivers=2`, generates a fresh hillslope PASS, and reaches MAIN's automatic
`ivers=3` transition and watershed routing in the same invocation. No channel
cover deck is supplied. Assertions require watershed completion, exactly one
RAP activation/read, exactly 366 distinct hillslope GROW dates, a fresh hillslope
PASS and channel water output. Channel growth adds no RAP GROW records.

```bash
PATH=/usr/bin:/bin:$PATH \
WEPP_RAP_MODE_BINARY=/home/workdir/wepp-forest-release-20261009/release/wepp_261029 \
pytest tests/test_specialized_rap_mode.py -x -q \
  --basetemp=/wc1/holdouts/mipa-native-r7-20261103/mode-history-qa/probes-v2
```

Result: **10 passed in 10.21 seconds**. These tests were run separately after the
parent's full-suite collection; do not add them to that suite's reported count.
The exact final watershed SHA-256 is
`4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`.

The retained first combined attempt failed because the test card retained the
hillslope-only `ipass` answer, shifting later routing prompts. The corrected
card omits that answer and supplies explicit routing prompts. No model source
changed to resolve this test setup error. Both attempt logs are retained.

## Independent review of eight development histories

Read-only audit source and results:
`/wc1/holdouts/mipa-native-r7-20261103/mode-history-qa/audit.py` and `audit.json`.
Inputs reviewed: `/wc1/holdouts/mipa-native-r7-20261103/histories-development-v1`.
The reviewed receipt SHA-256 is
`bdc10e33367832a515da52a217f041d4575baeab676f5a66657dd546c5f77007`.
Its declared development hillslope binary SHA-256 is
`210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
This is different evidence from the final watershed invocation above.

The audit independently rehashes every declared input and output, checks the
complete production output inventory, reparses the water files, and recomputes
all reported per-OFE totals with finite-value and calendar checks. It verifies:

- Eight successful receipt statuses and empty retained stderr files.
- Exactly 17,532 unique water rows per case: three OFEs, every day of 2000–2015,
  including leap days. All parsed numeric fields are finite.
- Every receipt water total and terminal row agrees with the retained artifact.
- Four observer-off/on pairs have identical bytes in all seven production output
  files; each pair differs only in the observer input marker.
- Each observed case contains 3 SOIL, 17,535 HYDRAULIC and 17,532 GROW records;
  all dynamic numeric fields are finite, all growth dates are unique and complete,
  and every hydraulic record has `ks = ssc(1) = ssc(2)`.
- Transformed/observed pairs differ only by `simfire.txt`. Daily/hourly pairs
  differ only by `wepp_ui.txt`.

The first transformed GROW difference is fire day, 2005 day 196; the first water
artifact difference is 2005 day 197 in both daily and hourly histories. OFE 1
canopy is identical at 0.389999986 on fire eve; on fire day it is 0.224999994
observed and 0.165000007 transformed. Both histories recover to 0.393999964 on
2006 day 195, then change to 0.227999985 and 0.166000009 on day 196. This records
the preserved recurring year/day condition; it is not a scientific correction.

Selected full-history OFE 3 totals, in mm (rounded here only for readability;
`audit.json` retains parsed precision and deltas for every OFE):

| Mode | Cover | Q | Ep | Es | Dp | Lateral flow |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Daily | Observed | 8125.484 | 8832.75 | 2202.30 | 2202.954 | 37890.88 |
| Daily | Transformed | 8250.335 | 8298.12 | 2430.20 | 2269.937 | 38100.08 |
| Hourly | Observed | 340.009 | 6794.18 | 2373.27 | 996.556 | 72498.20 |
| Hourly | Transformed | 341.041 | 6538.98 | 2608.42 | 999.811 | 72556.26 |

These contrasts establish propagation to generated water artifacts. They do not
establish scientific validity or equality of daily/hourly formulations. The
large mode differences remain explicit evidence; this QA changed no formulas,
thresholds, inputs or reference implementation to reduce them.

## Evidence and limits

`mode-history-qa/` retains the independent audit, both pytest logs, private probe
builds, combined inputs/outputs, stdout/stderr and an artifact hash manifest.
The audit can be reproduced with `python3 mode-history-qa/audit.py` using its
recorded absolute input location. It is supplementary holdout evidence, not a
required pytest dependency. The committed test uses only committed resources
and its deterministic generated cover deck.

No production source edits, shared builds or reference repository writes were
performed by this QA agent. The parent owns full native tests, final-pair
history replay and release gates. The three-OFE histories do not establish
OFE 2/10 binding; that discriminating coverage remains in the independent
12-OFE compiled growth/hydraulic probes. The combined test uses the inherited
9002 physical-control soil deck and establishes mode transition behavior;
9005 parsing and numerical formulas are covered separately.

## Final-history QA closure

The independent audit was rerun against every retained artifact under
`/wc1/holdouts/mipa-native-r7-20261103/histories-final-v1`; it passed all eight
cases. This reparses final water/observer outputs and rechecks all file hashes,
complete calendars, finite values, receipt totals, terminal states, controlled
input contrasts and four observer-neutrality pairs. It does not reuse a prior
PASS result solely because the declared binary hashes match.

The final receipt SHA-256 is
`5b9e5395c818756d61ac6d28369bab3382950be2145e8fab0a309bc76f0e8720`.
The audit independently hashes the actual final executable at
`release/wepp_261029_hill` and confirms
`210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`,
which matches both the final receipt and the development executable identity.
All eight final case receipts agree exactly with their development counterparts;
all 56 production output files and all eight RAP observer files agree exactly.
The numerical contrasts and preserved fire timing reported above therefore
also describe the final histories without a tolerance change.

Reproduction and evidence live in
`/wc1/holdouts/mipa-native-r7-20261103/mode-history-final-qa/`:
`audit.py`, `audit.log`, `audit.json`, `bind.py`, `binding.json` and `manifest.json`.
Run `python3 audit.py` and `python3 bind.py` from that directory. The input
paths are retained explicitly in the scripts and receipts.

This closes the independent final-history integrity and numerical-contrast
review. It does not approve the draft scientific report, its remaining
`FINALGATES`/`APPLICATIONRESULT` placeholders, the unfinished full-suite gate,
or configured-application execution. Those remain parent-owned follow-up work.
