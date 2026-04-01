# VPAT 2.5Rev INT: WEPPcloud

## Name Of Product/Version

- Product name: WEPPcloud
- Product version: repository snapshot `bb0fbb1cb`

## Report Date

- March 31, 2026

## Product Description

WEPPcloud is a web application for watershed-scale erosion modeling, wildfire response analytics, run management, reporting, and geospatial preprocessing built on the WEPPcloud stack.

## Contact Information

- Vendor / maintainer: University of Idaho / WEPPcloud project
- Accessibility contact: Roger Lew, `rogerlew@uidaho.edu`

## Notes

- This report is scoped to the WEPPcloud web application and public support pages under the WEPPcloud application for the frozen snapshot `bb0fbb1cb`.
- Out of scope: third-party sites linked from WEPPcloud, external video platforms, hardware, non-product institutional websites, and non-web document formats not yet added to the evidence boundary.
- Optional user-selectable sensory-preference themes remain visible as supplemental personalization features for some users, but they are outside the conformance set. The conformance baseline for WEPPcloud is the AA-validated theme set, and the default/reset path returns users to an AA-validated theme.
- The manual evidence boundary for this report is the documented local browser / operating system / assistive-technology matrix in `manual-at-pass-20260331.md` rather than a separate spoken screen-reader matrix.
- This artifact was transferred from the frozen worksheet in `acr-draft-int.md` using the official `VPAT 2.5Rev INT (April 2025)` structure.

## Evaluation Methods Used

The evaluation reflected in this report used:

- `pytest` route and template accessibility assertions
- `Jest` controller accessibility assertions
- Playwright `axe` smoke scans on representative public and authenticated pages
- Playwright rendered contrast measurements for the theme set
- manual keyboard, zoom/reflow, focus-visibility, and live-region checks required by the repo release checklist
- the documented March 31, 2026 core-flow manual pass recorded in `manual-at-pass-20260331.md`
- source inspection of the public accessibility statement and theme-labeling implementation

The frozen local browser / operating system / assistive-technology matrix for this report is:

- Operating system: Ubuntu 24.04.4 LTS
- Primary evaluated browser / engine: Chromium 141.0.7390.37 via Playwright
- Additional installed browsers recorded: Google Chrome 146.0.7680.75 and Mozilla Firefox 149.0
- Installed assistive technology recorded: Orca 46.1
- Authenticated browser validation method: local server-side session cookie minted from the `weppcloud` container for browser import

## Applicable Standards/Guidelines

This report covers:

- WCAG 2.0 Level A and AA
- WCAG 2.1 Level A and AA
- WCAG 2.2 Level A and AA
- Revised Section 508 standards
- EN 301 549 Accessibility requirements for ICT products and services V3.1.1 and V3.2.1

## Terms

The terms used in the Conformance Level information are defined as follows:

- `Supports`: The functionality of the product has at least one method that meets the criterion without known defects in the evaluated scope.
- `Partially Supports`: Some functionality of the product does not fully meet the criterion, is not yet fully verified, or has known limitations in the evaluated scope.
- `Does Not Support`: The functionality of the product does not meet the criterion in a material way.
- `Not Applicable`: The criterion is not relevant to the evaluated scope of the product.

## WCAG 2.x Report

