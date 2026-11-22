# Restore the text introduction

Starting revision `7e29bff44`. The operator requested the original
WEPPcloud title, project subtitle, purpose statement and introductory
paragraph without the repeated links. Replace the split illustrated hero
with that text hierarchy. Keep the four header destinations and later
sections. The landing contract's Reviewed presentation section governs
the change. Check heading order and the rendered hero at desktop and
mobile widths. Implementation pending. No data or access changes.

Two independent reviewers accepted the change. Use the opening text from
`weppcloud-ui-lab/src/AppLight.tsx`, keep the hero and heading anchors,
and use the shared theme foreground throughout.

Forest Chromium verified the two headings, absence of hero links, buttons
and artwork, and fit at 1440, 390 and 320 CSS pixels. Both landing route
suites passed (25 tests).
