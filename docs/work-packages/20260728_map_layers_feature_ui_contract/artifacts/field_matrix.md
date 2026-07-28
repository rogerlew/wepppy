# DOM-04B Map Layers and Feature UI Matrix

| Rendered/helper behavior | Contract | Evidence |
| --- | --- | --- |
| `#sbs_color_shift_toggle` | Checkbox is rendered unchecked; change alters only SBS presentation | Actual render + Map Jest palette test |
| `sub_cmap_radio_default` | Default subcatchment colormap is selected | Actual render |
| `#sub_legend`, `#sbs_legend` | Dedicated live legend hosts exist | Actual render + Map Jest legend tests |
| Layer control | Accessible Layers button and deterministic base/overlay order | Existing Map Jest |
| Scale control | Map-distance label responds to zoom and unit preferences | Existing Map Jest |
| Feature modal | Dialog has an explicit accessible name | Existing Map Jest |

Excluded: coordinate/search/elevation/drilldown are DOM-04A. Remote resource
URLs and file-serving behavior are not changed or re-audited by this package.
