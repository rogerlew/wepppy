# WP05 Capability Evidence

Real WP04 snapshot tests resolve every one of 128 shipped presets and now prove
non-empty semantic climate, soil-builder, and land-use lists in the canonical
flattened config. Soil capability IDs are explicitly mapped rather than derived
from aliased enums. Climate and land-use reuse their existing semantic catalog
keys.

Focused validation passed 69 soil/land-use/helper tests after the wiring change;
the broader capability/snapshot/catalog selection passed in the same focused
iteration. Stub, documentation, broad-exception, and diff gates are recorded in
the package tracker.

The exact repository suite passed with 6,888 passed and 63 skipped.
