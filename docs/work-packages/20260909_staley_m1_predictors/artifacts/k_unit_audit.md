# K convention audit

Engineering audit, 2026-09-09. Owner subsequently accepted coverage/readiness
policies P02/P03; ADR-0059 records that decision separately from this unit evidence.

## Evidence and conclusion

Staley 2017 section 4.1 identifies M1 S as the fine-fraction KF factor;
its soil source is Schwarz and Alexander's STATSGO compilation. The paper
specifies division by 100 for M3 soil thickness, not M1 KF.
See the [publication reference](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/README.md)
and [USGS source record](https://pubs.usgs.gov/publication/ofr95449).

The [NRCS soil-property definition](https://efotg.sc.egov.usda.gov/references/Delete/2007-12-15/soilpropqual.htm)
identifies Kf with the fine-earth fraction and distinguishes whole-soil Kw.
Wischmeier and Smith 1978, Agriculture Handbook 537, printed page 10,
equation 3, defines the customary USLE nomograph scale. The locally retained
[primary handbook](../../../../wepppy/nodb/mods/rusle/docs/pdfs/wischmeier_smith_1978_ah537.pdf)
was inspected with `pdftotext -layout`.

The repository's `k_nomograph.compute_polaris_nomograph_k` implements that
equation, including its division by 100. `k_integration.py` writes the result
directly to the named Nomograph raster without an SI conversion. The supported
mapping is therefore S = basin mean of the named raster, with multiplier 1.
This is a formula/source interpretation, not a conclusion from raster magnitude.
Do not divide K by 100 again or apply a metric conversion for Staley.

## Independent numeric check

For sand 40%, silt 40%, clay 20%, organic matter 2%, and Ksat 3 cm/hour,
the existing modeled mappings give very fine sand 19.68%, structure 3 and
permeability 3. Thus M = (40 + 19.68) × 80 = 4774.4 and:

    K = [0.00021 × 4774.4^1.14 × 10 + 3.25] / 100
      = 0.3607363906456875

A standalone scalar calculation and direct import of the existing estimator
both returned exactly that value using `.venv/bin/python`. This checks the
formula scale; it does not establish empirical equivalence of POLARIS estimates
and STATSGO calibration data.

## Provenance limitations

RUSLE models texture/structure/permeability, applies source gap filling and may
adjust permeability using profile fragments. Preserve those choices in output;
do not call the resulting field measured STATSGO Kf. The optional permeability
adjustment is not a direct whole-soil Kw multiplier. No change to those upstream
parameterizations is authorized here.

Current K manifests describe configuration and artifact paths, but do not bind
all source and output bytes with SHA-256. Two inventoried legacy manifests also
lack gap-fill policy/summary fields. A newly computed digest establishes current
byte identity only. Freshness and legacy provenance handling must be explicit
in the frozen interface; missing information must not be fabricated.
