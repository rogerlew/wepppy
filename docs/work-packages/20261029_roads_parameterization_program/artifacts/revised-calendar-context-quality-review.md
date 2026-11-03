# Independent review: sensitivity reader calendar context

Reviewer: `/root/harness_quality`, 2026-11-03. Scope is the maintained study helper
and its real-filesystem regression, plus retained generated recovery metadata.
No production model/parser, calendar tolerance, parameter or default changes.

## Confirmed defect and producer/consumer boundary

The generated study replaced `wepp/roads/runs/p1.cli` with the retained years 1–16
climate, while its temporary fixture preparation left ancestor `climate/site.cli`
using years 2000–2015. Native execution consumed the former; owned interchange
readers discovered the latter. The exact generated native outputs still matched
all seven retained r7 outputs, but readback mapped an event date differently.
This is a study runtime-context defect, not evidence of a native numerical defect.
Original failed roots and their outputs remain retained.

The Python reader discovers the nearest ancestor `climate` directory. Its helper
reuses `wepp_cli.parquet` when present, so checking text CLI identity alone cannot
exclude a stale cache. The owned native `wepp_interchange/src/calendar.rs`
`load_cli_calendar` consumes year, month and day-of-month columns; direct comparison
of those complete rows with the actual CLI calendar proves the relevant cache
semantics without weakening native parser contracts.

## Correction review

The proposed `validate_calendar_context` checks the actual discovered directory,
rejects unexpected nearer climate contexts and aliases, requires exactly the
expected text CLI with native input identity, and reads the actual selected Parquet
calendar. It compares every consumed date with the complete native CLI calendar.
This guard runs before native execution and before summary interchange. No stale
cache is silently replaced or accepted. Valid parser-produced calendar caches
remain usable. Final declared-input binding and focused tests are recorded below.

## Recovery metadata

Independently checked declaration v4 SHA256
`31a69f8200264d8064f4be3c08d26fee72f1f4901698f4c2326b0ad933978d7b`:
its predecessor hash matches v3; all 47 context/arm/final-record identities are
unchanged. All seven generated native input inventories remain byte-identical.
Each recovered `climate/site.cli` exactly matches its consumed `p1.cli` and the
declared native hash. The declaration retains 40 template outcomes and one exact
native generated history, and authorizes six remaining native calls. These are
metadata/input checks, not independent scientific acceptance of later outcomes.

The earlier abbreviated-LOSS reader correction is appropriately limited to the
canonical fixture lane, whose deck did not request yearly LOSS text. Daily and
yearly PASS/WAT calendar checks remain required; no missing native years are
waived by accepting the already-emitted mean LOSS summary. Retained generated
LOSS parsing continues to require its yearly summaries.

## Validation and verdict

**Accept the bounded calendar-context conformance repair.** The final guard binds
the actual native CLI to its prepared receipt before both execution and summary,
so changing both text files together cannot bypass declared input identity.
Independent command `wctl run-pytest tests/roads/test_roads_sensitivity.py
tests/roads/test_roads_contracts.py -q --maxfail=1` passed all **21 tests** in
10.69 seconds; log `/tmp/roads-calendar-guard-quality-tests.log`. The real-filesystem
regression rejects mismatched text, stale cached dates, nearer ancestor context
and paired text drift, and accepts the valid parser-produced cache. No native
model calls are needed to demonstrate this preflight behavior.

The broad suite started on the earlier helper revision; its result must not
silently certify this late guard. These final focused checks are separate. No
unresolved medium/high correctness or QA finding remains in this bounded repair.

Final frozen source bindings:

- `tests/roads/roads_sensitivity.py`: `1f2ee6564fa5e01a63dde1503b120a483943b9a759fd29ac778dcc7b26354246`.
- `tests/roads/test_roads_sensitivity.py`: `1ae7e36579948c79c8b7d938900b30e0dc47158b6a421f7c41de4211634919db`.
