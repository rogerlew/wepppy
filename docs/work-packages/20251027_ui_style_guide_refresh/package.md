# UI Style Guide Refresh Work Package

**Package ID:** `20251027_ui_style_guide_refresh`  
**Created:** October 27, 2025  
**Status:** In Progress  
**Lead Agent:** Claude Sonnet 4.5  
**Stakeholders:** GPT-5-Codex (review), Roger Lew (developer)

---

## Objective

Merge and restructure UI documentation to enable rapid agent-driven UI construction with zero aesthetic decisions. Transform UI development from a time sink into a mechanical pattern-matching workflow.

---

## Scope

### In Scope
1. Merge `ui-style-guide-ENHANCED.md` into `ui-style-guide.md`
2. Add Pattern Catalog with 8 copy-paste templates at top of document
3. Add Quick Reference Tables, Troubleshooting, Testing Checklist
4. Integrate "Zero-Aesthetic" design philosophy
5. Generate TOC via `markdown-doc toc`
6. Solicit GPT-5-Codex review of merged document

### Out of Scope
- Modifying actual UI components or CSS
- Creating new patterns beyond the initial 8
- Implementation of agent auto-generation system
- Testing patterns against real controls

---

## Success Criteria

1. ✅ Single unified document at `docs/ui-docs/ui-style-guide.md`
2. ✅ Pattern Catalog section enables <5 minute control creation
3. ✅ Agent can match user request → pattern ID → template mechanically
4. ✅ TOC provides clear navigation structure
5. ⏳ GPT-5-Codex review validates pattern accuracy and completeness
6. ⏳ No technical errors in templates (class names, nesting, composition rules)

---

## Deliverables

1. ✅ Merged `ui-style-guide.md` (1151 lines)
   - Pattern Catalog (8 patterns)
   - Composition Rules
   - Pattern Decision Tree
   - Quick Reference Tables (5 tables)
   - Troubleshooting (7 entries)
   - Testing Checklist (11 items)
   - Original reference material (Technology Stack, Control Components, etc.)

2. ✅ TOC generated via `markdown-doc toc --update`

3. ✅ Review request prompt (`prompts/active/REVIEW_REQUEST.md`)

4. ⏳ GPT-5-Codex review feedback (pending)

5. ⏳ Revisions based on review (if needed)

---

## Background

### Problem Statement
UI development is a significant time sink for the developer. Key pain points:
- **Time cost:** Setting up new controls takes too long
- **Aesthetic decisions:** Developer doesn't want to make styling choices
- **Inconsistency risk:** Without patterns, controls drift visually
- **Agent friction:** Existing docs were reference-heavy, not action-ready

Developer quote:
> "I hate doing ui and styling. UI is a huge time suck and barrier to standing up new functionality."

### Design Philosophy Evolution
Original philosophy (GPT-5-Codex): Focus on calm utility, accessibility, Pure.css efficiency

New "Zero-Aesthetic" philosophy:
- **Goal:** Spend zero time on aesthetics, minimize layout time
- **Constraints:** Grayscale only, single light theme, token-based spacing, macro composition
- **Metrics:** <5 min per control, 0 styling decisions, <30 sec QA
- **End state:** Agent generates complete templates from text descriptions

### Existing Assets
- `ui-style-guide.md` (GPT-5-Codex) - Detailed reference, terse/dense style
- `ui-style-guide-ENHANCED.md` (Claude) - Pattern catalog, verbose examples
- `_pure_macros.html` - Jinja macros (control_shell, status_panel, button_row, etc.)
- `ui-foundation.css` - Token system, component styles

---

## Approach

### Phase 1: Document Merge ✅
**Status:** Complete  
**Outcome:** Single unified guide with pattern catalog at top, reference material below

**Actions taken:**
1. Analyzed both documents for complementary vs. redundant content
2. Decided on single-document approach to avoid meta-problem of "which doc?"
3. Inserted pattern catalog at top (lines 1-750)
4. Repositioned design philosophy with "Zero-Aesthetic" framing
5. Kept original reference material intact (lines 754+)
6. Added TOC markers and generated navigation

**Key decisions:**
- Pattern-first structure (agents see quick patterns immediately)
- Kept Codex's terse reference material (agents scroll for deep dive)
- No content removed (only reorganized and augmented)

### Phase 2: Pattern Documentation ✅
**Status:** Complete  
**Outcome:** 8 patterns with trigger words, templates, examples, composition rules

**Patterns documented:**
1. Basic Control Shell - Run workflow controls
2. Summary Pane - Read-only state display
3. Advanced Options (Collapsible) - Rarely-used settings
4. Status Panel + WebSocket - Background task streaming
5. Data Table + Pagination - Multi-page datasets
6. Form with Validation - User input with error handling
7. Status Indicators - Job/task state display
8. Console Layout - Admin dashboards/tools

**Supporting materials:**
- Pattern matching table (trigger words → pattern ID)
- Pattern decision tree (step-by-step selection logic)
- Composition rules (valid nesting, constraints, invalid combinations)
- Quick reference tables (buttons, containers, spacing, forms, WebSocket)
- Troubleshooting (7 symptom→fix entries)
- Testing checklist (11 validation items)