### Table 1: Success Criteria, Level A

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content | Supports | Tested templates and UI surfaces use accessible names, labels, and alt text in evaluated flows. Additional product-wide manual verification remains advisable for future issues. |
| 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | The evaluated WEPPcloud scope does not rely on prerecorded audio-only or video-only content for core operation. External video platforms are out of scope. |
| 1.2.2 Captions (Prerecorded) | Not Applicable | The evaluated product scope does not include prerecorded video required for core product operation. |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | The evaluated product scope does not include prerecorded video required for core product operation. |
| 1.3.1 Info and Relationships | Partially Supports | Semantic structure is covered by route tests, `axe` scans, and template review on representative surfaces. The evaluated evidence is representative rather than exhaustive across the full product. |
| 1.3.2 Meaningful Sequence | Supports | No known reading-order defects were found in evaluated landing, usersum, and tested controller/report surfaces. |
| 1.3.3 Sensory Characteristics | Partially Supports | No known critical defect is documented in current evidence, but a full product-wide review of instruction text has not yet been completed. |
| 1.3.4 Orientation | Supports | The evaluated web application does not impose a known orientation lock on major flows. |
| 1.3.5 Identify Input Purpose | Partially Supports | Core controls use labels and names, but a complete audit of semantic input-purpose and autocomplete coverage has not yet been completed. |
| 1.4.1 Use of Color | Partially Supports | No known critical color-only dependency is documented in evaluated flows, but the product-wide audit is incomplete. User-selectable themes are provided for personalization and sensory accommodation; conformance for this criterion is evaluated against the AA-validated theme set rather than optional themes outside the conformance baseline. |
| 1.4.2 Audio Control | Not Applicable | No autoplay audio was identified in the evaluated product scope. |
| 2.1.1 Keyboard | Partially Supports | Keyboard behavior is covered in controller tests and manual checklist items for core flows, but not yet exhaustively across the entire product. |
| 2.1.2 No Keyboard Trap | Partially Supports | No known keyboard traps are documented in the tested flows, but a complete product-wide manual sweep is still pending. |
| 2.1.4 Character Key Shortcuts | Supports | No known single-character shortcut dependency is required for product operation. |
| 2.2.1 Timing Adjustable | Partially Supports | No known core workflow relies on inaccessible timed interaction, but auth/session timeout behavior has not yet been fully documented in the evidence package. |
| 2.2.2 Pause, Stop, Hide | Partially Supports | No known critical defect is documented, but dynamic and status surfaces need fuller manual confirmation in a later issue. |
| 2.3.1 Three Flashes or Below Threshold | Supports | No known flashing content beyond the threshold is part of the evaluated product flows. |
| 2.4.1 Bypass Blocks | Partially Supports | Representative pages use headings, regions, and structured navigation, but a full inventory is not yet documented. |
| 2.4.2 Page Titled | Supports | Evaluated templates and pages provide titles. |
| 2.4.4 Link Purpose (In Context) | Partially Supports | Link text is generally descriptive in evaluated pages, but a full product-wide review is still required. |
| 2.5.1 Pointer Gestures | Supports | No known essential path-based or multipoint gesture is required to operate evaluated product functionality. |
| 2.5.2 Pointer Cancellation | Partially Supports | No known defect is documented, but pointer event behavior has not yet been formally audited across all custom controls. |
| 2.5.3 Label in Name | Partially Supports | Accessible-name coverage is tested for representative controls and modals, but a complete inventory is still pending. |
| 2.5.4 Motion Actuation | Supports | Motion actuation is not required for evaluated product use. |
| 3.1.1 Language of Page | Supports | Route tests cover document language metadata. |
| 3.2.1 On Focus | Supports | No known change-of-context-on-focus defect is documented in evaluated flows. |
| 3.2.2 On Input | Partially Supports | No known critical defect is documented, but dynamic control surfaces should be fully confirmed in a later issue. |
| 3.2.6 Consistent Help | Partially Supports | The evaluated scope exposes consistent global help and contact affordances on representative surfaces, but a complete product-wide inventory of repeated help mechanisms has not yet been frozen. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 3.3.1 Error Identification | Partially Supports | Form labeling is covered in representative surfaces, but complete error-handling review across all forms remains outstanding. |
| 3.3.2 Labels or Instructions | Partially Supports | Tested flows use labels and instructions, but the full form set has not yet been exhaustively audited. |
| 3.3.7 Redundant Entry | Partially Supports | No known critical redundant-entry defect is documented in the evaluated flows, but repeat-data handling has not yet been explicitly audited across all authenticated workflows. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 4.1.1 Parsing | Supports | For Revised Section 508, EN 301 549, WCAG 2.0, and WCAG 2.1 mappings, the official template treats this row as `Supports` based on the September 2023 W3C errata. In WCAG 2.2 the criterion is obsolete and removed. |
| 4.1.2 Name, Role, Value | Partially Supports | Controller and route tests cover representative controls and modal behavior, but a complete product-wide inventory is still needed. |

