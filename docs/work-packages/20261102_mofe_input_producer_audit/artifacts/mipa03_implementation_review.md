# MIPA-03 independent implementation correctness review

Reviewer: `mipa03_contract_correctness`, 2026-11-03 UTC.
Scope: final working source and focused native regression review, before release gates.
Disposition: **PASS for reviewed source and focused tests; R1–R4 source findings closed**.
No remaining source correctness blocker was found. Final integration evidence remains
outside this approval, as detailed below.
No release or deployment approval is implied.

## Findings and closure

### R1 — High: specialized state leaked from hillslope simulation into routing

Initial `src/main.for` switched `ivers` from 2 to 3 after a combined run's
hillslopes without clearing `rap_state.cc_run`. Only `CONTIN` called `rap_mode`.
`WSHDRV` subsequently calls `INFILE`, `INIT1`, `SOIL`, `WATBAL` and `DECOMP` for
channels, so it could use the last hillslope's RAP mode/cover/fire state and apply
specialized physics to routing. This contradicted the contract's routing boundary
and could address the current-hill cover allocation with channel indices.

Source closure verified: `main.for` now imports `rap_mode` and calls it immediately
inside `if (ivers.eq.3)`, before watershed file/input/initialization and `WSHDRV`.
`rap_mode(3,...)` clears `cc_run`. Retain a regression exercising the transition
from newly simulated hillslopes into routing, in addition to fresh existing-pass
routing; testing only the latter would not reproduce this state leak.

### R2 — Medium: ordinary GROW actual argument changed from OFE slot to array

Initial new branches in `src/ptgrp.for` and `src/range.for` passed `idecom` where
the old calls passed `idecom(iplane)`. Both GROW routines declare scalar IDECOM;
the whole-array actual aliases the first element. IDECOM is currently inactive
in those routines, so this review does not attribute measured output changes to
it, but it violated the ordinary-call preservation requirement and changed the
declared parameter ownership.

Source closure verified: both ordinary and specialized calls now pass
`idecom(iplane)` in PTGRP/RANGE. PTGRA correctly retains its scalar actual.

### R3 — Medium: two extra canopy-growth state resets departed from reference

The initial PTGRP patch reset `ccmxfr` in the inner high-temperature JDSTOP block
and the freeze block. The bound reference only adds PTGRP resets at outer JDSTOP
and planting; the other reset owners are INITGR and inactive GROW. Adding resets
at convenient neighboring `ncount=0` sites was not a faithful reference port.

Source closure verified: the two extra resets were removed. Only the outer
JDSTOP/planting additions remain in PTGRP. Retain source/dynamic regression
coverage of the actual reset schedule, not a check that resets merely exist.

### R4 — Medium: cover parsing introduces binary32 double rounding

The initial `src/rap_state.f90:numeric_row` read cover tokens as `real64`;
`rap_read` then stored `real(row)` into the single-precision bands. The reference reads tokens
directly into REAL. This can change accepted input values despite unchanged
formula text. A system-gfortran reproduction with the legal token
`1.000000059604644775390626` yields:

```text
direct REAL bits:       3F800001 = 1.0000001192092896
REAL64 then REAL bits:  3F800000 = 1.0000000000000000
```

Evidence: `/tmp/mipa03-review-rounding-nySJ/probe.f90` and its compiled executable.
The contract admits numeric tokens up to 128 characters; this 26-character token
is not malformed. Keep wide parsing for validation/calendar/date as needed, but
parse each cover token directly into the actual REAL storage representation.
Add this discriminating case to the actual-reader regression. The current BAND
observer also prints the real64 input row, not stored native REAL arrays; emit
the final stored representation when claiming read-state observation.

Closure verified: `numeric_row` now parses each cover token directly into optional
REAL `stored` output, after wide validation. `rap_read` assigns those values to all
six bands and prints the same stored values in BAND observation. The new actual
reader test `test_cover_reads_directly_to_reference_real_precision` uses the token
above, requires upward rounding, and checks observer equality. It passed in the
independent focused test run below.

## Reviewed semantics and remaining validation

The isolated `grow_rap.for` differs from bound reference GROW in its routine name,
module state import, unreachable non-RAP CO2 and nested annual branch removal,
explicit failure before the unchanged canopy logarithm domain violation, and
opt-in observer output. Reachable reference growth, root, canopy, LAI and fire
arithmetic otherwise remain intact in the inspected source. Ordinary GROW is
unchanged. All three callers have RAP-only dispatch. The explicit domain failure
does not insert a clamp, epsilon or alternate successful result. This honors the
user's instruction to preserve reference science under Anurag's ownership.

The 9005 soil header/restrictive changes are bounded; INFPAR keeps the selected
ordinary block and inserts reference 9005 arithmetic plus layer feedback. Both
the existing saturated `avsat` cap and extra .99 scaling remain. The residue
burn-down block uses the reference exact-date/classes/multipliers. INITGR and
cutting LAI are gated to RAP; `ccmxfr` COMMON storage exists before INITGR.
Clean full compilation remains mandatory after COMMON layout changes.

WEPPpy date normalization preserves established formats and saved text. Year-key
normalization restores previous-year fallback for hydrated strings and rejects
duplicate calendars. The three activation/date files use visible retirement,
exclusive temporary replacement and regular-file checks. The previous concern
about unguarded `.cov` publication is closed in source: both RAP cover writers now
use `cover_output`, which checks regular destinations, retains interrupted writes,
and publishes through the same retirement helper. Publication tests cover linked
sources, modes, symlink rejection and injected failures; this reviewer inspected
those tests but did not independently execute the WEPPpy suite.

Independent native execution on the reviewed working source:

```text
PATH=/usr/bin:/bin:$PATH pytest -q tests/test_specialized_rap_reader.py \
  tests/test_specialized_rap_growth.py tests/test_specialized_rap_hydraulics.py
320 passed in 12.36s
```

The suites compile actual native routines privately, with runtime checks, and
compare growth/hydraulic/residue/initialization behavior against retained reference
source fixtures. The complete log is `/tmp/mipa03_correctness_final_pytest.log`.
The reader driver also verifies `rap_mode(3,1)` clears an already active RAP mode.
That is component-level transition evidence: actual combined `main` version2→3
execution remains a release validation requirement, because deleting its call
would not fail the component assertion. The eight daily/hourly history passes
reported by the parent are integration evidence owned by their retained receipts,
not independently rerun for this review.

Reviewed source identities (SHA-256):

| File in selected native checkout | SHA-256 |
| --- | --- |
| `src/rap_state.f90` | `d95df340f1588fc9b218bd654cf5367709693e9d3d21f93ee1fb38dab5968272` |
| `src/grow_rap.for` | `4e2df23576623f4b1a8591dc672ce476fdcf8ad55afd80971c04486780089bda` |
| `src/main.for` | `b40d40fefd2dd9302aeb53dc5dc1ed0809718f9c0e7db99440bd97c5c57e9446` |
| `tests/test_specialized_rap_reader.py` | `3ab576d271cfa2b4b2a00f7800391f9a37dacf79c99ba947e0a343ad60e7c27f` |

This review did not run make or mutate production files. Release approval still
requires clean builds, complete configured-fork execution, archive restoration,
ordinary controls, final binary/source binding and required gates. Security review
remains independent. Source changes after these identities require corresponding
review renewal; passing focused tests does not authorize a scientific revision.
