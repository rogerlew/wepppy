# I-CREWS 2026 Poster Spec: WEPPcloud St. Joe Basin

Date: 2026-05-21  
Prepared for: I-CREWS Annual Meeting Poster Session

## 1) Poster Requirements (from conference guidance)

- Canvas size: 36 in tall x 48 in wide (landscape).
- Recommended total poster text: less than 750 words.
- Title length target: 100 characters or fewer.
- Include: title, authors and affiliations, abstract, background, research question or hypothesis, methods, results, discussion, and conclusion.
- Required NSF acknowledgment text:
  - "This material is based upon work supported by the National Science Foundation under EPSCoR Award #OIA2242769."
- Logos to include: University of Idaho, I-CREWS, Idaho NSF EPSCoR (NSF logo optional per NSF guidance).
- Typography targets:
  - Title: 72-100 pt
  - Section headings: 36-48 pt
  - Body: 24-32 pt
- Design target: readable at 3-4 feet, visual-first composition.

## 2) Ready-to-Use Poster Content Draft

### Title (<=100 chars, includes WEPPcloud)

**WEPPcloud for I-CREWS: Basin-Scale St. Joe Modeling for Energy-Water Decisions**

### Author and Affiliation

Roger Lew, Department of Design and Environments, University of Idaho
Platform: https://wepp.cloud

### Abstract (target <250 words)

WEPPcloud is a browser-based watershed modeling platform that combines geospatial preprocessing, climate assembly, and physically based WEPP simulations into an integrated workflow for runoff and sediment analysis. For the I-CREWS St. Joe Basin effort, the full basin has been prepared at operational scale (56 tributary watersheds, 134,033 hillslopes, and 151,121 channel segments across about 411,000 hectares). This creates a new opportunity to support alternative-futures analysis that links upstream land management to downstream water and energy systems. Methods include automated delineation and parameter assembly in WEPPcloud, iterative full-basin simulation, and scenario comparison across disturbance and treatment assumptions. Results to date show the software and data pipeline are ready for basin-scale calibration, while compute and storage capacity remain the primary bottleneck. A dedicated two-server deployment has been specified to provide local-storage-backed throughput for iterative calibration and scenario production; this procurement is currently pending approval. This work supports I-CREWS goals by creating a reproducible decision-support pathway from watershed disturbance and treatment scenarios to downstream impacts relevant to lake water quality, streamflow, and hydropower planning.

### Background

St. Joe Basin modeling was added to I-CREWS scope in collaboration with the Coeur d'Alene Tribe. The scale is materially larger than prior project basins and now requires repeated full-basin simulations for calibration and scenario testing. WEPPcloud is already an operational platform used for agency, research, and management workflows; the current challenge is scaling computational throughput to match the newly prepared basin domain.

### Research Question

Can WEPPcloud support iterative, basin-scale calibration and alternative-futures scenario modeling for the St. Joe Basin in a way that is useful for I-CREWS energy-water decision support?

### Methods

- Delineated St. Joe tributary watersheds and generated hillslope/channel topology using the WEPPcloud terrain-processing workflow.
- Built model inputs in-platform (soils, landuse, climate, disturbance context) using WEPPcloud preprocessing controls.
- Executed full-basin WEPP simulations with asynchronous worker queues and run-level reporting.
- Designed an iterative calibration loop (observe outputs -> adjust parameters -> rerun basin -> compare outcomes).
- Framed deployment architecture for sustained throughput using a dedicated two-server WEPPcloud topology.

### Results (current status)

- Basin preparation complete: 56 watersheds, 134,033 hillslopes, 151,121 channels, ~411,000 ha.
- WEPPcloud workflow readiness: end-to-end basin setup and execution path is operational.
- Infrastructure bottleneck identified: shared-service compute and network storage constraints limit calibration velocity.
- Dedicated deployment specification completed:
  - Two servers, 256 total cores, 512 GB RAM, local RAID-backed storage.
  - About 3.9x raw aggregate compute vs current shared baseline.
  - About 40x project-usable provisioning estimate for I-CREWS due to dedicated allocation.
- Procurement status: server procurement request is pending approval.

### Discussion

The central science result is that basin-scale, process-based runoff and sediment analysis is now operational for St. Joe, enabling testable hypotheses about how hillslope disturbance, channel connectivity, and climate variability control watershed export. Full-basin calibration remains essential because upstream parameter changes propagate through downstream routing and alter outlet behavior; tributary-only tuning cannot capture those coupled effects. The main constraint is therefore throughput for iterative hypothesis testing, not model formulation. For I-CREWS, this creates a transferable science workflow that other project sites can use: delineate basin topology, run consistent WEPPcloud scenarios, compare alternative futures, and link watershed outputs to downstream water-quality and energy-system models.

### Conclusion (bulleted takeaways)

- WEPPcloud now supports St. Joe modeling at full basin extent.
- The workflow supports science-first hypothesis testing of runoff and sediment pathways across scales.
- The dominant blocker for calibration and scenario throughput is infrastructure capacity.
- A dedicated WEPPcloud deployment is specified, aligned with I-CREWS project needs, and available to all I-CREWS sites and participants.
- The St. Joe basin model can inform downstream flow and energy modeling through linked watershed-to-lake-to-river analyses.
- WEPPcloud (https://wepp.cloud) is positioned as a shared modeling platform for other I-CREWS sites.

### Required NSF Acknowledgment (verbatim)

"This material is based upon work supported by the National Science Foundation under EPSCoR Award #OIA2242769."

## 3) Figure and Visual Specification

Use visuals to carry the narrative and keep text concise.

- Figure 1 (left column): St. Joe Basin map image file `figures/st_joe_watersheds.png` showing proposed basin coverage and tributary structure.
- Figure 2 (center): WEPPcloud Platform Topology diagram using the provided architecture block (Human/AI operators, core stack, services, and storage buses).
- Figure 3 (right column): WEPPcloud GL Dashboard image file `figures/gl-dashboard.png` showing modeled annual soil loss outputs.

Suggested result-focused figure titles:

- "Proposed Watersheds for St. Joe Basin"
- "WEPPcloud Platform Topology"
- "Modeled Annual Soil Loss in WEPPcloud GL Dashboard"

## 4) Layout Blueprint (36 x 48 landscape)

- Header band (full width): title, author/affiliation, logos.
- Column 1: abstract + background + research question + basin map.
- Column 2: methods + WEPPcloud Platform Topology diagram.
- Column 3: results + discussion + conclusions + GL Dashboard annual soil-loss figure.
- Footer band: NSF acknowledgment, contact, and explicit platform URL `https://wepp.cloud` (plus optional QR code to `https://wepp.cloud`).

## 5) Presenter Notes (for consistency with current status)

- State clearly that infrastructure procurement is pending approval as of May 2026.
- Present capacity numbers as planning/provisioning values, not final measured post-deployment benchmarks.
- Emphasize that this poster reports workflow readiness and deployment readiness for the next modeling phase.
