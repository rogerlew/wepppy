# AGENTS.md
> Local agent guide for `docs/projects/i-crews/2026_annual_meeting`.

## Authorship
**This document is maintained by GitHub Copilot / Codex agents. Agents may revise this file when needed to improve execution quality for this directory.**

## Scope
- Applies to files in this directory and its subdirectories.
- Current focus: I-CREWS annual meeting poster planning and assets.

## Primary Objective
- Produce a scientifically rigorous, visually clear poster package for I-CREWS.
- Keep infrastructure content as enabling context, not the central scientific claim.

## Canonical Inputs
- Poster requirements: `ICREWS_Poster_Guidelines.pdf`
- Working poster spec: `WEPPcloud_ICREWS_poster_spec.md`
- Key figures:
  - `figures/st_joe_watersheds.png`
  - `figures/gl-dashboard.png`
  - platform topology diagram (ASCII source currently embedded in poster planning discussions)
- Scientific/project context (outside this directory):
  - `../st_joe/*.md`
  - `../../../wepppy/weppcloud/routes/usersum/weppcloud/*.md`

## Content Directives
- Science-first framing:
  - Lead with hydrologic/sediment science questions, methods, and findings.
  - Treat compute/deployment details as secondary implementation context.
- Accuracy and evidence:
  - Do not invent metrics, counts, or performance claims.
  - Mark projected or provisioning values as estimates.
  - Keep procurement status explicit when relevant.
- Audience fit:
  - This is an I-CREWS audience; highlight transferability to other I-CREWS sites.
  - Keep copy concise and legible for poster-read distance.

## Mandatory Poster Constraints
- Poster size: `36" x 48"` landscape.
- Recommended total text: `<750 words`.
- Include required sections per guideline document.
- Include exact NSF acknowledgment text:
  - "This material is based upon work supported by the National Science Foundation under EPSCoR Award #OIA2242769."
- Include logos required by conference guidance.
- Use `https://wepp.cloud` (do not downgrade to `http`).

## Figure and Asset Rules
- Prefer print-suitable sources:
  - vector (`.eps`) or high-resolution raster for logos.
- Preserve provenance when adding assets:
  - record source URL in commit message or nearby doc note.
- Do not silently replace existing figure files with different content.
- Keep file names stable once referenced in poster spec unless a rename is intentional and all references are updated.

## Writing Quality Controls
- Avoid long paragraph blocks; prefer scannable bullets.
- Prefer result-oriented figure titles and section headers.
- Remove repetitive or generic phrasing often seen in AI-generated text.
- Keep claims concrete, testable, and tied to model outputs.

## Validation Before Handoff
From `/home/workdir/wepppy`:
- `wctl doc-lint --path docs/projects/i-crews/2026_annual_meeting/WEPPcloud_ICREWS_poster_spec.md`
- Verify title length and section word budget if content changed materially.
- Confirm all referenced local figure paths exist.

## Out of Scope
- Do not treat this directory as the source of truth for WEPPcloud production architecture.
- Do not modify unrelated repository files when working poster tasks.
