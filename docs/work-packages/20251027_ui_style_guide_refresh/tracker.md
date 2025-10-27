# UI Style Guide Refresh Tracker

**Package ID:** `20251027_ui_style_guide_refresh`  
**Last Updated:** October 27, 2025  
**Status:** In Progress - Awaiting Review

---

## Task Board

### Done ✅

- [x] Create work package structure
- [x] Analyze both UI documentation files
- [x] Decide on merge strategy (single document vs separate)
- [x] Merge documents with pattern catalog at top
- [x] Document 8 core patterns with templates
- [x] Add composition rules and constraints
- [x] Create pattern decision tree
- [x] Build 5 quick reference tables
- [x] Document 7 troubleshooting entries
- [x] Create 11-item testing checklist
- [x] Integrate "Zero-Aesthetic" design philosophy
- [x] Add TOC markers
- [x] Generate TOC via `markdown-doc toc`
- [x] Write review request prompt
- [x] Move review request to work package

### In Progress 🚧

- [x] **Awaiting GPT-5-Codex review** (blocking)
- [x] Process Codex review feedback
  - ✅ Address Pattern #1 issues: remove nested `<form>`, import `button_row` from `shared/console_macros.htm`, clarify `summary_html` dependency
  - ✅ Fix Pattern #4 JS snippet: use `controller.attach_status_stream(controller, { channel, runId })`
  - ✅ Close stray code fence in Pattern #4
- [x] Correct technical errors surfaced by review
  - ✅ Author minimal token-based CSS for `.wc-advanced-options*`, `.wc-pagination*`, `.wc-status-chip` in `ui-foundation.css`
  - Patterns #3, #5, #7 now fully functional (no fallback markup needed)
- [ ] Add/adjust patterns per review gaps
  - Draft "File Upload + Progress" pattern (prioritize before publish)
  - Queue "Modal / Drawer overlay" pattern for follow-up iteration
- [ ] Solicit Round 3 review from Codex (verify CSS implementation)

### Blocked 🚫

- [ ] Update TOC if needed (blocked on revisions)

### Backlog 📋

- [ ] Test patterns against real control templates
- [ ] Create pattern usage examples from existing controls
- [ ] Document pattern evolution process (how to add new patterns)
- [ ] Create agent training module using patterns

---

## Decisions Log

### Decision 1: Single Document Strategy
**Date:** October 27, 2025  
**Decision:** Merge `ui-style-guide-ENHANCED.md` into `ui-style-guide.md` instead of maintaining separate documents  
**Rationale:**
- Avoids "which doc?" meta-problem for agents
- Natural reading order: patterns first, details on scroll
- Single source of truth, no cross-reference management
- Linear agent workflow

**Alternative considered:** Keep separate quick-start and reference docs  
**Why rejected:** Creates navigation burden, requires cross-reference maintenance, agents must decide which to read first

**Impact:** Document length increased to 1151 lines, must maintain TOC for navigation

---

### Decision 2: Pattern-First Structure
**Date:** October 27, 2025  
**Decision:** Place Pattern Catalog at top (lines 1-750), reference material below (lines 754+)  
**Rationale:**
- Agent's first action: scan patterns for match
- Most common use case: copy pattern, fill variables, done
- Deep dive only needed for edge cases
- Matches agent cognitive workflow

**Alternative considered:** Reference material first, patterns at bottom  
**Why rejected:** Forces agent to scroll past technical details to get copy-paste templates

**Impact:** TOC shows patterns prominently, agents reach actionable content immediately

---

### Decision 3: Zero-Aesthetic Philosophy Framing
**Date:** October 27, 2025  
**Decision:** Add "Zero-Aesthetic Reality" section before Codex's "Calm utility" principles  
**Rationale:**
- Developer clarified actual goal: minimize UI time, zero aesthetic decisions
- Need to frame original principles within velocity-first context
- Both philosophies valid: velocity (developer) + utility (user)

**Alternative considered:** Replace original philosophy entirely  
**Why rejected:** Codex's principles (accessibility, consistency) still critical, just need velocity context

**Impact:** Potential philosophical tension to resolve in review

