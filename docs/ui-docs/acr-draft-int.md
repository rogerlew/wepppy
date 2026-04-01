# WEPPcloud ACR Draft Worksheet

This document is a **drafting worksheet** for a future formal Accessibility Conformance Report (ACR) using the official **VPAT 2.5Rev INT** template.

It is intentionally conservative. It is meant to gather product metadata, current evidence, preliminary conformance positions, and open follow-up items before the content is transferred into the official ITI template.

## Status

- Draft maturity: preliminary
- Intended final template: `VPAT 2.5Rev INT`
- Federal procurement posture: this draft is useful source material, but it is **not** the final procurement artifact
- Current repository snapshot evaluated: `bb0fbb1cb`
- Draft date: **March 31, 2026**

## Product Metadata

| Field | Draft value |
| --- | --- |
| Product name | WEPPcloud |
| Product version | Repository snapshot `bb0fbb1cb` |
| Report type | Draft ACR worksheet for later transfer into `VPAT 2.5Rev INT` |
| Product description | Web application for watershed-scale erosion modeling, wildfire response analytics, run management, reporting, and geospatial preprocessing built on the WEPPcloud stack. |
| Vendor / maintainer | University of Idaho / WEPPcloud project |
| Accessibility contact | Roger Lew, `rogerlew@uidaho.edu` |
| Primary delivery model | Web application / software as a service |
| Primary scope in this draft | Web UI, authenticated run flows, report templates, landing/interfaces pages, public support pages under the WEPPcloud application |
| Out-of-scope for this draft | Third-party sites linked from WEPPcloud, external video platforms, hardware, non-product institutional websites |

## Drafting Notes

- This worksheet currently focuses on the **Section 508-relevant web/software subset** already evidenced in the repo.
- Because the intended final artifact is `VPAT 2.5Rev INT`, the final filing should also include any **INT-only** tables and any **WCAG 2.2-only** criteria that are not fully covered here.
- This worksheet now includes draft placeholders for the `WCAG 2.2-only` A/AA criteria and a clause-level `EN 301 549` section so the later transfer into the official template is mostly structural rather than substantive.
- Where current repo evidence is incomplete, this worksheet uses conservative language and favors `Partially Supports` over unsupported claims.

## Evaluation Methods Used In This Draft

Current evidence reflected here comes from:

- `pytest` route/template accessibility assertions
- `Jest` controller accessibility assertions
- Playwright `axe` smoke scans on representative public and authenticated pages
- Playwright rendered contrast measurements for the theme set
- manual keyboard, zoom/reflow, focus-visibility, and live-region checks required by the repo's release checklist
- the documented March 31, 2026 core-flow manual pass in `docs/ui-docs/manual-at-pass-20260331.md`
- source inspection of the public accessibility statement and theme-labeling changes

Current evidence is stronger than the earlier draft placeholder. For the current buyer issue, the manual evidence boundary is the documented core-flow pass and its formal local browser / operating system / assistive-technology matrix rather than a separate procurement-ready spoken-screen-reader matrix. Before final issue, add and document:

- evaluation dates
- evaluator identity / responsible team
- explicit testing coverage boundaries and excluded workflows

The current browser / operating system / assistive-technology matrix for the documented core-flow pass is recorded in `docs/ui-docs/manual-at-pass-20260331.md`.

## Applicable Standards Planned For Final Report

The final `VPAT 2.5Rev INT` report should cover, at minimum:

- WCAG 2.1 Level A and Level AA
- Revised Section 508 Chapter 3: Functional Performance Criteria
- Revised Section 508 Chapter 5: Software
- Revised Section 508 Chapter 6: Support Documentation and Services

Hardware is not applicable to WEPPcloud.

## Conformance Terms Used In This Draft

- `Supports`: no known defect for the evaluated product scope in current evidence
- `Partially Supports`: some product functionality is not fully verified, has known limitations, or has known exceptions
- `Does Not Support`: the current product materially fails the criterion
- `Not Applicable`: the criterion is not relevant to the evaluated product scope

## Preliminary Product-Wide Limitations

- Optional **sensory-preference themes** are not part of the AA-validated conformance set and should not be claimed as conformant themes in the final ACR.
- Current repo evidence is strong for representative flows and now includes a documented core-flow manual pass with a formal local browser / operating system / assistive-technology matrix, but it is not a product-wide spoken-screen-reader audit across all workflows.
- Support documentation and support-services accessibility are only partially documented at this stage.
- A final `VPAT 2.5Rev INT` issue should be blocked until the product version, environment matrix, evaluator details, and manual AT pass are frozen for the evaluated release.

