# WEPPcloud Diff Viewer

👋 Hi! I'm the diff viewer living in `wepppy/weppcloud/routes/diff`. I was crafted to turn side-by-side file comparisons into a fast, pleasant experience—even when you throw hundreds of thousands of lines or deeply tokenized parameter files my way.

###

vibe coded with Open-AI codex (gpt-5-codex high)

## Feature Highlights

- **High-performance client diffing** – A Myers-based line diff combined with token-level highlights keeps differences precise without shipping raw files to the server.
- **Virtualized rendering** – Only the viewport’s rows are in the DOM at any moment, and implements virtual scrolling with buffering, so scrolling through large files stays smooth.
- **Smart layout** – Line-number gutters stay fixed, panes stay balanced, and long lines are clipped to their columns while horizontal scrolling reveals details when you need them.
- **Diff-only toggle** – Instantly collapse identical rows to focus on what changed and jump back to the full view with a single click.
- **Dynamic sizing** – Column widths adapt to the content while respecting the viewport, and sticky header/toolbar controls remain accessible at all times.
- **Robust tokenization** – Differences inside structured parameter files (e.g., WEPP soils) are highlighted token-by-token instead of blobbed together for a line.

## Processing Flow

1. **Route bootstrap** (`diff.py` → `comparer.htm`)
   - The Flask route resolves the left and right file URLs, injects metadata (run IDs, config, download links), and serves the minimal HTML shell.

2. **Client initialization** (`diff_viewer.js`)
   - On `DOMContentLoaded`, the viewer fetches both files in parallel and normalizes line endings/tabs.  
   - A Myers diff produces line-level operations; contiguous insert/delete pairs become `replace` blocks.

3. **Token highlighting**
   - For every `replace`, a secondary Myers pass runs over tokens (split on whitespace and punctuation) to wrap fine-grained insert/delete spans.

4. **Column sizing + layout**
   - Estimated character widths drive CSS custom properties that size both panes and gutters. Widths are clamped so long lines never shove the opposite column off screen.

5. **Virtualized render loop**
   - The renderer maintains start/end row indexes based on scroll position plus configurable overscan.  
   - `requestAnimationFrame` throttles updates, and the spacer element expands to the total virtual height.

6. **Interaction affordances**
   - The diff-only toggle swaps the rendered row set, re-measures column widths, and scrolls back to the top.  
   - Resizing the window recalculates widths and recenters the horizontal scroll.

## Working With the Viewer

### Key Files

| File | Purpose |
| --- | --- |
| `diff.py` | Flask blueprint delivering the diff comparer shell. |
| `templates/comparer.htm` | HTML + CSS responsible for layout, sticky toolbar, and overall styling. |
| `static/js/diff_viewer.js` | All client logic: fetching, diffing, virtualization, token highlighting, and UI wiring. |

### Parameters Worth Knowing (`diff_viewer.js`)

- `ROW_HEIGHT`, `OVERSCAN_ROWS` – tune virtualization density. If you adjust the CSS row height, keep these in sync.
- `MAX_COLUMN_WIDTH_CHARS`, `COLUMN_PADDING_PX`, `PANE_GAP_PX` – control horizontal layout behaviour.
- `TOKEN_BOUNDARY_REGEX`, `TOKEN_DIFF_MAX_LENGTH` – tweak token level diff sensitivity.
- `FETCH_TIMEOUT_MS` – cap download wait times if repositories are slow.

### Layout Tips

- **Toolbar + viewport spacing**: The toolbar is absolutely positioned; `diff-root` adds top padding equal to the toolbar height so the scroll region never overlaps. If you restyle the toolbar height, update the CSS variable or the `ResizeObserver` will handle it for you.
- **Gutters**: Both line-number gutters are sticky and share the same width variable. If long run IDs require more digits, `applyLineNumberWidthHint` automatically widens them.
- **Column clipping**: Each pane uses `overflow: hidden` with `min-width: max-content` for the inner content so long lines are clipped but still accessible via horizontal scroll.

### Virtualization Pain Points

- **Row height mismatches**: The renderer samples the first visible row and updates the `--diff-row-height` variable if it detects a deviation. If you radically change row styling, make sure that sample still represents the final height.
- **Overscan trade-offs**: Large `OVERSCAN_ROWS` smooth out fast scrolling but increase DOM size. Too small and you risk white gaps if the browser can’t render in time.
- **Diff-only mode**: When toggling back to full view we recalc column widths so the layout doesn’t jump. If you add new filters, remember to trigger `applyColumnWidthHints`.

### Extending Functionality

- **Additional metadata**: Pass extra fields through the bootstrap object in `comparer.htm` and read them inside `diff_viewer.js` for custom badges or context banners.
- **Alternate diff algorithms**: The Myers implementation is modular—drop in a different `diffCore` if you need patience diff or histogram diff, but ensure `buildRows` still receives the same operation shape.
- **Theme adjustments**: Most colours/sizes live in CSS custom properties at the top of `comparer.htm`. Adjust them once and the entire viewer adapts.

## Final Notes

This viewer was purpose-built for WEPPcloud workflows, but the architecture is generic: asynchronous file fetch, Myers diff, virtualized rendering, and a responsive layout. Feel free to iterate—tweak the parameters, plug in new renderers, or wrap it in your own tooling. If something becomes sluggish or misaligned, the hotspots above are the first places to look.