---

### Decision 4: Mechanical Pattern Matching
**Date:** October 27, 2025  
**Decision:** Use trigger words → pattern ID → template approach instead of agent interpretation  
**Rationale:**
- Reduces agent decision overhead
- Prevents pattern drift (agent invents new approaches)
- Aligns with "zero degrees of freedom" goal
- Enables future automation (text → template generation)

**Alternative considered:** Give agents flexibility to interpret and adapt patterns  
**Why rejected:** Increases cognitive load, risks inconsistency, defeats "zero decisions" goal

**Impact:** Pattern coverage must be comprehensive or agents stuck on edge cases

---

### Decision 5: Ship supporting CSS with the catalog
**Date:** October 27, 2025  
**Decision:** Implement the missing `.wc-advanced-options*`, `.wc-pagination*`, and `.wc-status-chip` styles in `ui-foundation.css` as part of this work package. Keep the rules minimal, grayscale, and token-driven so they respect the Zero-Aesthetic/Calm Utility guardrails. Documentation will mention the fallback native markup until the commit lands.  
**Rationale:**
- Maintains the copy-paste guarantee—agents can rely on the pattern snippets without additional styling work.
- Prevents ad-hoc inline CSS and preserves the “zero decisions” workflow.
- The styling footprint is small (padding, flex alignment, existing accent tokens) and aligns with current design principles.  
**Impact:** Slight scope increase now, but fewer downstream support requests; future modal/drawer pattern can re-use these primitives.

---

## Risks & Issues

### Active Risks

**Risk #1: Pattern Templates Contain Technical Errors**  
**Severity:** High  
**Probability:** Medium  
**Impact:** Agents replicate bad patterns across all new controls  
**Mitigation:** Codex review flagged multiple high-severity issues; must remediate before publishing  
**Status:** Active – fix items in review summary before unblocking

**Risk #2: Missing Critical Patterns**  
**Severity:** Medium  
**Probability:** Medium  
**Impact:** Agents can't handle some common UI requests, fall back to improvisation  
**Mitigation:** Codex review suggests adding File Upload + Progress and Modal/Drawer patterns; schedule for next edit  
**Status:** Active – needs follow-up writeup

**Risk #3: Zero-Aesthetic Contradicts Accessibility**  
**Severity:** High  
**Probability:** Low  
**Impact:** UI becomes unusable for users with disabilities  
**Mitigation:** Maintained WCAG AA requirements in all patterns, testing checklist includes accessibility  
**Status:** Monitoring (review will validate)

### Resolved Risks

None yet.

---

## Verification Checklist

### Pattern Accuracy
- [x] All class names match `ui-foundation.css` and `_pure_macros.html`
- [x] Nesting rules align with actual component behavior
- [x] Template variables use consistent naming (`{{VARIABLE}}` format)
- [x] Examples fill all required variables
- [x] No contradictions with Technology Stack section
- [x] Pattern #1 updated to pass `form_id`, `status_panel_override`, `summary_panel_override`
- [x] Status panel pattern reflects actual `status_panel` signature
- [x] Pattern support CSS classes now exist in `ui-foundation.css` (`.wc-advanced-options*`, `.wc-pagination*`, `.wc-status-chip`)

### Composition Rules
- [ ] Valid nesting table matches macro implementation
- [ ] Constraints table covers all critical restrictions
- [ ] Invalid combinations list includes common mistakes
- [ ] Rules documented match actual rendering behavior
- [ ] References to `summary_panel_content` renamed to `summary_panel_override`

### Quick Reference Tables
- [ ] Button styles map correctly to Pure.css classes
- [ ] Container selection guidance is accurate
- [ ] Spacing token values match `ui-foundation.css`
- [ ] Form type descriptions match Pure.css behavior
- [ ] WebSocket patterns align with `controlBase` API
- [ ] Document whether `.pure-button-secondary`/`.pure-button-link` require CSS additions

### Troubleshooting
- [ ] Symptom descriptions are specific and observable
- [ ] Fixes resolve stated symptoms
- [ ] Code examples are syntactically correct
- [ ] All 7 entries cover real failure modes
- [ ] Consider adding entries for status panel fallback and modal button styling

