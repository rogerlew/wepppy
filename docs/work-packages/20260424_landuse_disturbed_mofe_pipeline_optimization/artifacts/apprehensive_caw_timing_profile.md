# Timing Profile: `apprehensive-caw / disturbed9002-10-mofe`

## Scope and evidence
- Run root analyzed: `/wc1/runs/ap/apprehensive-caw/`
- Primary logs analyzed: `landuse.log`, `disturbed.log`, `rq.log`
- Code paths correlated: `wepppy/nodb/core/landuse.py`, `wepppy/nodb/mods/disturbed/disturbed.py`
- Raw parsed data: `apprehensive_caw_timing_raw.json`

## Stage timeline (from logs)

### Cycle 1 (00:00:43-00:38:58)

| Stage | Start | End | Duration | Evidence |
|---|---:|---:|---:|---|
| Landuse build kickoff | 00:00:45 | 00:00:56 | 11s | `landuse.log:3-5` |
| MOFE assignment prep | 00:00:56 | 00:00:58 | 2s | `landuse.log:5-7` |
| MOFE management synth submit -> first completion | 00:00:58 | 00:01:11 | 13s | `landuse.log:7-10` |
| MOFE management synth submit -> last completion | 00:00:58 | 00:01:12 | 14s | `landuse.log:7`, `landuse.log:4901` |
| Disturbed remap landuse | 00:01:12 | 00:01:17 | 5s (`4.65s` logged) | `disturbed.log:7-13` |
| LANDUSE_BUILD_COMPLETE burst span | 00:01:17 | 00:06:40 | 323s | `disturbed.log:12`, `disturbed.log:20-21` |
| Disturbed SOILS_BUILD_COMPLETE -> modify_mofe_soils total | 00:38:04 | 00:38:58 | 54s (`53.57s` logged) | `disturbed.log:23-26`, `disturbed.log:19773` |
| Disturbed soil generation tasks (171) completion burst | 00:38:24 | 00:38:31 | 7s | `disturbed.log:4924`, `disturbed.log:5094` |
| MOFE soil file writes (4892 hillslopes) | 00:38:32 | 00:38:48 | 16s | `disturbed.log:5097`, `disturbed.log:19770` |

### Cycle 2 (05:08:38-05:15:03)

| Stage | Start | End | Duration | Evidence |
|---|---:|---:|---:|---|
| Landuse build kickoff | 05:08:40 | 05:08:50 | 10s | `landuse.log:24327-24329` |
| MOFE assignment prep | 05:08:50 | 05:08:51 | 1s | `landuse.log:24329-24330` |
| MOFE management synth submit -> first completion | 05:08:51 | 05:09:05 | 14s | `landuse.log:24331-24334` |
| MOFE management synth submit -> last completion | 05:08:51 | 05:09:06 | 15s | `landuse.log:24331`, `landuse.log:29225` |
| Disturbed remap landuse | 05:09:06 | 05:09:11 | 5s (`5.17s` logged) | `disturbed.log:19777-19783` |
| LANDUSE_BUILD_COMPLETE burst span | 05:09:11 | 05:15:03 | 352s | `disturbed.log:19782`, `disturbed.log:19790-19791` |

## High-signal quantitative facts
- `landuse.log` lines: `48,649`; `disturbed.log` lines: `19,791`; `rq.log` lines: `22`.
- Two full MOFE management synth passes are present: `9,784` completion lines total (`2 x 4,892`).
- Disturbed MOFE soil generation built `171` unique disturbed soils, then wrote `4,892` hillslope MOFE soil files.
- Remap windows are extremely log-heavy: each 5-second remap window has about `10k` `landuse.log` lines, including `4,892` `topaz_id` lines and `4,815` `burning` lines.
- No `[WARN]` or `[ERROR]` records were found in the three primary logs for this run window.

## Sequence-point evidence snippets

```text
landuse.log:7-10
00:00:58 Submitting MOFE management synthesis tasks to ProcessPoolExecutor
00:01:03 Waiting ... (pending=4, 5.0s)
00:01:08 Waiting ... (pending=4, 10.0s)
00:01:11 (1/4892) Completed MOFE management synthesis ...
```

```text
disturbed.log:7-21
00:01:12 disturbed.on(LANDUSE_DOMLC_COMPLETE)
00:01:17 disturbed.on(LANDUSE_BUILD_COMPLETE)
00:06:39 disturbed.on(LANDUSE_BUILD_COMPLETE)
00:06:40 disturbed.on(LANDUSE_BUILD_COMPLETE)
```

```text
disturbed.log:4920-4924 and 5094-5097
00:38:06 Submitting MOFE disturbed soil tasks ...
00:38:21 Waiting ... (pending=171, 15.0s)
00:38:24 (1/171) Completed MOFE disturbed soil build ...
00:38:31 (171/171) Completed MOFE disturbed soil build ...
00:38:32 (1/4892) Generated MOFE soil file ...
```

## Diagnostics vs optimization
- Diagnostics: no explicit warnings/errors or failures in these logs.
- Optimization-relevant behavior: repeated `LANDUSE_BUILD_COMPLETE` bursts, multi-minute spans between repeated completion events, and very high INFO-volume inside remap loops.
