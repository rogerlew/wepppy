# Use the site masthead on the landing preview

Base `77a044ed2`. The operator superseded the earlier preview-specific
header disposition. The landing contract's Reviewed presentation section
now defers to the shared shell and the UI style guide's header and navigation
conventions. Inherit the brand, tools, theme labels and breakpoint behavior;
provide the landing destinations as standard navigation links, including the
session-appropriate account link. Preserve skip navigation.

Remove the preview-specific icon, heavy brand styling, menu script, theme
mode and header link overrides. This change affects presentation, with no
changes to access, publication or public cutover. Implementation pending.
Check rendered header markup, link states, theme operation and narrow layout.

Both independent reviews accepted the shared masthead. Check narrow reflow
for the theme picker and navigation, retain the full theme labels and use
the Interfaces More disclosure for secondary destinations if space requires.

## Verification

Forest renders the inherited text brand, ordinary account and Interfaces
links, and the standard More disclosure for Help and Research. Chromium
matched computed brand, navigation link and select styles to Interfaces.
Only header wrapping and control width containment are scoped to the preview.
The shared masthead theme label uses the theme text foreground after axe
measured contrast below 2:1 in both Ayu Mirage themes. The five AA theme
header scans subsequently reported zero violations.

Verified theme changes, keyboard activation of More, skip-to-content,
and reflow from 320 to 1440 CSS pixels. A signed-in fixture containing
My Runs and Notifications also passed at 200% zoom with More expanded.
The two landing route suites passed (25 tests).
