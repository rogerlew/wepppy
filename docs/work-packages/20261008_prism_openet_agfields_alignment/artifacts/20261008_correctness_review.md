# PRISM downstream correctness review

Reviewer: `/root/prism_contract_review_a`, independent read-only review,
2026-10-09 UTC. Base/contract checkpoint: `18076eaa9` on master, before code edits.
Canonical authority: `docs/schemas/prism-downstream-eligibility-contract.md`.
Outcome: PASS for eligibility implementation; no high/medium findings.

## State and input evidence

| State/input | Evidence | Result |
| --- | --- | --- |
| Valid mode16, spatial0/1/2, calendar bounds | OpenET validator regressions | Pass |
| Missing/reversed/malformed bounds, unsupported mode | OpenET negative regressions; existing AgFields negatives | Pass |
| Existing supported modes | AgFields parameterized readiness regression | Pass |
| Optional outputs absent | Real isolated OpenET acquisition reaches API; AgFields parent false | Pass |
| Parent files populated | Actual readiness reports parent true; abstraction remains independently false | Pass |
| Missing crop year | Actual schedule validator rejects Crop2020 omission | Pass |
| Unauthorized caller | Existing focused route/access tests; no changed grants/auth | Pass |

## Artifact evidence chain

The source project's actual historic PRISM Climate controller supplies 2019–2021
bounds. Both archived spatial methods supply the parent CLI/soil/slope files.
The unmocked subfield writer generates relative CLI references; actual native
WEPP output has matching precipitation and 1,096 dates. Six actual readiness
probes exercise separate gates. Source project and feature grants are unchanged.

Production OpenET reaches the upstream API, which rejects its credential (401).
The direct API's separate successful samples establish monthly alignment only.
No new filesystem/persistence/security boundary was changed by the two entries.
The maintained exception allowlist line references were shifted without changing
existing broad-catch behavior.

## Completion limits

Eligibility is implemented and locally/environment validated at the controller,
artifact and native-model boundaries. Full AgFields UI readiness was not claimed
(the scratch watershed abstraction is absent). Production Climate Engine
acquisition remains blocked; direct-provider success cannot close it. Final
monthly alignment evidence was produced after this review and is recorded in
`results.md`, `alignment.json` and `monthly-alignment.csv`.

## Independent final artifact audit

`/root/prism_contract_review_b`, 2026-10-09 UTC: PASS, no findings. A separate
read-only container probe verified all six direct requests (monthly ET, mm,
polygon mean, v2.1), 216 unique raw monthly values and their exact copies into
432 comparison rows. All six archived parent daily series have 1,096 dates,
finite Ep/Es/Er and correct month lengths. Independently recomputed monthly ET
matches the CSV within 1e-9. AgFields parent references, CLI hashes and output
water-balance hashes verify. Three zero ET observations originate in the provider
responses rather than missing-value filling. The production Climate Engine401
limitation remains explicit.