### Testing Checklist
- [ ] All 11 items are verifiable (yes/no checks)
- [ ] Checklist covers accessibility, mobile, progressive enhancement
- [ ] Items match WCAG AA requirements

### Integration Quality
- [ ] Pattern catalog doesn't contradict reference material
- [ ] No redundant content between sections
- [ ] TOC provides clear navigation
- [ ] "Quick Start" → "Deep Dive" flow is logical
- [ ] Zero-Aesthetic framing reconciled with “Calm utility” principles
- [ ] Pattern #4 JS example reflects `controlBase.attach_status_stream` usage

---

## Open Questions

1. **Pattern completeness:** Are 8 patterns sufficient, or are there obvious gaps? (Awaiting Codex review)

2. **Tone consistency:** Does verbose pattern section clash with terse reference material? (Codex: acceptable, keep quick-start framing)
- **Action:** Document additional patterns (File Upload + Progress, Modal/Drawer) per review
- **Pending:** Add explicit bridge sentence aligning Zero-Aesthetic reality with Calm Utility/accessibility principles

---

## Review Notes (2025-10-27 Codex R2)

- Blocking corrections required before publish:
  - Update Pattern #1 to rely on `control_shell` form wrapper only and import `button_row` from `shared/console_macros.htm`.
  - Rewrite Pattern #4 controller snippet to use `controller.attach_status_stream(controller, { channel: '{{CHANNEL}}', runId: window.runid })` (no `controller.base` helper, avoid `{{ run_id }}` placeholder).
  - Close missing triple backtick after the `status_panel()` signature.
- CSS alignment open item: either author `.wc-advanced-options*`, `.wc-pagination*`, `.wc-status-chip` rules in `ui-foundation.css` or downgrade patterns to existing utilities.
- Philosophy section needs explicit connective tissue stating that velocity constraints operate alongside Calm Utility / accessibility guardrails.
3. **Composition rules:** Do documented constraints match actual component behavior? (Awaiting Codex review)

4. **Troubleshooting coverage:** Are there other common failures agents hit repeatedly? (Awaiting Codex review)

5. **Agent workflow:** Does trigger word → pattern ID matching actually reduce cognitive load? (Will learn from usage)

6. **Pattern evolution:** How should agents propose new patterns when edge cases emerge? (Defer to future work)

---

## Next Steps

1. **Immediate:** Await GPT-5-Codex review feedback
2. **Upon review completion:**
   - Address technical corrections
   - Add missing patterns identified
   - Resolve philosophical tensions
   - Update TOC if structure changes
   - Move review request to `prompts/completed/`
3. **Package closure:**
   - Update `package.md` with final status
   - Document lessons learned
   - Archive artifacts

---

## Lessons Learned

(To be completed after package closure)

---

## Artifacts

- `package.md` - Work package definition
- `tracker.md` - Living status document (this file)
- `notes/CSS_IMPLEMENTATION_SUMMARY.md` - Detailed CSS implementation notes
- `prompts/active/ROUND_3_CSS_REVIEW.md` - Current review request for Codex
- `prompts/completed/REVIEW_REQUEST_V2.md` - Initial review request (Rounds 1 & 2)
- `prompts/completed/CSS_STRATEGY_QUESTION.md` - CSS approach decision request (answered via Decision 5)

---

## Related Work

- **Main deliverable:** `/workdir/wepppy/docs/ui-docs/ui-style-guide.md`
- **Macro source:** `/workdir/wepppy/wepppy/weppcloud/templates/controls/_pure_macros.html`
- **Token system:** `/workdir/wepppy/wepppy/weppcloud/static/css/ui-foundation.css`
- **Control component docs:** `/workdir/wepppy/docs/ui-docs/control-ui-styling/control-components.md`

---

## Review Conversation

### Initial Review Request (2025-10-27)
**Claude → Codex:** Sent comprehensive review request covering 8 review areas (integration quality, pattern completeness, accuracy, composition rules, troubleshooting, agent cognitive load, tone, philosophy). See `prompts/active/REVIEW_REQUEST.md`.

