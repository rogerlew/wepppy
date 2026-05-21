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

**WEPPcloud Enables Basin-Scale Runoff and Sediment Science for I-CREWS Energy-Water Decisions**

### Author and Affiliation

Roger Lew, Department of Design and Environments, University of Idaho
Platform: https://wepp.cloud

### Abstract (target <250 words)

- Purpose: quantify basin-scale controls on runoff and sediment export in the St. Joe Basin and connect those outputs to downstream flow and energy questions in I-CREWS.
- Methods: prepare full-basin inputs in WEPPcloud (terrain, channels, hillslopes, soils, landuse, climate), run full-basin WEPP simulations, and iterate through hypothesis-driven scenario comparison.
- Key result: the St. Joe basin is prepared at operational scale (56 tributary watersheds, 134,033 hillslopes, 151,121 channel segments across about 411,000 hectares), and the end-to-end WEPPcloud modeling workflow is operational.
- Scientific implication: WEPPcloud now provides a reproducible pathway to test how disturbance, treatment, and climate assumptions propagate from hillslopes to channels to basin outlets.

### Background

St. Joe Basin modeling was added to I-CREWS scope in collaboration with the Coeur d'Alene Tribe. The basin is materially larger than prior project domains and creates a new opportunity to test process-based runoff and sediment hypotheses at watershed-network scale. WEPPcloud provides a common modeling environment for this science workflow across researchers, partners, and sites.

### Research Question

How do disturbance, treatment, and climate assumptions change runoff and sediment pathways across the full St. Joe Basin, and how can those modeled responses inform downstream I-CREWS flow and energy analyses?

### Methods

- Delineated St. Joe tributary watersheds and generated hillslope/channel topology using the WEPPcloud terrain-processing workflow.
- Built model inputs in-platform (soils, landuse, climate, disturbance context) using WEPPcloud preprocessing controls.
- Executed full-basin WEPP simulations with asynchronous worker queues and run-level reporting.
- Designed an iterative calibration loop (observe outputs -> adjust parameters -> rerun basin -> compare outcomes).
- Framed cross-site reproducibility around consistent data preparation, run settings, and output comparison across scenarios.

### Results (current status)

- Basin preparation complete: 56 watersheds, 134,033 hillslopes, 151,121 channels, ~411,000 ha.
- WEPPcloud workflow readiness: end-to-end basin setup and execution path is operational.
- Science product availability: spatial annual soil-loss outputs are now generated and reviewable in WEPPcloud GL Dashboard.
- Modeling implication: full-basin runs make upstream-to-downstream coupling explicit and support basin-scale hypothesis testing.
- Operational note: additional dedicated compute (pending procurement) is expected to shorten iteration cycles for calibration and scenario ensembles.

### Discussion

- Science takeaway: process-based runoff and sediment analysis is now operational at St. Joe basin scale, enabling testable hypotheses on disturbance, connectivity, and climate controls on watershed export.
- Why full-basin runs matter: upstream parameter changes propagate through downstream routing, so tributary-only tuning cannot resolve basin outlet behavior.
- Near-term science priority: calibrate modeled hydro-sediment responses against observations and then evaluate alternative-futures scenario contrasts.
- I-CREWS transfer value: other sites can apply the same workflow to delineate basin topology, run consistent scenarios, compare alternatives, and connect watershed outputs to downstream water-quality and energy modeling.

### Conclusion (bulleted takeaways)

- WEPPcloud now supports St. Joe modeling at full basin extent.
- The workflow supports science-first hypothesis testing of runoff and sediment pathways across hillslope, channel, and basin scales.
- St. Joe outputs provide a basin-scale evidence layer for downstream flow and energy modeling.
- A shared WEPPcloud deployment can support coordinated scenario science for all I-CREWS sites and participants.
- A common WEPPcloud workflow enables cross-site comparison of alternative-futures science across I-CREWS basins.
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
- "WEPPcloud Platform Topology Supporting Basin-Scale Science"
- "Modeled Annual Soil Loss in WEPPcloud GL Dashboard"

## 4) Layout Blueprint (36 x 48 landscape)

- Header band (full width): title, author/affiliation, logos.
- Column 1: abstract + background + research question + basin map.
- Column 2: methods + WEPPcloud Platform Topology diagram.
- Column 3: results + discussion + conclusions + GL Dashboard annual soil-loss figure.
- Footer band: NSF acknowledgment, contact, and explicit platform URL `https://wepp.cloud` (plus optional QR code to `https://wepp.cloud`).

## 5) Presenter Notes (for consistency with current status)

- Lead with the science questions (runoff/sediment controls and downstream implications), then use infrastructure only as enabling context.
- Present modeled annual soil-loss patterns as basin-scale scientific outputs and identify calibration as the next validation step.
- If discussed, describe capacity figures as planning estimates and keep them secondary to scientific interpretation.
