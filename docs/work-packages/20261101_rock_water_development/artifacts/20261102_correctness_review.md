# Rock/water correctness and user-experience review

## Metadata

Reviewer: `/root/s01_implementation`, 2026-11-02. Package:
`docs/work-packages/20261101_rock_water_development/`. Native source:
`d2e14d96af5942409c9a315dc8594fcc164a702a`; canonical optional integration:
`41c8b53cfe93f9657a0ce53f602e3e134b48d172`.

This independent review covers S01 preparation, actual consumers, boundary inputs,
raw outputs and final scientific reporting. Earlier unchanged implementation and
security evidence is reused within its original scope; it is not represented as
newly rerun. Broad regression, final PDF/sidecar delivery, archival completeness,
public selection and commits have separate final delivery gates.

Authority is the [whole-soil contract](../../../schemas/whole-soil-water-capacity-contract.md#known-native-coefficient-ownership-defect),
[ADR-0132](../../../adrs/ADR-0132-optional-ssurgo-retention-builder.md), and the
existing program plan. Related security evidence includes the
[installed-controller outcome](P04-installed-controller-actual-security-review-v2.md).
Security approval does not substitute for this correctness gate.

## User outcome and failure-class coverage

Users need generated soils and model outputs to preserve the selected retention
policy and each OFE's own physical coefficients. Existing optional artifact
production and source lineage remain boundedly validated. A successful model
process or finite output does not establish correct coefficient ownership.

The broken assumption is that layer-only FC/HK arrays remain valid while the
consumer changes OFE. Four direct native histories establish that both policies
consume OFE 3 coefficients on OFEs 1/2. Each policy has 15 dynamic FC slots and
15 executed unsaturated HK slots; 10 in each set differ from that OFE's initialized
bits. Exact seven-file plain/observer parity holds for each policy. This is a
confirmed consumer defect, not a measured repaired-model hydrograph error.

Shared declarations, full PURK/PERC consumers and daily/hourly initialization
blocks are unchanged across revision 4, program ancestors and final source.
Twenty Git blobs were independently verified against the science lineage receipt.
The pattern therefore predates revision 5; changed supply/phase histories can
still change exposure and consequences. Daily, general watershed and lateral/
drainage source peers remain implicated by shared storage, but the new dynamic
witness is the declared hourly hillslope experiment. No class-wide repair or
exhaustive environmental coverage is claimed. The [S01 coverage matrix](S01-final-disposition.md#coverage-and-explicit-limits)
retains unexecuted scheduled tillage and other excluded branches.

## Valid-state and error-policy matrix

| State or input | Required behavior and observed boundary | Evidence/status |
| --- | --- | --- |
| Ordinary unmarked soil; option absent | Preserve default processing and formula | Existing P04 integration admission reused; no default migration |
| Valid opt-in source and complete companions | Preserve source/row identity through actual writer, treatment, stack and staging | Installed controller reproduces 66 soils/companions, 193 OFEs; actual S01 boundary chains independently parsed |
| Marked soil with absent, empty, malformed or mismatched companion | Explicit contract error; no silent downgrade to ordinary handling | Existing ADR-0132 validation/security evidence reused; no new error behavior introduced |
| Existing opt-in destination or stale treatment | Reject overwrite/reuse according to freshness contract | Existing integration evidence reused; no destructive retry |
| Mixed or all-Rosetta source; above-cap optional exclusion | Preserve excluded material with recorded reason | Actual synthetic builders and native fallback identity pass; no invented inverse for excluded rows |
| Heterogeneous initialized coefficients | Each consumer needs its own OFE coefficient | **Fails: confirmed wrong-owner FC/HK; successful exit does not surface or resolve it** |
| Failed research attempt | Preserve partial files, explicit failure receipt and hashes; fresh version for correction | Earlier preparation/runtime failures retained; no implicit native retries |

Filesystem state and material/policy combinations are separate dimensions. This
matrix does not claim every malformed-input case or every user environment was
newly exercised. No new UI or persisted policy setting was introduced by S01.

## Generated artifact evidence chain

| Stage | Direct evidence | Result and limit |
| --- | --- | --- |
| Intent | Exact reviewed default/optional declarations, three-OFE materials and finite boundary packs | Bound before execution |
| Reloaded persistence | S01 has no NoDb/persisted-setting mutation | N/A for this investigation; prior controller artifact admission remains separate |
| Intermediate artifacts | 22 actual synthetic-source builder soils; canonical optional companion readback; eight treated/stacked decks | Independent parser/lineage verification passes |
| Executable input | Exact H11 nonsoil bytes and actual consumed soil hashes; native INPUT/remap/SCON readback | Pass for declared inputs; emitted and native support distinguished |
| Execution output | Four ownership histories plus 16 boundary histories; all ordinary files, calendars, initialization/domain traces and consumer bits reread | Observation/parity pass; coefficient correctness fails |
| User-facing explanation | Exact S01 final report/JSON reviewed against raw evidence | Scientific report passes; final release PDF and local delivery remain separate gates |

The boundary audit independently checked 112 ordinary output files, eight exact
plain/observer pairs, 24 OFE profiles and 144 native layers. Actual support is
1000 mm from 700 mm source/800 mm emitted support. Density/rock caps and guard
nonactivation are observed; mixed/all-Rosetta3 policy outputs are byte-identical.
Synthetic source records are not acquired SSURGO or field-calibration evidence.

Actual configured-service application evidence is reused from the
[492-history implementation outcome](application-final-actual-implementation-review-v1.md):
3,443 artifacts, 978 changed, with configured service identity and retained
quantitative consequences. Prior native, combined, legacy, Roads and P03 admissions
remain bounded by their original receipts. The original Roads screen still fails
at 744/840. No broad-suite result can override the direct ownership witness.

## Findings and verdict

| ID | Severity | Finding | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-S01-01 | High | Heterogeneous dynamic FC and executed HK consumers use another OFE's initialized coefficients under both policies | Separately authorize a native correction, assess all confirmed shared consumers, and validate affected artifacts and consequences | **Open** |

**Correctness gate: fail. General-release recommendation: hold. Package closure:
hold. Unresolved findings: one High; zero additional Medium or Low findings in this
review's scope.** Local known-defect revision 5 artifacts and exact reviewed commits
may document the bounded work under existing authority; they cannot waive this
finding or claim unrestricted heterogeneous readiness. Native repair is outside
S01 authority. No default change, existing-project rewrite or deployment is admitted.

Independent readback receipts are retained under
`out/rock-water-development-20261101/S01-independent-implementation-closeout-v1/`:

| Receipt | SHA256 |
| --- | --- |
| `actual-ownership-review-v1.json` | `ec1114fb243da32c563c09121ca777fa8e819e1f6a7882c8b3a8364bad185ace` |
| `actual-boundary-review-v1.json` | `d1ebbe02fb714116716ab8b8f8cf82c40b824ae4685a6e349ca654a7b7593121` |
| `release-impact-recommendation-v1.json` | `1d70aca5dafe3a0ab0d5511a5cb8abf6cbe8b08f591bf294eeb773e4d208c873` |
| `final-public-report-review-v1.json` | `ef487c49d400fd60805cd7aeaa791e0a3c0055769c2f3ee7bacc6514bfee633c` |

## Artifact observability gate

Canonical soils and adjacent retention companions follow the established project
soil layout and existing authorization boundary. S01 creates private research
observations, not a new hidden project workflow. Native source, patches and raw
traces remain private under the explicit program publication boundary; this review
contains only source-free findings and receipt identities.

This technical review does not independently sign off final private archive/member
restore completeness, public selection, or browser/download delivery. Those remain
separate final delivery evidence in the parent's gate inventory. No absence of
that evidence is converted into a pass here. Failed/partial attempts remain retained;
no source deletion, project migration or new archive exclusion is authorized.