## Sensory-Preference Theme Policy

This draft takes a conservative position on optional sensory-preference themes.

- WEPPcloud's conformance claim should be limited to the AA-validated theme set.
- Optional sensory-preference themes may still be described as supplemental personalization features for users who benefit from lower visual intensity, reduced glare, calmer palettes, or different dark/light presentation.
- The supporting research is strongest for autistic users and supports user-selectable control and sensory-load reduction; it does not support claiming that low contrast itself is a better universal accessibility baseline than WCAG AA.
- For the current buyer-facing deployment posture, non-AA sensory-preference themes remain user-visible. The final ACR should state clearly that:
  - those themes are outside the conformance set
  - the default/reset path returns users to an AA-validated theme
  - theme-selector labeling distinguishes AA-validated themes from sensory-preference-only themes

Current source basis for this policy:
- AASPIRE participatory web-guidelines research supports multiple theme choices, including low-contrast, dark, and light options, while also warning that low-contrast palettes can create barriers for users with low vision.
- Qualitative autistic-adult sensory studies support reducing sensory burden through control over light intensity, color combinations, clutter, and predictability.
- Limited ADHD evidence supports the plausibility of light-sensitive user subsets outside autism, but not a general low-contrast claim.

## VPAT-Ready Sensory Theme Remark Language

The following wording is intended to be copied into the official `VPAT 2.5Rev INT` rows with only light version/scope edits.

### Product-wide limitation statement

Optional user-selectable sensory-preference themes are provided as supplemental personalization features for some users who benefit from lower visual intensity, reduced glare, or calmer color palettes. These optional themes are not relied upon for the product's conformance claim. The conformance baseline for WEPPcloud is the AA-validated theme set, and the default/reset path returns users to an AA-validated theme.

### Criterion-level wording for contrast-related rows

- For `1.4.3 Contrast (Minimum)`:
  - WEPPcloud provides an AA-validated theme set that is measured and enforced through rendered contrast testing. Optional sensory-preference themes remain available as supplemental personalization features for some users with sensory hypersensitivity, but those themes are outside the conformance set and are not relied upon for this criterion.
- For `1.4.11 Non-text Contrast`:
  - Non-text contrast is evaluated and enforced for the AA-validated theme set used for the conformance baseline. Optional sensory-preference themes remain available for user preference and sensory accommodation, but are excluded from the conformance set and should not be interpreted as part of the product's formal conformance claim.
- For `1.4.1 Use of Color`, when relevant:
  - User-selectable themes are provided for personalization and sensory accommodation. Conformance for this criterion is evaluated against the AA-validated theme set rather than against optional themes outside the conformance baseline.

### Chapter-level wording for Revised 508 rows

- For Chapter 3 / Chapter 5 rows that reference visual access or software presentation:
  - WEPPcloud supports an AA-validated default theme set as the conformance baseline. Additional sensory-preference themes are available as optional personalization features for some users but are excluded from the formal conformance set.
- For Chapter 6 rows, when support materials mention themes or personalization:
  - Product documentation identifies the AA-validated themes used for the conformance baseline and distinguishes them from optional sensory-preference themes that are offered as supplemental user controls.

## WCAG 2.x Report

This section is written as draft content that can later be transferred into the official `VPAT 2.5Rev INT` template. For the INT edition, this means:

- `WCAG 2.2-only` rows should remain in the worksheet because the INT template includes WCAG 2.2.
- `4.1.1 Parsing` remains in the template because it still maps to Revised 508 and EN 301 549, even though it is obsolete and removed in WCAG 2.2.

### Table 1: Success Criteria, Level A

