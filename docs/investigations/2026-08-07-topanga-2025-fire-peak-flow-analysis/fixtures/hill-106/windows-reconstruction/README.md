# Windows WEPP Reconstruction Inputs

The three `7778` soils are literal reconstructions of Appendix B in Elliot's
report. They are investigation-derived inputs, not files retrieved from
Elliot's computer. The climate, slope, and management inputs for replays come
from the corresponding unchanged WEPPcloud fixture.

Replays on `blarhg` must use isolated directories and test `wepp_ui.txt` and
`pmetpara.txt` independently. The WEPPcloud-only `gwcoeff.txt` and `snow.txt`
sidecars are retained in the source fixture but are not read by the installed
Windows 2024 source tree.

