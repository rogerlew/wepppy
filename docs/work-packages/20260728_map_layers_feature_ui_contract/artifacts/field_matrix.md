# DOM-04B Map Layers and Feature UI Matrix

| Rendered/helper behavior | Contract | Evidence |
| --- | --- | --- |
| SBS palette | One canonical USGS palette is used; no color-shift checkbox or display-time recoloring is rendered | Actual render + Map Jest palette test; amended by SBS-A11Y-01 |
| `sub_cmap_radio_default` | Default subcatchment colormap is selected | Actual render |
| `#sub_legend`, `#sbs_legend` | Dedicated live legend hosts exist | Actual render + Map Jest legend tests |
| Layer control | Accessible Layers button and deterministic base/overlay order | Existing Map Jest |
| Scale control | Map-distance label responds to zoom and unit preferences | Existing Map Jest |
| Feature modal | Dialog has an explicit accessible name | Existing Map Jest |

SBS-A11Y-01 additionally requires labeled legend entries and a dark-bordered
white masked/unmappable swatch while masked map pixels remain transparent. Old
saved shift state is ignored without error.

Excluded: coordinate/search/elevation/drilldown are DOM-04A. Remote resource
URLs and file-serving behavior are not changed or re-audited by this package.