### Phase 3: Review & Validation ⏳
**Status:** In Progress  
**Outcome:** GPT-5-Codex validates pattern accuracy, identifies gaps

**Review request sent:** `prompts/active/REVIEW_REQUEST.md`

**Key questions:**
1. Integration quality - Does pattern catalog mesh with reference material?
2. Pattern completeness - Are there missing patterns?
3. Pattern accuracy - Do templates follow documented conventions?
4. Composition rules - Align with actual component behavior?
5. Troubleshooting - Other common failure modes?
6. Agent cognitive load - Does pattern-matching reduce overhead?
7. Tone mismatch - Do verbose patterns clash with terse reference?
8. Zero-Aesthetic philosophy - Contradict accessibility principles?

**Awaiting:** Codex feedback on technical accuracy, missing patterns, workflow improvements

### Phase 4: Refinement ⏳
**Status:** Not Started  
**Outcome:** Address review feedback, correct errors, add missing patterns

**Planned actions:**
1. Review Codex feedback thoroughly
2. Correct any technical errors (class names, nesting, composition)
3. Add missing patterns identified by Codex
4. Resolve any philosophical tensions
5. Update TOC if structure changes
6. Document changes in changelog

---

## Timeline

- **Oct 27, 2025 (morning):** Package initiated, document merge complete
- **Oct 27, 2025 (afternoon):** Pattern catalog complete, TOC generated, review request sent
- **Oct 27-28, 2025:** Awaiting Codex review
- **Oct 28-29, 2025 (estimated):** Refinement based on feedback
- **Oct 30, 2025 (target):** Package complete

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pattern templates contain errors | High - Agents replicate bad patterns | Codex review validates accuracy |
| Missing critical patterns | Medium - Agents can't handle some requests | Codex identifies gaps in review |
| Verbose patterns clash with terse reference | Low - Agents confused by tone shift | "Quick-start then deep-dive" framing |
| Zero-Aesthetic contradicts accessibility | High - Unusable UI for some users | Review ensures WCAG AA compliance maintained |
| Pattern matching too rigid | Medium - Edge cases not covered | Decision tree provides fallback logic |

---

## References

- **Main deliverable:** `/workdir/wepppy/docs/ui-docs/ui-style-guide.md`
- **Review request:** `/workdir/wepppy/docs/work-packages/20251027_ui_style_guide_refresh/prompts/active/REVIEW_REQUEST.md`
- **Original guides:**
  - `ui-style-guide.md` (GPT-5-Codex authorship)
  - `ui-style-guide-ENHANCED.md` (Claude authorship, now deleted/merged)
- **Related docs:**
  - `docs/ui-docs/control-ui-styling/control-components.md` - Macro API reference
  - `wepppy/weppcloud/templates/controls/_pure_macros.html` - Macro source
  - `wepppy/weppcloud/static/css/ui-foundation.css` - Token system

---

## Notes

### Architecture Decision: Single Document
**Decision:** Merge into single document rather than maintain separate quick-start and reference

**Rationale:**
- Avoids meta-problem: "Which doc should agent read first?"
- Natural reading order: patterns first (top), details second (scroll)
- Single source of truth, no cross-reference management
- Agent workflow becomes linear (scan → match → copy → scroll if needed)

**Trade-offs:**
- Longer document (1151 lines vs two ~500 line docs)
- Must maintain TOC to provide navigation
- Risk of agents getting lost in long document

**Mitigation:** Clear section headers, TOC navigation, "Quick Start" vs "Deep Dive" framing in header

### Pattern Catalog Philosophy
**Approach:** Mechanical pattern matching, not interpretation

**Format:**
```
User says: "Climate control with dropdown and status log"
          ↓
Agent: Scans trigger words → climate, dropdown, status log
       Matches: Pattern #1 (control), Pattern #4 (status log)
          ↓
Copy: Templates for #1 and #4
Fill: {{TITLE}} = "Climate Data", {{PANEL_ID}} = "climate-status"
          ↓
Done. Zero aesthetic decisions.
```

**Key principle:** If user says X, agent uses pattern Y. No interpretation needed.

### Authorship Attribution
**GPT-5-Codex sections:**
- Design Philosophy (original "Calm utility" principles)
- Technology Stack
- Control Components
- Tokens, Colors, Typography
- Component Guidance
- Accessibility Checklist
- Implementation Playbook
- Site-wide Assessment

**Claude Sonnet 4.5 sections:**
- Pattern Catalog (8 patterns)
- Composition Rules
- Pattern Decision Tree
- Quick Reference Tables
- Troubleshooting
- Testing Checklist
- "Zero-Aesthetic" philosophy framing

**Collaborative:** Integration and structure decisions

---

## Change Log

**2025-10-27:**
- Package created
- Documents merged into single `ui-style-guide.md`
- Pattern catalog added (8 patterns)
- Quick reference tables, troubleshooting, testing checklist added
- "Zero-Aesthetic" philosophy integrated
- TOC generated via `markdown-doc toc`
- Review request sent to GPT-5-Codex