| Criteria | Draft conformance | Draft remarks and explanations |
| --- | --- | --- |
| 1.1.1 Non-text Content | Supports | Tested templates and UI surfaces use accessible names, labels, and alt text in evaluated flows. Additional product-wide manual verification should still be completed before final issue. |
| 1.2.1 Audio-only and Video-only (Prerecorded) | Not Applicable | The evaluated WEPPcloud product scope does not rely on prerecorded audio-only or video-only content for core operation. External links to video platforms are out of scope. |
| 1.2.2 Captions (Prerecorded) | Not Applicable | The evaluated product scope does not include prerecorded video required for core product operation. |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) | Not Applicable | The evaluated product scope does not include prerecorded video required for core product operation. |
| 1.3.1 Info and Relationships | Partially Supports | Semantic structure is covered by route tests, axe scans, and template review on representative surfaces. A full product-wide manual audit is still required. |
| 1.3.2 Meaningful Sequence | Supports | No known reading-order defects were found in evaluated landing, usersum, and tested controller/report surfaces. |
| 1.3.3 Sensory Characteristics | Partially Supports | No known critical defect is documented in current evidence, but full product-wide review of instruction text has not yet been completed. |
| 1.3.4 Orientation | Supports | The evaluated web application does not impose a known orientation lock on major flows. |
| 1.3.5 Identify Input Purpose | Partially Supports | Core controls use labels and names, but a complete audit of semantic input-purpose/autocomplete coverage has not yet been completed. |
| 1.4.1 Use of Color | Partially Supports | No known critical color-only dependency is documented in evaluated flows, but the product-wide audit is incomplete. User-selectable themes are provided for personalization and sensory accommodation; conformance for this criterion is evaluated against the AA-validated theme set rather than optional themes outside the conformance baseline. |
| 1.4.2 Audio Control | Not Applicable | No autoplay audio was identified in the evaluated product scope. |
| 2.1.1 Keyboard | Partially Supports | Keyboard behavior is covered in controller tests and manual checklist items for core flows, but not yet exhaustively across the entire product. |
| 2.1.2 No Keyboard Trap | Partially Supports | No known keyboard traps are documented in the tested flows, but a complete product-wide manual sweep is still pending. |
| 2.1.4 Character Key Shortcuts | Supports | No known single-character shortcut dependency is required for product operation. |
| 2.2.1 Timing Adjustable | Partially Supports | No known core workflow relies on inaccessible timed interaction, but auth/session timeout behavior has not yet been fully documented in the draft ACR evidence. |
| 2.2.2 Pause, Stop, Hide | Partially Supports | No known critical defect is documented, but dynamic/status surfaces need final manual confirmation in the formal issue. |
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
| 3.2.2 On Input | Partially Supports | No known critical defect is documented, but dynamic control surfaces should be fully confirmed in the final audit. |
| 3.2.6 Consistent Help | Partially Supports | The current evaluated product scope exposes consistent global help and contact affordances on representative surfaces, but a complete product-wide inventory of repeated help mechanisms has not yet been frozen. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 3.3.1 Error Identification | Partially Supports | Form labeling is covered in representative surfaces, but complete error handling review across all forms remains outstanding. |
| 3.3.2 Labels or Instructions | Partially Supports | Tested flows use labels and instructions, but the full form set has not yet been exhaustively audited. |
| 3.3.7 Redundant Entry | Partially Supports | No known critical redundant-entry defect is documented in the evaluated flows, but repeat-data handling has not yet been explicitly audited across all authenticated workflows. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 4.1.1 Parsing | Supports | For Revised Section 508, EN 301 549, WCAG 2.0, and WCAG 2.1 mappings, the official template treats this row as `Supports` based on the September 2023 W3C errata. In WCAG 2.2 the criterion is obsolete and removed, so the final INT transfer should preserve that template note in the remarks. |
| 4.1.2 Name, Role, Value | Partially Supports | Controller and route tests cover representative controls and modal behavior, but a complete product-wide inventory is still needed. |

### Table 2: Success Criteria, Level AA

