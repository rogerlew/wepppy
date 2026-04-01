# ITI VPAT 2.5Rev INT Notes

This directory records local notes about how WEPPcloud maps into the official `VPAT 2.5Rev INT (April 2025)` template.

## Key Transfer Notes

- `docs/ui-docs/acr-draft-int.md` is the living source worksheet before transfer.
- The official INT template includes:
  - WCAG 2.x tables
  - Revised Section 508 sections
  - EN 301 549 report sections
- The template includes WCAG 2.2-only rows such as:
  - `3.2.6 Consistent Help`
  - `3.3.7 Redundant Entry`
  - `2.4.11 Focus Not Obscured (Minimum)`
  - `2.5.7 Dragging Movements`
  - `2.5.8 Target Size (Minimum)`
  - `3.3.8 Accessible Authentication (Minimum)`
- `4.1.1 Parsing` remains in the INT template because it still maps to Revised 508 and EN 301 549, even though WCAG 2.2 marks it obsolete and removed.

## WEPPcloud Posture

- Use the AA-validated theme set as the conformance baseline.
- Keep sensory-preference themes visible only as supplemental user-choice themes outside the conformance set.
- Archive issued packages only for frozen production-bound buyer issues.

