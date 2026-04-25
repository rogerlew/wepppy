# NSF-Style Distilled Request: I-CREWS WEPPcloud Server Procurement

**Status:** Draft for internal review and Research.gov submission  
**Date:** 2026-04-24  
**Project:** I-CREWS / St. Joe Basin WEPPcloud modeling  
**Request Type (Research.gov):** Prior approval / budget modification (or `Other Request` if no exact type matches)  

## 1) Decision Summary

Request approval to procure **two dedicated compute servers** for an independent I-CREWS WEPPcloud deployment supporting St. Joe calibration and alternative-futures modeling.

- **Total request:** **$42,783.00** (`2 x $21,391.50`)
- **What this changes:** Increases project-usable compute/storage capacity for I-CREWS St. Joe work.
- **What this does not change:** Core project objectives, scientific scope, and award intent.

## 2) Why This Is Necessary Now

The St. Joe basin preparation work is complete and modeling is blocked by compute/storage capacity, not software readiness.

- Basin already delineated at scale (56 tributaries; 134,033 hillslopes; 151,121 channels).
- Full-basin calibration requires repeated whole-basin runs, not one-off tributary runs.
- Current shared infrastructure cannot provide sustained I-CREWS throughput without cross-project contention.
- Active run workload is small-file heavy; local storage is needed to avoid network-filesystem penalties.

## 3) Alternatives and Due Diligence

The team evaluated use of Lemhi/Falcon shared HPC as an alternative.

- Direct replacement of WEPPcloud persistent RQ worker architecture on shared HPC is not practical for near-term delivery.
- Key constraints include persistent queue-worker model mismatch, secure cross-boundary control-plane requirements, and small-file I/O mismatch with shared Lustre patterns.
- Estimated adaptation effort is materially larger and slower than direct procurement, with high opportunity cost against I-CREWS timelines.

Conclusion: dedicated servers are the lowest-risk path for timely I-CREWS delivery.

## 4) Federal Cost and Compliance Framing

This request is framed as a **direct I-CREWS project cost**, not as relief for unrelated WEPPcloud operations.

- **Allowability/necessity:** `2 CFR 200.403`
- **Allocability to this award:** `2 CFR 200.405(a)(1)`
- **If mixed benefit emerges during period of performance:** prospective documented allocation under `2 CFR 200.405(d)`
- **No cross-award cost shifting:** `2 CFR 200.405(c)`
- **Prior written approval / equipment treatment:** `2 CFR 200.407`, `2 CFR 200.439`, definitions in `2 CFR 200.1`
- **Post-award use, records, disposition:** `2 CFR 200.313`

## 5) Governance and Controls

If approved, operations will follow explicit controls:

- Primary use during the award period remains I-CREWS St. Joe calibration/scenario work.
- Administrative records retained for deployment assignment, run accounting, and project usage.
- If non-I-CREWS benefit becomes material during the award period, allocation method will be documented prospectively.
- Any post-award reassignment will follow sponsor/pass-through/institutional property requirements.

## 6) Outcome if Approved

Approval converts the project from compute-constrained to execution-ready:

- Dedicated I-CREWS WEPPcloud deployment for sites, participants, and partners.
- Feasible full-basin iterative calibration and alternative-futures scenario matrix runs.
- Reduced schedule risk for near-term project deliverables.

## 7) Explicit Decision Requested

Approve procurement and required prior-approval/budget-modification routing for:

- **Quantity:** 2 servers
- **Unit cost:** $21,391.50
- **Total:** $42,783.00
- **Purpose:** Direct support of I-CREWS St. Joe basin modeling scope

---

## Research.gov Narrative Paste Block (Concise)

We request prior approval and budget modification authority (as applicable under award terms) to procure two compute servers totaling $42,783.00 ($21,391.50 each) for an independent I-CREWS WEPPcloud deployment dedicated during the award period to St. Joe basin calibration, alternative-futures scenario modeling, and access by I-CREWS sites, participants, and partners.

This request reflects a direct project need. The St. Joe basin is already delineated and ready to model; work is currently constrained by compute and storage throughput rather than software readiness. The proposed servers provide dedicated project capacity and local storage needed for WEPPcloud's small-file, metadata-heavy execution profile during full-basin iterative calibration cycles.

We evaluated shared HPC alternatives (Lemhi/Falcon) and documented due diligence. For this near-term award scope, adapting WEPPcloud's persistent queue-worker architecture to shared HPC operating constraints is not a practical delivery path and would introduce substantial schedule and implementation risk compared to direct procurement.

This cost is framed as award-specific under 2 CFR 200.403 and 200.405(a)(1). If mixed benefit becomes material during the period of performance, we will document and apply prospective allocation under 2 CFR 200.405(d). We will follow prior-approval and equipment requirements under 2 CFR 200.407 and 200.439, and maintain post-award property/use records consistent with 2 CFR 200.313 and award terms.

No change is requested to core scientific objectives; this action enables execution of the approved I-CREWS modeling scope.

## Suggested Attachments for the Request Packet

1. `procurement-request.md` (full technical/regulatory justification and quote)
2. `weppcloud-architecture-overview.md` (architecture and workflow constraints)
3. `lemhi-rq-workers.md` (alternative-path due diligence and risk/time/cost analysis)
4. Vendor quote and institution-required procurement forms