| Criteria | Draft conformance | Draft remarks and explanations |
| --- | --- | --- |
| 1.2.4 Captions (Live) | Not Applicable | Live synchronized media is not part of the evaluated product scope. |
| 1.2.5 Audio Description (Prerecorded) | Not Applicable | Prerecorded video is not part of the evaluated product scope for core operation. |
| 1.4.3 Contrast (Minimum) | Partially Supports | WEPPcloud provides an AA-validated theme set that is measured and enforced through rendered contrast testing. Optional sensory-preference themes remain available as supplemental personalization features for some users with sensory hypersensitivity, but those themes are outside the conformance set and are not relied upon for this criterion. |
| 1.4.4 Resize Text | Partially Supports | Manual checklist requires 200% zoom/reflow review, but a complete final report package has not yet been assembled. |
| 1.4.5 Images of Text | Supports | No known operational dependence on images of text was identified in the evaluated product scope. |
| 1.4.10 Reflow | Partially Supports | Reflow checks are part of the manual gate, but final evaluated-release evidence has not yet been frozen. |
| 1.4.11 Non-text Contrast | Partially Supports | Non-text contrast is evaluated and enforced for the AA-validated theme set used for the conformance baseline. Optional sensory-preference themes remain available for user preference and sensory accommodation, but are excluded from the conformance set and should not be interpreted as part of the product's formal conformance claim. |
| 1.4.12 Text Spacing | Partially Supports | No known critical defect is documented, but a dedicated text-spacing evaluation has not yet been recorded in the evidence pack. |
| 1.4.13 Content on Hover or Focus | Partially Supports | No known critical defect is documented in evaluated flows, but hover/focus-triggered content has not yet been fully inventoried product-wide. |
| 2.4.3 Focus Order | Partially Supports | Focus order is covered in representative keyboard tests, but a complete product-wide manual audit is still required. |
| 2.4.5 Multiple Ways | Partially Supports | Multiple navigation paths exist for major product areas, but this has not yet been formally documented for all in-scope functionality. |
| 2.4.6 Headings and Labels | Supports | Evaluated pages and controls use headings and labels with meaningful text in current evidence. |
| 2.4.7 Focus Visible | Partially Supports | Focus visibility is part of the manual checklist and is covered on representative surfaces, but final release evidence is incomplete. |
| 2.4.11 Focus Not Obscured (Minimum) | Partially Supports | No known critical defect is documented in the evaluated flows, and the sampled manual pass did not reveal persistent focus obstruction on core pages. A dedicated product-wide audit for sticky headers, overlays, and responsive breakpoints has not yet been frozen. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 2.5.7 Dragging Movements | Supports | No known evaluated workflow requires dragging as the only means of operation. Where spatial interaction exists, equivalent click, tap, or form-based alternatives remain available. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 2.5.8 Target Size (Minimum) | Partially Supports | No known critical target-size defect is documented in representative flows, but a dedicated measurement pass across all interactive controls has not yet been recorded in the evidence pack. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 3.1.2 Language of Parts | Supports | No known defect is documented in current evaluated content. |
| 3.2.3 Consistent Navigation | Supports | No known inconsistency defect is documented for evaluated core navigation surfaces. |
| 3.2.4 Consistent Identification | Supports | No known inconsistency defect is documented for evaluated repeated controls. |
| 3.3.3 Error Suggestion | Partially Supports | Error suggestion coverage has not yet been fully evaluated across all forms and workflows. |
| 3.3.4 Error Prevention (Legal, Financial, Data) | Not Applicable | The evaluated product scope does not center on legal commitments, financial transactions, or similar irreversible submissions covered by this criterion. |
| 3.3.8 Accessible Authentication (Minimum) | Partially Supports | The evaluated product scope does not intentionally require cognitive-function tests such as memorization or transcription for core local access, but the full set of buyer-facing authentication variants and recovery flows has not yet been frozen in the evidence boundary. This is a WCAG 2.2-only row in the INT template and does not map to Revised Section 508 or EN 301 549. |
| 4.1.3 Status Messages | Partially Supports | Live-region requirements exist in the controller contract and manual checklist, but the product-wide status-message inventory is not yet complete. |

### Table 3: Success Criteria, Level AAA

The official `VPAT 2.5Rev INT` template includes Table 3, including the WCAG 2.2-only `2.4.13 Focus Appearance` row. WEPPcloud is not making a Level AAA conformance claim in this draft. When this worksheet is transferred into the official template:

- retain Table 3 only if the buyer or filing posture requires explicit AAA statements, or
- otherwise omit or de-emphasize AAA rows consistent with the official template instructions and the intended A/AA procurement posture

If Table 3 is retained, `2.4.13 Focus Appearance` should be treated as an explicit WCAG 2.2-only AAA row outside the current product claim.

## Revised Section 508 Summary

This worksheet does not yet expand every Revised Section 508 criterion into official VPAT row form. Instead, it records the current draft position by chapter so the content can be transferred into the final template.

| Chapter | Draft conformance | Draft remarks and explanations |
| --- | --- | --- |
| Chapter 3: Functional Performance Criteria | Partially Supports | Current web and keyboard evidence indicates meaningful support for users without vision, with limited vision, without color perception, and with limited manipulation, but the final report still needs a complete manual AT matrix and documented evaluation scope. WEPPcloud's conformance baseline is the AA-validated theme set; optional sensory-preference themes are supplemental personalization features and are excluded from the formal conformance set. |
| Chapter 4: Hardware | Not Applicable | WEPPcloud is a web-delivered software/service product and does not provide hardware. |
| Chapter 5: Software | Partially Supports | Current testing and source review support a preliminary web/software conformance claim, but several criteria still rely on representative rather than exhaustive evidence. WEPPcloud supports an AA-validated default theme set as the conformance baseline; additional sensory-preference themes are available as optional personalization features for some users but are excluded from the formal conformance set. |
| Chapter 6: Support Documentation and Services | Partially Supports | Public accessibility statement and usersum documentation now exist, but support-doc accessibility and service-process accessibility are not yet fully evaluated and documented for a final ACR issue. Final buyer-facing documentation should identify the AA-validated themes used for the conformance baseline and distinguish them from optional sensory-preference themes offered as supplemental user controls. |

