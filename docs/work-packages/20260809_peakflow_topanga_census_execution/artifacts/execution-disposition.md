# Execution Disposition - Frozen Topanga Local Census

## Decision

**PASS for the preregistered local screening census.** Frozen plan
`b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`
and selection `2e450acbaa131c268fab70bd048480e1bc100990094071d74b432bf1579e3e3d`
produced 1,088 complete terminals, zero failed terminals, and zero stopped
terminals. The result supports only eligible mutation-trial and paired-event-row
screening prevalence. It does not adjudicate candidate mechanisms or support a
routing, channel, watershed, or downstream-impact claim.

## Frozen Population and Execution

The plan contains 1,120 requested records. Exactly 1,088 were eligible and
selected; 32 paired-cover records were excluded before outcomes because one
direction would clip. Execution used eight workers on host `forest`, observer
SHA-256 `2ec15778df957f909da383df9e3e0c9b516688d367c11f0109c6012387c0731f`,
and input snapshot
`2006d278ede4da5157e9d344863a64cef746b879106cf17b16c87d9c9a80542d`.
It ran from 2026-08-09 05:52:25 UTC through 06:06:06 UTC.

Every terminal passed hardened validation of plan, selection, snapshot, schema,
input, executable, terminal identity, return code, sole changed input, complete
mutation metadata and realization, before/after hashes, trace hash, and
hillslope-pass hash. Fourteen Ksat realized values differed from the frozen
binary float only by representation (`1.78e-15` maximum absolute delta).

## Screening Results

Immutable aggregation produced 225,654 outer-joined event rows: 225,036 paired,
320 baseline-only, and 298 mutant-only. Missing-side measurements remain null,
not zero. Frozen ADR-0042 screening identified 11,506 candidate event rows
across 1,027 of 1,088 eligible mutation trials.

The overall eligible mutation-trial screening prevalence is
`1027 / 1088 = 0.9439338235294118`. The paired-event-row screening prevalence is
`11506 / 225654 = 0.05098956809983426`. Scenario mutation-trial rates are
`516 / 546 = 0.945054945054945` for burned and
`511 / 542 = 0.9428044280442804` for undisturbed. Family rates are
`560 / 560 = 1.0` for Ksat and `467 / 528 = 0.884469696969697` for cover.
These are screened signals, not adjudicated mechanisms.

## Evidence and Reviews

The compact authority is `topanga-execution-summary.json`. External evidence is
rooted at
`/home/workdir/peakflow-topanga-census-evidence/b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`.
The version-two storage manifest inventories 24,265 retained non-lock artifacts
with locator, size, SHA-256, format, and retention policy. Repeated aggregation
produced identical ledger hashes and summary ID
`e5348e2e26adafc2fb858c0b96d8b5f7bb4dc1821e0f878f376c904a9d47f547`.

Independent scientific, code, QA, and security re-reviews all passed with no
unresolved medium or high finding. The security record explicitly preserves the
three interim HOLD/remediation cycles and GO issued before launch, plus the
procedural fact that the scaffold review file was synchronized only afterward.

## Validation Limitation

The host focused suite passed 18 tests. The canonical-container focused suite
passed 17 with one environment skip, and the Phase 2A suite passed all 5 tests.
Broad-exception enforcement and documentation lint passed. The canonical broad
suite did not pass: container `/tmp` is full. It collected 6,074 tests but failed
at setup; an alternate basetemp reached 50 passes and 13 skips before a direct
`TemporaryDirectory()` again failed with `/tmp` ENOSPC. This limitation is not
reported as a passing broad gate.

## Follow-up Boundary

Candidate adjudication, adaptive bracket/replay follow-up, cross-site
replication, and any sampled routing study require separately governed work.
Nothing in this disposition authorizes those mutations or conclusions.
