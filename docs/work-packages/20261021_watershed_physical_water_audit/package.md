# Watershed physical water audit

Status: Complete (diagnostic audit, 2026-10-21); four native defects unresolved.

Address Ayush’s concerns about Dp, lateral flow, ET and Q/QOFE through the last
OFE and into watershed routing. Audit the released 261021 ASCII PASS v3 pair,
with single and multiple OFEs and daily and hourly water-balance execution.
Ash and consumer UI changes are excluded. Calendar fixes are prerequisites,
not evidence of physical conservation. Original workbook decks were not supplied.

[Completed ExecPlan](prompts/completed/audit_execplan.md) · [Tracker](tracker.md)

## Acceptance and scope

Trace actual writer/reader boundaries and retain fresh output identities. Build
volume accounting for each OFE, whole hillslope, groundwater, PASS delivery,
channel and watershed outlet. Account for internal transfers exactly once.
Quantify threshold omissions, storage changes, numerical precision and unknown
terms. Independently integrate channel discharge; a published balance identity
is insufficient. Test single, equal and unequal two-OFE, three-OFE, tributary
and cascade cases across daily/hourly modes. Report physically plausible
behavior separately from algebraic conservation and from discretization parity.

Instrument only when existing output cannot establish a boundary; require
unmodified/off/on scientific parity. No production physics corrections,
release changes, deployment or original-project mutation are part of this audit.
A demonstrated defect requires a bounded reproduction and proposed remedy.
Do not close on passing dates, tests, or one aggregate residual alone.

Complexity budget: existing native source, output readers and offline analysis;
no new runtime dependencies or infrastructure. Security impact: low; isolated
local copies and no service/auth changes. Dedicated security review not required.
Closed predecessor packages remain unchanged historical evidence.

## Outcome

[Findings](artifacts/findings.md) document four reproduced defects: channel-local
water omitted from rate routing; flat CHRQIN source volume loss; hourly
infiltration remainder discarded; initial groundwater normalized by terminal
OFE area. Eighteen 44-year watershed configurations complete; local OFE/PASS
conversion checks pass, but routed rates and published volumes disagree.
All observational comparisons pass scientific parity; five corruption controls
pass. No source fix, binary replacement or deployment was performed.

Highest claim: current-release diagnosis with reproduced failures and explicit
coverage limits. **Watershed hydrologic correctness is not certified.**