## EN 301 549 Report Summary

The `VPAT 2.5Rev INT` template includes a separate `EN 301 549 Report`. For WEPPcloud, the draft clause-level position is:

| Clause | Draft conformance | Draft remarks and explanations |
| --- | --- | --- |
| Clause 4: Functional Performance Statements | Partially Supports | Current WCAG/web evidence, keyboard evidence, contrast evidence, and the manual core-flow pass support a preliminary claim for users without vision, with limited vision, without color perception, with limited manipulation, and with limited cognition/language support on representative flows. The final INT transfer should align this clause with the same scope boundaries used in the WCAG and Revised 508 sections. |
| Clause 5: Generic Requirements | Partially Supports | WEPPcloud is primarily an open-functionality web-delivered product, so many closed-functionality, speech-output, tactile, biometric, and hardware-adjacent rows are expected to be `Not Applicable`. Remaining applicable rows should inherit support from the WCAG/software evidence and be expanded row-by-row in the final INT template. |
| Clause 6: ICT with Two-Way Voice Communication | Not Applicable | The evaluated WEPPcloud scope does not provide two-way voice communication, RTT, or built-in video communication services. |
| Clause 7: ICT with Video Capabilities | Not Applicable | The evaluated product scope does not provide native caption-processing or audio-description playback technology as a required product capability. Third-party video platforms are out of scope. |
| Clause 8: Hardware | Not Applicable | WEPPcloud is a web-delivered software/service product and does not provide hardware. |
| Clause 9: Web | Partially Supports | This clause should cross-reference the drafted `WCAG 2.x` tables above, including the WCAG 2.2-only rows required by the INT template. |
| Clause 10: Non-Web Documents | Not Applicable | Non-web documents are not part of the currently frozen evidence boundary for this draft worksheet. If buyer-facing PDF, Office, or other non-web documents are later added to scope, this clause should be re-opened and evaluated directly. |
| Clause 11: Software | Partially Supports | Current testing and source review support a preliminary software conformance position for the evaluated web application, but the final INT transfer still needs explicit row-by-row handling for interoperability with assistive technology, documented accessibility usage, user preferences, and any applicable authoring-tool rows. |
| Clause 12: Documentation and Support Services | Partially Supports | Public accessibility statement and support-facing documentation now exist, but support workflow accessibility, alternate-format handling, and support-service communication processes are not yet fully documented for a final INT issue. |
| Clause 13: ICT Providing Relay or Emergency Service Access | Not Applicable | The evaluated WEPPcloud product scope does not provide relay services or emergency-service access functionality. |

## Support Documentation And Services Notes

Current draft position:

- Public accessibility statement is available in product documentation.
- Users can report issues and request alternate access through a documented contact path.
- Product documentation exists in markdown-backed web pages under the WEPPcloud application.

Still needed before final issue:

- confirm accessibility of support workflows themselves
- confirm alternate-format fulfillment process
- confirm whether buyer support channels have documented relay / accommodation handling
- evaluate public documentation pages with the same rigor as primary application flows

## Open Items Before Final VPAT 2.5Rev INT Issue

1. Freeze the exact evaluated product version and deployment environment.
2. Convert this worksheet into the official ITI template and normalize wording to the template's exact required structure, including the row-by-row EN 301 549 clauses summarized here.

## Primary Evidence In Repo

- `docs/ui-docs/accessiblity.md`
- `docs/ui-docs/manual-at-pass-20260331.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/accessibility-statement.md`
- `tests/weppcloud/routes/test_pure_controls_render.py`
- `tests/weppcloud/routes/test_user_runs_admin_scope.py`
- `wepppy/weppcloud/controllers_js/__tests__/copytext.test.js`
- `wepppy/weppcloud/controllers_js/__tests__/map_gl.test.js`
- `wepppy/weppcloud/static-src/tests/smoke/theme-metrics.spec.js`
- `wepppy/weppcloud/static-src/tests/smoke/a11y/`

## External References

- https://lists.itic.org/policy/accessibility/vpat
- https://lists.itic.org/dotAsset/2434a080-87fe-4db1-815e-1e032bf7ac09.docx
- https://www.section508.gov/sell/acr/
- https://www.section508.gov/sell/how-to-create-acr-with-vpat/
- https://www.section508.gov/sell/acr-vpat-faq/
- https://www.section508.gov/test/elements-of-an-accessibility-test-report/
- https://www.itic.org/policy/accessibility/accessibility/vpat
- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/WCAG21/Understanding/
- https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6485264/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8217662/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10726197/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC4261727/