### Table 2: Success Criteria, Level AA

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| 1.2.4 Captions (Live) | Not Applicable | Live synchronized media is not part of the evaluated product scope. |
| 1.2.5 Audio Description (Prerecorded) | Not Applicable | Prerecorded video is not part of the evaluated product scope for core operation. |
| 1.4.3 Contrast (Minimum) | Partially Supports | WEPPcloud provides an AA-validated theme set that is measured and enforced through rendered contrast testing. Optional sensory-preference themes remain available as supplemental personalization features for some users with sensory hypersensitivity, but those themes are outside the conformance set and are not relied upon for this criterion. |
| 1.4.4 Resize Text | Partially Supports | Manual checklist requires 200% zoom and reflow review, but a complete final report package for every in-scope surface has not yet been assembled. |
| 1.4.5 Images of Text | Supports | No known operational dependence on images of text was identified in the evaluated product scope. |
| 1.4.10 Reflow | Partially Supports | Reflow checks are part of the manual gate, but final evaluated-release evidence has not yet been frozen for all in-scope surfaces. |
| 1.4.11 Non-text Contrast | Partially Supports | Non-text contrast is evaluated and enforced for the AA-validated theme set used for the conformance baseline. Optional sensory-preference themes remain available for user preference and sensory accommodation, but are excluded from the conformance set and should not be interpreted as part of the product's formal conformance claim. |
| 1.4.12 Text Spacing | Partially Supports | No known critical defect is documented, but a dedicated text-spacing evaluation has not yet been recorded in the evidence pack. |
| 1.4.13 Content on Hover or Focus | Partially Supports | No known critical defect is documented in evaluated flows, but hover and focus-triggered content has not yet been fully inventoried product-wide. |
| 2.4.3 Focus Order | Partially Supports | Focus order is covered in representative keyboard tests, but a complete product-wide manual audit is still required. |
| 2.4.5 Multiple Ways | Partially Supports | Multiple navigation paths exist for major product areas, but this has not yet been formally documented for all in-scope functionality. |
| 2.4.6 Headings and Labels | Supports | Evaluated pages and controls use headings and labels with meaningful text in current evidence. |
| 2.4.7 Focus Visible | Partially Supports | Focus visibility is part of the manual checklist and is covered on representative surfaces, but final release evidence is incomplete. |
| 2.4.11 Focus Not Obscured (Minimum) | Partially Supports | No known critical defect is documented in the evaluated flows, and the sampled manual pass did not reveal persistent focus obstruction on core pages. A dedicated product-wide audit for sticky headers, overlays, and responsive breakpoints has not yet been frozen. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 2.5.7 Dragging Movements | Supports | No known evaluated workflow requires dragging as the only means of operation. Where spatial interaction exists, equivalent click, tap, or form-based alternatives remain available. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 2.5.8 Target Size (Minimum) | Partially Supports | No known critical target-size defect is documented in representative flows, but a dedicated measurement pass across all interactive controls has not yet been recorded in the evidence pack. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 3.1.2 Language of Parts | Supports | No known defect is documented in current evaluated content. |
| 3.2.3 Consistent Navigation | Supports | No known inconsistency defect is documented for evaluated core navigation surfaces. |
| 3.2.4 Consistent Identification | Supports | No known inconsistency defect is documented for evaluated repeated controls. |
| 3.3.3 Error Suggestion | Partially Supports | Error suggestion coverage has not yet been fully evaluated across all forms and workflows. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | The evaluated product scope does not center on legal commitments, financial transactions, or similar irreversible submissions covered by this criterion. |
| 3.3.8 Accessible Authentication (Minimum) | Partially Supports | The evaluated product scope does not intentionally require cognitive-function tests such as memorization or transcription for core local access, but the full set of buyer-facing authentication variants and recovery flows has not yet been frozen in the evidence boundary. This is a WCAG 2.2-only row and does not map to Revised Section 508 or EN 301 549. |
| 4.1.3 Status Messages | Partially Supports | Live-region requirements exist in the controller contract and manual checklist, but the product-wide status-message inventory is not yet complete. |

### Table 3: Success Criteria, Level AAA

