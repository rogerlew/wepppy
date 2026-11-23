# Restore familiar landing destinations

Base `28b505bcf`. The operator selected the original four direct desktop
destinations and a mobile hamburger. Use a native disclosure at the shared
540 px mobile breakpoint, with the same link order and URLs for either
layout. Retain the shared brand, tools and link styling. Check both account
states, keyboard operation, and resizing without scripts. The landing
contract's Reviewed presentation section governs this change. Implementation
is pending. No authorization or data changes.

Both independent reviewers accepted the scope. Keep mobile links in normal
flow. Use one navigation landmark, hide the inactive layout, and expose
the shared tools when the mobile disclosure opens. Check the Tab order and
the breakpoint in both directions.

Forest verification passed at 320, 390, 540, 541, 768 and 1440 CSS pixels.
With scripting disabled, Enter and Space toggled Menu. Closed links were
absent from the navigation accessibility tree and Tab order, and expanded
links were visible and keyboard-reachable in the requested order. The
theme picker was accessible when expanded. Both landing route suites passed
(25 tests), including the authenticated account destination.
