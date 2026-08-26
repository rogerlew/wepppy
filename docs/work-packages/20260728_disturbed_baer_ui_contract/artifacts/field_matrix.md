# DOM-23 Disturbed/BAER Field Matrix

| Rendered field/action | Evidence |
| --- | --- |
| SBS modes/upload/uniform/remove | Actual render + both Jest suites + routes |
| Fire date and lookup lifecycle | Actual render + Disturbed route tests |
| BAER classification/map | Exact current USGS RGB values map to the existing categorical classes; historical recognized colors remain compatible; masked/unmappable is transparent NoData; explicit `export_palette="legacy"` exports use the USGS palette while the default shifted export remains unchanged. BAER Jest + route/NoDb tests; amended by SBS-A11Y-01 |
