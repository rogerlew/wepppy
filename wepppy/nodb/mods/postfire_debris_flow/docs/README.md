# Postfire Debris Flow Reference Bundle

Scientific requirements and rationale live in the
[module specification](../specification.md). This catalog records reference
locations and retrieval status; it is not a runtime dependency.

## Staley 2017

Staley, D.M., Negri, J.A., Kean, J.W., Laber, J.L., Tillery, A.C., and Youberg,
A.M. (2017). Prediction of spatially explicit rainfall intensity-duration
thresholds for post-fire debris-flow generation in the western United States.
Geomorphology 278, 149-162.

- [DOI](https://doi.org/10.1016/j.geomorph.2016.10.019).
- [USGS publication record](https://pubs.usgs.gov/publication/70188478).
- [Indexed PDF source](https://ftp.wildfire.gov/public/nat_baer/2016_BAER/ChimneyTops2/GRSM/DebrisFlow/StaleyEtAl_InPress_SpatiallyExplicitThresholds_Geomorphology%20%281%29.pdf).
- Local filename: `pdfs/staley_2017.pdf` (gitignored).
- Acquired: 2026-09-08, copied from operator-provided `/tmp/staley2017.pdf`.
  Original download URL was not supplied.
- Version: 42-page accepted manuscript, accepted 2016-10-10, with an Elsevier
  cover sheet stating that copyediting and typesetting remain pending. Title,
  authors, and DOI match the 2017 publication. All 42 pages extract as text.
- Size: 1,941,455 bytes.
- SHA-256: `72de34d27231acd14cc0ba8daf431e9121464132072447aef6ff658b687e660b`.
- Earlier retrieval attempted: 2026-09-08. The web index exposes the 14-page paper,
  but direct PDF retrieval returns HTTP 404 for both encoded and literal
  parentheses. The legacy `ftp.nifc.gov` hostname does not resolve here;
  the publisher PDF endpoint returns HTTP 403. Those attempts saved no PDF.
- OpenAlex lists no PDF location; Semantic Scholar lists no open-access PDF.
  These are discovery results, not definitive legal classifications.

Useful reading locations: section 4.1 for source data; equations 4-6 for
probabilities and rainfall thresholds; Table 4 (printed page 156, PDF page 8)
for predictors and coefficients; section 5.2 for model selection. These page
numbers refer to the final journal version, not the local accepted manuscript.
Use section and table labels when navigating the local copy, and verify any
scientific discrepancies against the final publication before implementation.

## Related Sources

- [M3 terrain evaluation](m3_terrain.md): WBT ownership, relief ambiguity,
  algorithm complexity, and catchment/resolution comparison design.
- [dNBR upload design](dnbr_upload.md): SBS precedent, scale normalization,
  exact grid alignment, valid overlap, and partial-coverage semantics.
- [SSURGO M3 feasibility assessment](ssurgo_m3_feasibility.md): original THICK
  units, project cache fields, derivation limitations, and validation needs.
- [Staley et al. (2016), USGS Open-File Report 2016-1106](https://doi.org/10.3133/ofr20161106):
  companion methodological source, not a substitute for the 2017 paper.
- [pfdf Staley model guide](https://ghsc.code-pages.usgs.gov/lhp/pfdf/guide/models/s17.html):
  comparison implementation; local checkout declares GPL-3.0-only.
- [RUSLE specification](../../rusle/specification.md): K artifact ownership,
  estimator assumptions, and source provenance.
- [PDF storage decision](pdfs/README.md).
