# Resolve whole-soil retention and capacity representation

This living ExecPlan follows docs/prompt_templates/codex_exec_plans.md. Starting
WEPPpy checkpoint d3adee2bf; native source-free checkpoint2f35f0d6c. User “proceed”
authorizes the capacity/retention contract following accepted flux ownership.

## Purpose and scope

Determine whether the SSURGO source-to-file retention transformation preserves
its stated water basis, and specify the native consumer constraints that a
replacement must meet. Establish a reproducible audit rather than promote an
unreviewed capacity multiplier. A bounded negative result is useful: dimensional
mismatch can be proven while a physical replacement remains unvalidated.

## Progress

- [x] Read preceding findings, representation contract and exact adapter/native source.
- [x] M1: retain official source definitions, declare finite source/control panel and review design.
- [x] M2: execute actual SSURGO preparation/serialization audit and separate arithmetic/domain controls.
- [x] M3: derive durable source/consumer contract, independently review results and implications.
- [x] M4: preservation, archive, scoped validation and reviewed checkpoint.

## Context and Orientation

SSURGO Horizon in wepppy/soils/ssurgo/ssurgo.py derives mass rock fraction from
fraggt10_r,frag3to10_r and sieveno10_r. Its preferred retention branch divides
wthirdbar_r/100 and wfifteenbar_r/100 by1-min(50,rock_percent)/100. Invalid
pairs can switch to Rosetta, and serialization changes precision. Native SCON
converts mass using fine-earth density to CPM (fine-earth volume share), then
multiplies input retention by CPM and applies further guards. These operations
must be distinguished, not collapsed into an inferred universal physical error.

Official NRCS metadata defines retention as whole-soil volumetric percentage,
large fragments and sieve fractions by weight, and chfrags volume separately.
Retain primary-source URLs, acquisition identity and relevant definitions before
conclusions. Published metadata does not establish field truth or porous-fragment
storage. Do not assume source density equals the later native density.

Native UL, FC, DRFC, HK and ice references must share explicit bases. A previous
source/scalar counterexample establishes that ordered dry/field/saturation does
not ensure UL-DRFC is nonzero. Accepted flux work shows selected reset residuals
are inherited references and does not justify changing reset logic.

## Plan of Work

M1 retains official NRCS definitions and inspects actual source expressions.
Acquire only four already admitted development mapunits1718465,1718494,1856573,
2711184 with explicit query/response receipts; preserve nulls and original row
identities. No withheld materials or full-panel scan. If source access fails,
retain failure and use clearly labeled synthetic controls, not invented records.
Declare a finite mass/density/retention panel before deriving numerical results.
Independent reviewers check basis and implementation; they do not implement.

M2 calls the actual Horizon and serializer in the supported local container with
no mocks, producing disposable source/prepared/emitted artifacts. Preserve every
eligible and excluded row plus fallback decisions; no unsupported missing-value
completion. Separately compute declared exact mass-volume inverse, existing
capped-mass transformation and native CPM-only projection. This is a diagnostic,
not a native run or candidate output. Retain rounding and native density/cap
conditions. Exercise source/missing/duplicate/basis/fallback/precision controls.
If full artifact construction needs unrelated material selection, use complete
synthetic source contexts and label that boundary; real Horizon output alone is
not complete native execution.

M3 writes docs/schemas/whole-soil-water-capacity-contract.md as an evidence and
change-admission contract. Specify source basis, unavailable values, native
conversion/air/dry coordinates, constitutive domains, overflow ownership and
scope limits. Link the existing rock contract. Do not change runtime formulas,
thresholds, defaults or fallbacks; such changes require their own ADR and native
validation. Derive an explicit next candidate decision from audited evidence.

M4 independently reviews actual prepared artifacts and arithmetic, preserves all
source/previous evidence, archives only after writers clear and verifies every
member/inventory. Run scoped docs lint and meaningful audit controls. No native
build/run is planned and no production code changes justify an application suite.
Commit a source-free checkpoint on the existing branch; preserve unrelated dirty
SSURGO documentation and generated docs_index.json. Do not alter closed packages.

## Validation and Acceptance

Read prepared and emitted values directly, compare against actual source fields
and inspect branch notes. Evaluate the existing heuristic and hypothetical
volume inverse separately, including zero rock, mass50cap, high rock/native85cap,
finite densities and unavailable density/retention. No arithmetic ratio can
establish a new retention law or annual response. Record units, roundoff and
source-specific limitations. Require independent scientific and execution review.

## Concrete Steps and Recovery

Work from /home/workdir/wepppy with python -B; public helpers under this package's
artifacts and private evidence under out/whole-soil-retention-20261101. Fresh
exclusive destinations; never write caches into old roots. Use wctl exec -T
weppcloud /opt/venv/bin/python -B for actual builder execution. Exact commands,
source hashes and records are retained in declarations/receipts before use.
No new dependency, branch, native source distribution, model run or deployment.

## Surprises & Discoveries

The adapter uses a capped mass complement to reverse whole-soil volumetric
retention, while native rock correction uses density-derived volume. Their
composition can vary with density and cap branch; direction cannot be assumed.

The actual source panel contains incomplete/organic horizons: all exclusions are
retained. Rosetta has no installed distribution metadata; all50loaded source/model
files were hashed and copied, with runtime versions captured additively. The
projection receipt key naming source/native density equality is imprecise; the
findings explicitly correct it to hypothetical native=emitted rounded density.

## Decision Log

2026-11-01: quantify the retained heuristic and admission contract before changing
it. The selected frozen-water explanation is complete and is not a reason to
expand that campaign. Source definitions and emitted artifacts are the next
missing evidence. Separate surface cover remains outside this bounded phase.

2026-11-01: actual audit confirms the capped-mass inverse and volume correction
do not generally cancel. Admit only a separately declared prototype/native
consumer experiment next; no production multiplier or inverse promoted. Durable
rationale and admission rules are in docs/schemas/whole-soil-water-capacity-contract.md.

## Outcomes & Retrospective

72 actual Horizon attempts completed: 60 emitted files/120 rows, six explicit
construction failures and six serialization exclusions. Independent readback and
science reviews pass. Five corrupted-record controls and three algebraic domain
controls pass. Production behavior remains unchanged. All5802prior evidence files are unchanged;
all272new archive members independently hash-verified. Raw root is frozen.
Archive SHA256 bda16b066e560379c0cd8b9e8bdb445792dc7808103bbd2cd36709b68c5adc23.
Scoped documentation lint passed. No production change required application tests.
