# Century-calendar failure findings

Status: diagnosed and reproduced; repair identified, not implemented.
The actual project is `/wc1/runs/ch/chemotherapeutic-scope` (104 hillslopes,
200-year climate starting at year 1). The released executable is
`wepp_runner/bin/wepp_261010`, SHA256
`1dd1ca75cf53f9a0606cf5a598312d4e680e161df631156360d4a20dbcb6f17e`, source
`7471bb5e981d14d0b8c1cdb88a16af305aed1b67`. It consumes ASCII PASS components
v3, not binary HBP. The earlier schema-2 reader correction is independent.

## Confirmed artifact chain

The supplied climate has 73,048 records and no February 29 in years 100 or 200.
All 104 hillslope PASS files and the master have 73,050 days with a 366-day year
at both boundaries. Every PASS key matches the legacy every-four-years calendar;
there are no isolated hillslope date disagreements. See [full audit](date-audit.json)
and [reproducible parser](audit_dates.py).

Release `contin.for:636`, `wshdrv.for:565`, and `wshpas.for:371` calculate the
Gregorian rule, then explicitly override it with `legacy_centurial_day366`.
The loops consequently request an extra February day. The internal monthly-loop
date first diverges at its February 29/year 100, consuming March 1 climate.
The numerical year/Julian counters still coincide through day 365/year 100.
Their first mismatch is ordinal 36,525: PASS `(100,366)` consumes climate
January 1/year 101. Next model day `(101,1)` consumes January 2/year 101.

`stmget.for:137` assigns the year/month/day from each climate row, while `sdate`
is independently incremented by the simulation loop. Hillslope PASS is written
with `(lyear,sdate)` in `contin.for:1285`. Daily water balance is written with
`(year,sdate)` in `watbalprint.for:101,116`; `sedout.for:440,511` uses climate
calendar day/month/year for event output. Thus output families expose different
combinations of the conflicting counters.

H1 water balance confirms this directly: `(year=101,day=366)` then
`(101,1)` with 5.40 mm precipitation from **January 2**, then `(101,2)`.
There are 36,524 date discrepancies over the 73,048 actual climate rows, with
zero precipitation discrepancies when matched by sequential record position.
This is direct evidence for a post-century shift in Julian-day hillslope output
relative to calendar-dated event output. Jackson's separate run is not available,
so this does not establish its precise revision or complete failure mechanism.
See [weather audit](weather-audit.json) and [parser](audit_weather.py).

## Why this run stops in year 102

`wshred.for:116` reads only the master event kind, ignoring the daily header date.
Only EVENT records invoke `mixreadmaster(49,year,sdate,nhill)` at line 145.
SUBEVENT and NO EVENT records do not check the daily date.

At the first bad boundary `(100,366)` the master record is SUBEVENT. The next
boundary `(101,365)` is also SUBEVENT. At ordinal 37,255 the master has EVENT
`(102,365)`, followed by SOURCES3 `(102,365)` at master line 542114.
Climate has advanced to January 1/year 103, making the requested key `(103,365)`.
This predicts the exact SOURCES3 guard failure. The last completed watershed
`ebe_pw0.txt` date is December 31/year 102.

## EOF exposure

Hillslope output has two records beyond the climate input. Their precipitation
is 7.10 and 5.90 mm, matching December 22/23 of year 200 from the preceding
climate buffer. `stmget.for:121` reads ten records at a time and branches on EOF
to line 132 without tracking how many new records were loaded. Saved array
slots can therefore be consumed after input exhaustion. Calendar correction
removes the extra requests in this case; explicit complete-record/EOF validation
is still necessary for robust handling of short climate input.

## CLIGEN and proposed repair

The provided CLIGEN checkout is clean at
`8b9619b68c78f52d3bac778be19dc8436cac7d51`. Both it and the vendored binary's
provenance source `f7f337b026dc2eee18e098a3c5de72cd0c601a2e` use the Gregorian
continuous-generation rule at `cligen532/cligen.f:3776–3779`. The input file
agrees with that rule. No CLIGEN continuous-calendar correction is indicated.

[Repair design](repair-design.md) specifies a shared Gregorian execution calendar,
daily date checks, EOF validity tracking, explicit HBP policy compatibility,
regeneration requirements, and century-focused acceptance gates. This is a
recommendation, not an implemented fix or a recovered project.

## Reproduction and retained evidence

The supported `prepare_fork_run` helper created the full isolated project at
`/workdir/wepp-century-investigation-20261021/project-fork`; original watershed
outputs were retained separately in `original-output/`. A second execution lane
was staged from that fork with all run files and same-build hillslope PASS files.
All 534 forcing/control/context files hash identically across original and both
lanes. All climate files have one content hash. See [provenance](provenance.json).
`chntyp.txt`, despite its name, is opened for write by the watershed; it and
`chan.out`, `tc_out.txt`, `chanwb.out` are outputs, not forcing inputs.

The probe source is an archive of the exact release commit. Its only change is
[failure-only diagnostics](observation.patch) printing requested/read date keys
immediately before the existing STOP. Native checkout and released binaries were
not edited. Build used archived makefile defaults and `/usr/bin/gfortran`.
No behavioral ablation or model correction was run.

An initial local replay attempt accidentally started the probe in the baseline
working directory. Both processes were stopped, their logs retained under
`invalid-overlapping-attempt/`, and that attempt is excluded from evidence.
Both were restarted in separate directories. The live source project was never
used as an execution directory. Fresh replay comparisons are required below.

## Runtime verification result

Both full configured 200-year requests terminated with exit code 1 at the same
year-102 guard. The diagnostic printed expected `(103,365)` and master
`(102,365)`, exactly matching the independent artifact audit. All six generated watershed output files are byte-identical between the
unchanged release replay and diagnostic replay. Original-run master PASS and
plot output also match exactly. The other four original outputs have numerical
differences already in year 1 (for example March 5 sediment 39639.88 versus
39639.89). Their origin is unresolved; original numerical parity is not claimed.
All 37,254 outlet date/precipitation rows and the failure boundary match.
[Original/replay comparison](original-ebe-comparison.json) retains maximum
absolute numerical differences: 5.41 cubic meters runoff volume, 0.00006 cubic
meters per second peak flow and 1.88 kilograms sediment. These differences
precede the century boundary and are not attributed to the date defect. All 104 supplied hillslope PASS files remain unchanged in both lanes.
See [comparison](replay-comparison.json) and [comparison script](compare_replays.py).
This validates the diagnosis and observational parity, not 200-year completion.

Replay commands (working directories are material):

- `project-fork/wepp/runs`: `/workdir/wepppy/wepp_runner/bin/wepp_261010 < pw0.run`
- `probe/runs`: `/workdir/wepp-century-investigation-20261021/release-source/src/wepp < pw0.run`

Both directories are under `/workdir/wepp-century-investigation-20261021`;
stdout/stderr are retained as `release-stdout.txt`, `release-stderr.txt`,
`probe-stdout.txt`, `probe-stderr.txt` there. Package Markdown lint passes.
The next delivery must implement the calendar/reader correction, validate the
full regenerated project and complete normal release gates before recovery.
