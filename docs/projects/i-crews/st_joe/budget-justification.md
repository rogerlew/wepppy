# Budget Justification — Dedicated WEPPcloud Deployment for I-CREWS

**Date:** May 2026
**Project:** I-CREWS / St. Joe River Basin Watershed Modeling
**Total Request:** $42,783 (two servers at $21,391.50 each)

---

## What We Are Asking For

Funds to procure two dedicated compute servers for a new, I-CREWS-only deployment of WEPPcloud. The deployment will support watershed modeling of the St. Joe River Basin and provide a shared, priority-access modeling environment for other I-CREWS sites, participants, and partners.

## Why This Request Was Not in the Original Proposal

When the I-CREWS proposal was written, the technical capability to model the St. Joe River Basin at the scale required did not yet exist. The WEPPcloud team has since built that capability. The St. Joe River Basin has already been delineated end-to-end: 56 tributary watersheds covering roughly 411,000 hectares. The data is ready; the modeling is waiting on compute capacity.

WEPPcloud is a mature, operationally proven platform (Technology Readiness Level 9 — actively deployed and used in production by federal agencies, state agencies, researchers, and educators). What this request funds is not new software development. It is the dedicated hardware needed to run a production-grade WEPPcloud instance for I-CREWS without competing for  resources with the existing public service.

## Why the St. Joe Basin

The Coeur d'Alene Tribe — an I-CREWS partner — proposed the St. Joe Basin as the candidate watershed for modeling. The basin has unique downstream value for the I-CREWS program:

- The Tribe maintains a Coeur d'Alene Lake water-quality model. WEPPcloud streamflow and sediment outputs from the St. Joe Basin can feed directly into that lake model.
- Coeur d'Alene Lake drains to the Spokane River, which supports hydroelectric generation downstream. Linking WEPPcloud outputs through the lake model creates an end-to-end pathway from forest-and-watershed land management decisions through lake water quality to hydropower and downstream water supply.
- This enables alternative-futures scenario modeling — comparing how forest management, wildfire, climate change, and restoration treatments propagate downstream to water quality, streamflow, and energy production as proposed.

Hosting this work on Lemhi — The high-performance computing (HPC) cluster — was evaluated as an alternative to dedicated hardware and determined to be non-viable. WEPPcloud is an always-on web platform, not a batch-scheduled HPC job; the adaptation effort and storage limitations of the HPC environment make it the wrong fit. The detailed technical and feasibility analysis is available.

## How This Fits I-CREWS Goals

WEPPcloud is a flexible geospatial compute platform. It links site-specific geospatial assets — terrain, soils, climate, land cover, fire — to physically based hydrologic and erosion models, and exposes the results through a browser interface, an API, and an analytics layer. The platform is designed to be extended with new modeling capabilities and to integrate with other models. Coupling WEPPcloud outputs to downstream energy and water-resource models is a stated I-CREWS objective.

A dedicated I-CREWS deployment also makes the platform directly useful to the rest of the I-CREWS program. Other I-CREWS sites, participants, and partners will have a public web interface with priority access for collaborative modeling, training, and scenario work.

## Federal Cost Basis

This request is structured as a direct, award-specific cost to I-CREWS under the Uniform Guidance ([2 CFR Part 200](https://www.ecfr.gov/current/title-2/part-200)):

- **Necessary and reasonable** ([2 CFR § 200.403](https://www.ecfr.gov/current/title-2/section-200.403)). The full-basin St. Joe scope was added at the request of the Coeur d'Alene Tribe, an I-CREWS partner, and is blocked on compute and storage capacity rather than software readiness. The dedicated deployment is necessary to execute the approved project work.
- **Allocable to I-CREWS** ([2 CFR § 200.405(a)(1)](https://www.ecfr.gov/current/title-2/section-200.405)). The servers will host an independent WEPPcloud deployment provisioned primarily for St. Joe calibration, alternative-futures scenario modeling, and access by I-CREWS sites, participants, and partners. The cost is not framed as relief for unrelated WEPPcloud operating demand, consistent with the cross-award charging limits in [2 CFR § 200.405(c)](https://www.ecfr.gov/current/title-2/section-200.405).
- **Equipment treatment and prior approval** ([2 CFR §§ 200.439](https://www.ecfr.gov/current/title-2/section-200.439), [200.407](https://www.ecfr.gov/current/title-2/section-200.407), [200.1](https://www.ecfr.gov/current/title-2/section-200.1)). Working classification is general-purpose equipment. Prior written approval from the awarding agency or pass-through entity will be obtained and retained in the award file, with quantity, unit cost, classification, and approved project use documented.
- **Program fit.** The request aligns with NSF EPSCoR RII Track-1 program language on research-driven physical and cyber infrastructure investments that benefit jurisdictional R&D capacity. That alignment is a supporting program-fit argument; the primary cost basis is the direct-benefit allocability case above.

The detailed compliance documentation — including the approval-package checklist and asset-classification analysis — is preserved in [procurement-request.md](procurement-request.md).

## What this Procurement Enables

- A dedicated, production-grade WEPPcloud deployment operated for the I-CREWS award period.
- Sufficient compute and storage to calibrate and run alternative-futures scenarios across the full St. Joe Basin.
- A shared, priority-access modeling environment for I-CREWS sites, participants, and partners.
- A direct pipeline from WEPP hydrology and sediment outputs into the Coeur d'Alene Tribe's lake model and, through it, to downstream Spokane River and hydropower assessments.
- A concrete deliverable on the I-CREWS goal of integrating watershed modeling with energy and water-resource models.

## Asset Lifecycle After I-CREWS

The servers are standard, containerized infrastructure. After the award period, and consistent with award terms, sponsor or pass-through instructions, institutional property controls, and any continuing Federal interest under [2 CFR § 200.313](https://www.ecfr.gov/current/title-2/section-200.313), the same equipment could be redeployed in either of two natural roles:

- As a refresh for aging WEPPcloud production hardware, extending the operational life of the broader platform.
- As general-purpose research-computing capacity within the university's research computing infrastructure (RCDS).

Either path preserves the value of the investment beyond the immediate I-CREWS scope. Reassignment is not automatic — it occurs only if the equipment is no longer needed for the original project purpose, and only through the documented post-award disposition process.

## Cost Summary

| Item | Unit Cost | Qty | Total |
|------|-----------|-----|-------|
| Dedicated compute server (Supermicro 621P-TR, fully configured) | $21,391.50 | 2 | estimated **$42,783.00** |