WEPPcloud is not making a Level AAA conformance claim in this report. The official `VPAT 2.5Rev INT` template includes Level AAA rows, including the WCAG 2.2-only `2.4.13 Focus Appearance`, but those rows are outside the scope of this A/AA report.

## Revised Section 508 Report

This report uses chapter-level summary rows for Revised Section 508 because WEPPcloud is a web-delivered software/service product and the official template permits summary treatment when the methodology is clear.

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| Chapter 3: Functional Performance Criteria | Partially Supports | Current web and keyboard evidence indicates meaningful support for users without vision, with limited vision, without color perception, with limited manipulation, and with limited cognition/language support on representative flows. WEPPcloud's conformance baseline is the AA-validated theme set; optional sensory-preference themes are supplemental personalization features and are excluded from the formal conformance set. |
| Chapter 4: Hardware | Not Applicable | WEPPcloud is a web-delivered software/service product and does not provide hardware. |
| Chapter 5: Software | Partially Supports | Current testing and source review support a preliminary web/software conformance claim, but several criteria still rely on representative rather than exhaustive evidence. WEPPcloud supports an AA-validated default theme set as the conformance baseline; additional sensory-preference themes are available as optional personalization features for some users but are excluded from the formal conformance set. |
| Chapter 6: Support Documentation and Services | Partially Supports | Public accessibility statement and usersum documentation now exist, but support-document accessibility and service-process accessibility are not yet fully evaluated and documented. Buyer-facing documentation should identify the AA-validated themes used for the conformance baseline and distinguish them from optional sensory-preference themes offered as supplemental user controls. |

## EN 301 549 Report

This report uses clause-level summary rows for EN 301 549. Clause 9 cross-references the WCAG 2.x tables above, consistent with the official template instructions.

| Criteria | Conformance Level | Remarks and Explanations |
| --- | --- | --- |
| Clause 4: Functional Performance Statements | Partially Supports | Current WCAG/web evidence, keyboard evidence, contrast evidence, and the manual core-flow pass support a preliminary claim for users without vision, with limited vision, without color perception, with limited manipulation, and with limited cognition/language support on representative flows. |
| Clause 5: Generic Requirements | Partially Supports | WEPPcloud is primarily an open-functionality web-delivered product, so many closed-functionality, speech-output, tactile, biometric, and hardware-adjacent rows are `Not Applicable`. Remaining applicable rows inherit support from the WCAG and software evidence summarized in this report. |
| Clause 6: ICT with Two-Way Voice Communication | Not Applicable | The evaluated WEPPcloud scope does not provide two-way voice communication, RTT, or built-in video communication services. |
| Clause 7: ICT with Video Capabilities | Not Applicable | The evaluated product scope does not provide native caption-processing or audio-description playback technology as a required product capability. Third-party video platforms are out of scope. |
| Clause 8: Hardware | Not Applicable | WEPPcloud is a web-delivered software/service product and does not provide hardware. |
| Clause 9: Web | Partially Supports | See the `WCAG 2.x Report` above, including the WCAG 2.2-only rows required by the INT template. |
| Clause 10: Non-Web Documents | Not Applicable | Non-web documents are not part of the frozen evidence boundary for this report. If buyer-facing PDF, Office, or other non-web documents are later added to scope, this clause should be re-opened and evaluated directly. |
| Clause 11: Software | Partially Supports | Current testing and source review support a preliminary software conformance position for the evaluated web application, but explicit row-by-row assistive-technology interoperability detail remains conservative in this summary-format report. |
| Clause 12: Documentation and Support Services | Partially Supports | Public accessibility statement and support-facing documentation exist, but support workflow accessibility, alternate-format handling, and support-service communication processes are not yet fully documented. |
| Clause 13: ICT Providing Relay or Emergency Service Access | Not Applicable | The evaluated WEPPcloud product scope does not provide relay services or emergency-service access functionality. |

## Legal Disclaimer

This report is based on the evaluated WEPPcloud snapshot and evidence boundary described above. Future changes to product scope, user interface behavior, authentication flows, theme posture, support documentation, or the evaluation environment may require this report to be updated before a later production deployment or buyer issue.
