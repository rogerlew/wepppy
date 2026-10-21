# Proposed repair: one Gregorian execution calendar

Status: design recommendation, not implemented or released. User requested a
robust fix identification on 2026-10-21 and supplied `/workdir/jimf-cligen532`.

## Required behavior

Continuous simulations must consume exactly one climate record for each actual
Gregorian calendar date, and hillslope/PASS/watershed/output dates must describe
that same date. Leap years are divisible by 4, except centuries not divisible by
400. This applies to stochastic years beginning at 1 and observed calendar years.
Missing, duplicate, out-of-order or invalid daily dates must fail explicitly,
with expected/actual dates and input path, before advancing physical state.

Rationale: this is already the continuous CLIGEN calendar and the calendar in the
reported project's climate. Adding synthetic February 29 weather, repeating a
record, suppressing the SOURCES3 guard, or relabeling PASS records cannot restore
correct physical evolution, management timing, monthly or annual accounting.
Do not change CLIGEN's continuous generator to reproduce WEPP's legacy mistake.

## Implementation boundary

Use one shared WEPP calendar routine for leap status, days in month/year and
calendar-to-Julian conversion. Wire it into `contin`, `wshdrv`, `wshpas`, and
`stmget`, replacing the legacy centurial override in execution loops and PASS
combining. Current native files are `contin.for`, `wshdrv.f90`, `wshpas.f90`, and
`stmget.for`; release 261010 uses `.for` for all four. Keep requested loop date
separate from input date so reading a record cannot silently overwrite the value
against which it must be checked. Audit management/month-end/year-end consumers
of these counters; fixed capacity 366 and climatological lookup tables are not
by themselves evidence that an array or formula should be changed.

Make climate chunk reads track how many complete records were actually read.
Current `stmget` jumps to consumption on EOF during its ten-record read and has
no valid-record count. A final partial block must supply only its valid rows;
additional requested days must fail, never reuse saved buffer entries. Apply
corresponding explicit EOF handling to breakpoint climate without changing the
single-storm contract.

Validate every hillslope PASS header date against the independently computed
expected date during combining, and every master header during routing, including
SUBEVENT and NO EVENT. Continue validating SOURCES3/SRC3 dates. Validate matching
coverage across hillslopes. Keep the date guard; improve its diagnostics.

## Compatibility and recovery

Existing ASCII v3 files do not declare a calendar policy. Retain the format;
validate their date sequence against the chosen Gregorian execution calendar and
reject incompatible century records with a regeneration instruction. Do not
skip or rename an extra record: it contains physical state advanced under the
wrong schedule. Before a release, document compatibility in authoritative native
contracts and release metadata, and add an ADR for the calendar-policy change.

The modern HBP writer, adapter and reader currently declare
`wepp-gregorian-legacy-centurial-v1`. Introduce a distinct Gregorian policy ID and
propagate it through writer, adapter, reader, manifests and runtime compatibility
checks. Preserve old IDs' meaning and offline readability; reject an old-policy
shard when executing a Gregorian run. Do not silently reinterpret existing
schema-1/schema-2 data, and do not change the prior exact-date selection fix.
A calendar policy ID already exists, so a binary layout/schema-major change is
not automatically necessary; confirm this with serialization compatibility tests.

For chemotherapeutic-scope, retain the existing valid climate but regenerate all
104 hillslopes, master PASS, watershed outputs and downstream interchange/reports
with the corrected paired binaries. Rerunning only the watershed with old
hillslope PASS files is not recovery. Keep the failed original run as evidence.

## Acceptance gates

Cover ordinary years and leap years; synthetic boundaries 99–101, 199–201,
299–301 and 399–401; real 1899–1901 and 1999–2001. Require exactly 73,048
climate/hillslope/master daily records for years 1–200 and 146,097 for 1–400.
Use a small generated 400-year case to exercise all century rules, plus the full
200-year actual project. Include malformed dates and premature EOF at every
position in a ten-record climate block. Do not accept success banners alone.

Require date-keyed precipitation and flux readback across climate, daily water
balance, hillslope PASS, master PASS, watershed event output and downstream
interchange. In particular, independently compare December/January transitions;
post-century water balance currently combines the climate year with model Julian
day. Require unchanged outputs for unaffected non-century cases and parity up
to the first changed calendar boundary for this run. Test ASCII and both binary
schema paths, observation off/on parity, and existing native release gates.

CLIGEN source commit `8b9619b68c78f52d3bac778be19dc8436cac7d51` and vendored
provenance source `f7f337b026dc2eee18e098a3c5de72cd0c601a2e` both use Gregorian
continuous generation in `cligen532/cligen.f:3776`. Add calendar integration
fixtures using generated CLIGEN data. The separate options 4/7 `nt` expressions
near line 3761 deserve an independent single-storm audit; they do not explain
this continuous 200-year failure and should not be silently changed here.