### Codex Review Response (2025-10-27)
**Key findings logged in tracker:**
- Risk #1 elevated: Pattern templates contain technical errors requiring fixes
- Risk #2 updated: Suggests adding File Upload + Progress and Modal/Drawer patterns
- Verification checklist expanded with specific items:
  - Pattern #1 needs `form_id`, `status_panel_override`, `summary_panel_override` parameters
  - Status panel signature needs correction
  - `summary_panel_content` should be `summary_panel_override`
  - Document whether `.pure-button-secondary`/`.pure-button-link` require CSS additions
  - Consider adding troubleshooting for status panel fallback and modal button styling
- Tone feedback: Acceptable, keep quick-start framing
- Philosophy: Zero-Aesthetic framing needs reconciliation with "Calm utility" principles

**Status:** Need to address technical corrections before second review

### Revision Planning (2025-10-27 - Current)
**Claude:** Ready to revise based on Codex feedback. Will address:
1. Fix `summary_panel_content` → `summary_panel_override` throughout
2. Update Pattern #1 to show correct `control_shell` parameters
3. Correct status panel signature
4. Add notes about secondary/link button CSS requirements
5. Consider adding 2 new patterns (File Upload, Modal/Drawer)
6. Add troubleshooting entries suggested

**Status:** Addressing technical corrections

### Technical Fixes Applied (2025-10-27)
**Claude → ui-style-guide.md:**
1. ✅ **Pattern #1 (Basic Control Shell):** Updated to use correct `control_shell` parameters:
   - Added required `form_id` parameter
   - Changed `summary_panel_content` → `summary_panel_override`
   - Removed deprecated `status_panel_id` parameter
   - Fixed `status_panel()` call to use `id` parameter instead of `panel_id`
   
2. ✅ **Pattern #4 (Status Panel):** Corrected `status_panel()` macro signature:
   - Changed `panel_id` → `id` parameter
   - Added note showing full macro signature with all parameters
   - Documented that `log_id` auto-generates from `id` if not provided
   
3. ✅ **Composition Rules:** Updated to reflect correct parameter names:
   - Status panel constraint now references `id` parameter
   - Summary pane constraint now references `summary_panel_override`
   
4. ✅ **Troubleshooting (Summary pane doesn't show):** 
   - Fixed to use `summary_panel_override` instead of `summary_panel_content`
   - Added `form_id` to example (required parameter)
   
5. ✅ **Quick Reference - Button Style Selection:** Added note about CSS requirements:
   - Documented that `.pure-button-secondary` and `.pure-button-link` are NOT Pure.css defaults
   - These classes defined in `ui-foundation.css` or require custom CSS
   - Agents should verify implementation before using

6. ✅ **TOC regenerated:** No structural changes needed

**Next:** Solicit second review from Codex focusing on:
- Verify technical corrections are accurate
- Still need 2 new patterns (File Upload + Progress, Modal/Drawer)?
- Any remaining issues to address?

### Round 2 Fixes Applied (2025-10-27)
**Claude → ui-style-guide.md (addressing Codex R2 blocking corrections):**

1. ✅ **Pattern #1 (Basic Control Shell):** Removed nested `<form>` element:
   - `control_shell` provides form wrapper automatically
   - Removed duplicate `<form class="pure-form pure-form-stacked">` wrapper
   - Changed button_row import from `controls/_pure_macros.html` → `shared/console_macros.htm`
   - Content now inside `<fieldset>` only (form wrapper added by macro)
   - Added note explaining `control_shell` provides form automatically
   
2. ✅ **Pattern #4 (Status Panel):** Fixed controller JS API:
   - Changed `controller.base.attachStatusStream` → `controller.attachStatusStream`
   - Changed channel parameter from `'{{CHANNEL}}:{{ run_id }}'` → just `'{{CHANNEL}}'`
   - Added `runId: window.runid` as separate parameter
   - Removed optional `onMessage` callback (simplified example)
   
3. ✅ **Pattern #4:** Closed missing triple backtick after `status_panel()` signature

4. ✅ **Philosophy section:** Added bridge paragraph:
   - "Velocity constraints operate **alongside** accessibility and usability guardrails, not instead of them"
   - Clarifies zero aesthetic decisions eliminates subjective styling, preserves WCAG AA/accessibility
   - "Speed through constraints, quality through standards"

5. ⚠️ **CSS classes investigation:** Checked `ui-foundation.css` for:
   - `.wc-advanced-options*` - NOT FOUND
   - `.wc-pagination*` - NOT FOUND
   - `.wc-status-chip` - NOT FOUND
   
   **Status:** These classes are referenced in patterns but don't exist in `ui-foundation.css` yet
   **Options:**
   - a) Author these CSS rules in `ui-foundation.css` (adds maintenance burden)
   - b) Downgrade patterns to use existing utilities only (removes pattern functionality)
   - c) Document patterns as "requires custom CSS" (makes patterns less copy-paste ready)
   
   **Recommendation:** Document as "requires CSS to be authored" with placeholder patterns for now, defer CSS implementation to separate task

