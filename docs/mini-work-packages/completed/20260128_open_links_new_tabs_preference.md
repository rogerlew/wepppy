# Mini Work Package: Open Links in New Tabs Preference
Status: Completed (2026-01-28)
Last Updated: 2026-01-28
Primary Areas: `wepppy/weppcloud/templates/header/_run_header_fixed.htm`, `wepppy/weppcloud/templates/reports/_base_report.htm`, `wepppy/weppcloud/templates/controls/poweruser_panel.htm`, `wepppy/weppcloud/static/js/*`

## Objective
Add a user preference checkbox in the run page "More" menu that controls whether key links open in new tabs. Default to enabled (checked). Persist the preference in a cookie and apply it to README, Fork, Archive, Browse (More menu), Profile, Runs, Mods help, Access log, and **all** PowerUser modal links. Logout must always open in the same tab.

## Scope
- Add the preference checkbox to both run headers:
  - `header/_run_header_fixed.htm` (runs0_pure)
  - `reports/_base_report.htm` (report pages)
- Tag all affected links with a shared selector (e.g., `data-open-tab-pref`).
- Replace hard-coded `target="_blank"`/`rel="noopener"` on affected links with JS-driven behavior.
- Store preference in a cookie (e.g., `wc_open_links_new_tab=1|0`) with `path=/`, `SameSite=Lax`, and a long TTL (1 year).
- Apply preference to all links inside the PowerUser modal, including external docs.
- Ensure logout remains same-tab regardless of the preference.

## Non-goals
- Changing link behavior outside the specified run/report/PowerUser surfaces.
- Adding server-side user profile storage (cookie-only preference).
- Modifying modal button behavior (only links).

## Implementation Plan
1. **Template markup updates**
   - `header/_run_header_fixed.htm`: add "Open links in new tabs" checkbox under More; add `data-open-tab-pref` to README, Fork, Archive, Browse, Mods help, Access log, Profile, Runs.
   - `reports/_base_report.htm`: mirror the same changes to keep report headers consistent.
   - `controls/poweruser_panel.htm`: add `data-open-tab-pref` to all anchors (resource links, browse links, dashboards, docs). Remove hard-coded `target`/`rel` so JS owns the behavior.
2. **JS preference helper**
   - Add a small script (e.g., `static/js/link_target_pref.js`, included by both headers) that:
     - Reads the cookie and defaults to enabled when missing.
     - Sets the checkbox state on load and writes the cookie on change.
     - Applies `target="_blank"` + `rel="noopener"` to `[data-open-tab-pref]` when enabled.
     - Removes `target`/`rel` when disabled.
     - Explicitly skips logout (either omit `data-open-tab-pref` or add a `data-open-tab-forced="same"` guard).
3. **QA checks**
   - Toggle on: README/Fork/Archive, Browse, Profile, Runs, Mods help, Access log, and all PowerUser links open in new tabs.
   - Toggle off: those links open in the same tab.
   - Logout always opens in the same tab.
   - Preference persists across reloads and between run/report pages.

## Validation
- Manual smoke: open a run, toggle preference, click each affected link, confirm target behavior and cookie persistence.
- Verify PowerUser external docs follow the same preference.

## Follow-ups
- Consider consolidating the run/report headers into a shared include to avoid duplicated preference markup.
