# Restore the original Atlas wheel gesture and overlays

Base revision `657a1e3c2`. The operator requested the original Ctrl-wheel
interaction and overlaid run-type legend. The Run Atlas section of the
[current landing contract](../../../ui-docs/contracts/pure-landing-contract.md#run-atlas)
defines gesture scope, copy and placement. Verify native page scroll,
modified wheel zoom, synchronized cameras, overlay visibility and spacing
on desktop and narrow screens. Existing marker sizing and public routes
retain their contracts.

This is an operator-approved preview behavior change. Implementation
conformance is pending. The shared controller, accessibility and theme
conventions still apply. The change adds no permissions, data fields,
external requests or dependencies.

Two independent reviewers accepted the scope. Adopt their requested
browser evidence for ordinary and modified wheel over canvas and overlay
text, local handling and narrow reflow. Expand SBS for assistive technology,
retain the hillslope caption, and hide overlays with the unavailable map.
