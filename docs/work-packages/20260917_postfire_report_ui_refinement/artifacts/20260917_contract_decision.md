# Contract decision: post-fire report presentation refinement

Starting revision: `4b14bcddb`. The operator explicitly authorized the requested
report changes in the current conversation. Commit authority persists from the
session's earlier commit/push instruction. Security impact is low: no endpoint,
authorization, data, model, query or persistence behavior changes.

Canonical authority is the post-fire report contract and the shared controller
contract's “Established presentation conventions” section. The UI style guide,
theme system and accessibility strategy provide supporting implementation
guidance and evidence criteria. This checkpoint amends the post-fire report
contract and updates the accessibility evidence plan; it does not make the
evidence plan normative authority.

Exact delta: Assessment summary becomes a `wc-summary-pane`; existing content
and interpretation remain. SVG text paints after response curves and markers in
a pointer-transparent final layer. Its shared class uses `--wc-color-text` fill,
`--wc-color-surface` stroke, a 3-pixel halo, rounded joins and stroke-first
`paint-order` to remain legible and theme-aware without intercepting marker
activation. Storm events uses shared numeric/select field macros, canonical
checkbox and button row. Fields reflow in a responsive grid or stack with at
least `--wc-space-md` row gaps, bounded control widths and no narrow-screen
overflow; the button row is separated from fields by at least
`--wc-space-md`. Existing selectors, values, filter semantics, focus order,
report data and query requests remain unchanged.

State matrix: absent/error reports retain existing outcomes. Available current,
stale, partial and legacy assessments use the pane, including “Not recorded”
values. A report with no assessment-specific notices displays “None recorded.”
Charts with scenarios, curve-only data, P50 and unit/theme updates use the final
label layer; no-data fallback stays textual. Blank/populated/invalid filter
inputs keep current browser/controller behavior; loading, empty matches, retry,
pagination and reset remain unchanged. Hostile strings continue through
`textContent`; no HTML input is added.

Regression evidence: actual template assertions, focused/full controller tests,
SVG layer/class/token/pointer checks, filter query/reset tests, frontend lint,
axe, theme-metrics, keyboard/visual desktop/mobile checks and authenticated
reload. Filter coverage includes all four hooks, numeric bounds and steps, every
sort option, descending checked and unchecked submissions, Apply/Reset order and
unchanged query encoding. A real-browser overlap hit test confirms a label does
not prevent pointer marker activation; Tab plus Enter and Space confirm keyboard
selection.