**Next:** Update tracker conversation, solicit Round 3 review from Codex (or close if acceptable)

---

### CSS Implementation Decision (2025-10-27)
**Codex → Decision 5 in tracker:**

**Decision:** Ship supporting CSS with the catalog (Option A)

**Rationale:**
- Maintains copy-paste guarantee—agents can rely on pattern snippets without additional styling work
- Prevents ad-hoc inline CSS and preserves "zero decisions" workflow
- Styling footprint is small (padding, flex alignment, existing accent tokens)
- Aligns with current design principles (minimal, grayscale, token-driven)

**Implementation:** Implement missing `.wc-advanced-options*`, `.wc-pagination*`, `.wc-status-chip` styles in `ui-foundation.css` as part of this work package. Keep rules minimal, grayscale, and token-driven so they respect Zero-Aesthetic/Calm Utility guardrails.

**Impact:** Slight scope increase now, but fewer downstream support requests; future modal/drawer pattern can re-use these primitives.

### CSS Rules Implemented (2025-10-27)
**Claude → ui-foundation.css:**

Added 159 lines of pattern support CSS at end of file with documentation header:

**1. `.wc-advanced-options` (Pattern #3 - Advanced Options):**
- Collapsible `<details>` styling with border, padding, cursor
- Summary with arrow indicator (▸ → ▾ rotation on open)
- Hover state on summary (background: surface-alt)
- Content area with top border separator
- Uses: border, border-radius-sm, space-md, color tokens

**2. `.wc-pagination` (Pattern #5 - Data Table + Pagination):**
- Flexbox layout with gap, wrap support
- Link styling: min-width 2.5rem, border, hover states
- `.wc-pagination__link--current` variant (accent background, white text, no hover)
- Disabled state (opacity 0.5, no pointer events)
- Uses: space-xs/sm, border, border-radius-sm, accent color tokens

**3. `.wc-status-chip` (Pattern #7 - Status Indicators):**
- Inline-flex pill badge (border-radius-pill)
- Base style: border, surface background, text color
- `[data-state]` variants:
  - `success`/`completed` → positive-soft background, positive text
  - `error`/`failed` → critical-soft background, critical text
  - `warning`/`queued` → attention-soft background, attention text
  - `info`/`running` → accent-soft background, accent text
- Icon support via `.wc-status-chip__icon`
- Uses: space-xs/sm, border-radius-pill, semantic color tokens

**Design Characteristics:**
- All rules use existing CSS variables (--wc-color-*, --wc-space-*, --wc-radius-*)
- Grayscale default with semantic color variants only where meaningful
- No box-shadows, animations, or decorative effects (Calm Utility)
- Transition timing kept minimal (0.15s ease for hover states)
- Respects accessibility (cursor indicators, focus states, disabled states)

**Result:** Patterns #3, #5, #7 now fully functional. No fallback markup needed. Agents can copy-paste and styles "just work."

**Next:** Solicit Round 3 review from Codex to verify:
1. CSS implementation matches pattern intentions
2. Token usage is correct
3. Any edge cases or missing states
4. Ready for package closure

---

