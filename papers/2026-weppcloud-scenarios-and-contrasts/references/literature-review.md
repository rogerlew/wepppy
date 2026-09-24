# Literature review for the introduction

> Reviewed 2026-09-21. Targeted narrative review, not a systematic review.
> Seventeen PDFs retained, including three supplied by Roger.
> [sources.json](sources.json) records download URLs, dates, hashes, PDF page
> counts, and prior failures. [access-needed.md](access-needed.md) records resolved requests.

## Scope and evidence handling

Start from WEPPcloud Parts I/II and follow the forest-model, fire-treatment,
watershed-routing, and visualization references relevant to OMNI. Prioritize
publisher metadata, USDA Forest Service/ARS repositories, and author/institutional
copies. Check PDF title pages and the passages used for the introduction. This
pass does not evaluate every experiment in every retrieved paper.

Downloaded PDFs and their extracted full text remain local and are ignored by
[.gitignore](.gitignore). This includes openly licensed papers for a consistent
reading-copy policy. Public download availability is not treated as permission
to redistribute a publisher PDF. Bibliographic metadata and original review
notes can be versioned. The Dobre et al. Data in Brief PDF explicitly states a
CC BY license; no equivalent redistribution claim is made for other copies.

## Synthesis for this manuscript

1. **WEPP and forest applications:** introduce physical processes and the forest
   hydrology/parameterization lineage before discussing software automation.
   Native vegetation here means forests, shrublands, and grass-dominated systems;
   do not imply identical parameter performance across them.
2. **WEPPcloud's modeling harness:** `(Un)Disturbed` provides a coordinated soil
   and management parameterization for unburned, burned, and treated conditions.
   OMNI automates use of this framework; it does not replace its physical model.
3. **Scenario management:** WEPPcloud Part I, section 4.1.5 (PDF p. 8), explicitly
   describes cloning projects for management comparisons. The operator's report
   of tedious, error-prone manual synchronization motivates OMNI; no measured
   user-error reduction is claimed.
4. **Contrasts and routing:** distinguish source-area erosion from the routed
   effect at the outlet. Current runner/OMNI code supplies evidence for pass-file
   assembly; the watershed literature supports the process-model context.
5. **Interactive analysis:** acknowledge Pi-VAT as an existing multi-scenario
   analysis/visualization contribution. Position OMNI plus GL-Dashboard and query
   engine around the connected execution-and-analysis workflow, not invention of
   scenario comparison or interactive visualization.

## Downloaded papers

| Local PDF stem | Verified citation and DOI | Relevance and reading notes |
| --- | --- | --- |
| `Lew2022_WEPPcloud_PartI` | Lew et al. (2022), *WEPPcloud: An online watershed-scale hydrologic modeling tool. Part I. Model description*. Journal of Hydrology 608, 127603. [DOI](https://doi.org/10.1016/j.jhydrol.2022.127603) | Direct predecessor. Table 1 and section 4.1.5 establish the common disturbed/unburned parameterization and cloning workflow. Use current source for today's implementation. |
| `Dobre2022_WEPPcloud_PartII` | Dobre et al. (2022), *WEPPcloud: An online watershed-scale hydrologic modeling tool. Part II. Model performance assessment and applications to forest management and wildfires*. Journal of Hydrology 610, 127776. [DOI](https://doi.org/10.1016/j.jhydrol.2022.127776) | Forest evaluation and pre/post-disturbance application context. Abstract, application framing, and Table 7 consulted. Its performance findings do not validate new OMNI configurations. |
| `Elliot2004_ForestInterfaces` | Elliot (2004), *WEPP Internet Interfaces for Forest Erosion Prediction*. JAWRA 40(2), 299–309. [DOI](https://doi.org/10.1111/j.1752-1688.2004.tb01030.x) | Early practitioner interfaces and forest soil/management databases; useful historical basis for reducing input-preparation burden. Use journal issue year 2004 despite later online-publication metadata. |
| `Dun2009_ForestAdaptation` | Dun et al. (2009), *Adapting the Water Erosion Prediction Project (WEPP) model for forest applications*. Journal of Hydrology 366, 46–54. [DOI](https://doi.org/10.1016/j.jhydrol.2008.12.019) | Forest hydrology and subsurface-flow adaptation. Establishes historical development; do not equate its equations with every current executable path. |
| `Elliot2013_ForestErosion` | Elliot (2013), *Erosion processes and prediction with WEPP technology in forests in the Northwestern U.S.* Transactions of the ASABE 56(2), 563–579. [DOI](https://doi.org/10.13031/2013.42680) | Forest disturbances, downstream resources, and channel storage/transport motivate evaluating outlet response rather than only source erosion. |
| `Robichaud2007_ERMiT` | Robichaud et al. (2007), *Predicting postfire erosion and mitigation effectiveness with a web-based probabilistic erosion model*. CATENA 71(2), 229–241. [DOI](https://doi.org/10.1016/j.catena.2007.03.003) | Essential post-fire treatment comparator. ERMiT's probabilistic hillslope framework differs from OMNI's selected spatial alternatives with watershed rerouting. Do not claim probabilistic risk quantification for OMNI without an appropriate ensemble. |
| `RobichaudAshmun2013_DecisionTools` | Robichaud and Ashmun (2013), *Tools to aid post-wildfire assessment and erosion-mitigation treatment decisions*. International Journal of Wildland Fire 22, 95–105. [DOI](https://doi.org/10.1071/WF11162) | Explains the assessment/treatment decision setting and delivery of research to managers. Issue year is 2013; online publication was 2012. |
| `Brooks2016_Tahoe` | Brooks et al. (2016), *Watershed-scale evaluation of the Water Erosion Prediction Project (WEPP) model in the Lake Tahoe basin*. Journal of Hydrology 533, 389–402. [DOI](https://doi.org/10.1016/j.jhydrol.2015.12.004) | Supporting forest watershed evaluation. Title/abstract inspected; reserve detailed performance statements for closer methods/results review if used. |
| `Srivastava2015_MunicipalTreatment` | Srivastava, Elliot, and Wu (2015), *Use of Fire Spread and Hydrology Models to Target Forest Management on a Municipal Watershed*. Watershed Management 2015. [DOI](https://doi.org/10.1061/9780784479322.018) | Concrete pre-fire spatial targeting and water-supply example. Conference contribution, not a journal article. OMNI should acknowledge this application precedent. |
| `LarsenMacDonald2007_DisturbedWEPP` | Larsen and MacDonald (2007), *Predicting postfire sediment yields at the hillslope scale: Testing RUSLE and Disturbed WEPP*. Water Resources Research 43, W11412. [DOI](https://doi.org/10.1029/2006WR005560) | Important counterbalance: field evaluation shows substantial plot-level prediction difficulty. Historical parameterization; not a direct test of the present WEPPcloud build. |
| `Deval2022_PiVAT` | Deval et al. (2022), *Pi-VAT: A web-based visualization tool for decision support using spatially complex water quality model outputs*. Journal of Hydrology 607, 127529. [DOI](https://doi.org/10.1016/j.jhydrol.2022.127529) | Direct analysis/visualization predecessor. Abstract/introduction describe multi-scenario outputs and spatial aggregation for WEPP/SWAT. Compare capabilities explicitly before making novelty claims. |
| `Flanagan2013_GeospatialWEPP` | Flanagan et al. (2013), *Geospatial Application of the Water Erosion Prediction Project (WEPP) Model*. Transactions of the ASABE 56(2), 591–601. [DOI](https://doi.org/10.13031/2013.42681) | GIS automation and increasing input-management complexity. Do not confuse with the similarly titled 2011 conference paper, DOI 10.13031/2013.39277. |
| `Dun2013_OnlineForestHydrology` | Dun et al. (2013), *Applying Online WEPP to Assess Forest Watershed Hydrology*. Transactions of the ASABE 56(2), 581–590. [DOI](https://doi.org/10.13031/2013.42689) | Earlier online forest watershed interface; useful for lineage rather than a claim that OMNI first automated WEPP. Title/abstract inspected. |
| `Dobre2022_WEPPcloud_Datasets` | Dobre et al. (2022), *WEPPcloud hydrologic and erosion simulation datasets from 28 watersheds in US Pacific Northwest and calibrating model parameters for undisturbed and disturbed forest management conditions*. Data in Brief 42, 108251. [DOI](https://doi.org/10.1016/j.dib.2022.108251) | Companion artifact/data source and possible case-study leads. Title, data availability, and license inspected; legacy run links are not evidence of current availability or version parity. |
| `Ascough1997_WatershedModel` | Ascough II, Baffaut, Nearing, and Liu (1997), *The WEPP watershed model: I. Hydrology and erosion*. Transactions of the ASAE 40(4), 921–933. [DOI](https://doi.org/10.13031/2013.21343) | Hillslope pass-file reuse and watershed channel hydrology/erosion formulation; historical WEPP95 scope. Roger-supplied copy. |
| `Flanagan2007_WEPPOverview` | Flanagan, Gilley, and Franti (2007), *Water Erosion Prediction Project (WEPP): Development History, Model Capabilities, and Future Enhancements*. Transactions of the ASABE 50(5), 1603–1612. [DOI](https://doi.org/10.13031/2013.23968) | Process inventory, experimental origins, and interface lineage. Roger-supplied copy. |
| `Renschler2003_GeoWEPP` | Renschler (2003), *Designing geo-spatial interfaces to scale process models: the GeoWEPP approach*. Hydrological Processes 17, 1005–1017. [DOI](https://doi.org/10.1002/hyp.1177) | Geospatial input preparation and land-use scenario assessment, with explicit scale/uncertainty concerns. Roger-supplied copy. |

## Follow-up review of supplied papers

- **Ascough et al. (1997), pp. 923–924:** the conceptual framework explicitly
  describes hillslope pass files, their assembly into a watershed master pass
  file, and watershed-only execution. This is a precedent for computational
  reuse, not an OMNI invention. The historical run-mode requirements are not
  evidence that arbitrary scenarios or current binary formats are compatible.
- **Ascough et al. (1997), channel erosion section:** sediment response depends
  on upstream/lateral loads, shear stress, and transport capacity, with net
  detachment or deposition. This supports rerouting to assess outlet response.
  Its WEPP95 limitations exclude classical gully and large-stream erosion;
  do not describe process-based routing as comprehensive channel physics or
  infer current model limits solely from this historical version.
- **Flanagan et al. (2007), abstract and development overview:** supports the
  process inventory, cropland/rangeland/disturbed-forest experimental origins,
  and evolution of interfaces and model components. It does not validate the
  current WEPPcloud executable or OMNI treatment effects.
- **Renschler (2003), abstract, application workflow, and conclusions:** GeoWEPP
  connects spatial data preparation, watershed representation, and land-use
  scenario assessment. Spatial/temporal scale and input-data uncertainty are
  central design concerns. Use as interface/scenario lineage, not evidence of
  OMNI-style pass-file contrasts or present-day feature parity.

All initial access requests are resolved; see [access-needed.md](access-needed.md).
The three supplied PDFs were checked against their title pages and relevant
passages. This is a targeted reading, not a complete review of every equation.

## Implementation checks separate from literature

- [Current disturbed guide](../../../wepppy/nodb/mods/disturbed/ENDUSER.md):
  confirms unburned conditions use the same harness.
- [Scenario clone service](../../../wepppy/nodb/mods/omni/omni_clone_contrast_service.py):
  shares climate/watershed assets and copies controller state and disturbed resources.
- [Scenario mode builder](../../../wepppy/nodb/mods/omni/omni_mode_build_services.py):
  applies scenario-specific rebuilding; undisturbed removes SBS before rebuilding.
- [WEPP runner](../../../wepp_runner/README.md): separate hillslope/watershed steps
  and paths to hillslope pass files; confirm the evaluated binary's format.
- [Advanced options guide](../../../wepppy/weppcloud/routes/usersum/weppcloud/wepp-advanced-options.md):
  documents consequential model controls. It also flags differences between
  historical published equations and current execution paths, reinforcing the
  need to pin actual code/binaries for the eventual case study.

Inheritance during build is not a guarantee of complete later-change invalidation.
Likewise, rerouting preserves the selected model's process calculations but does
not prove every physical feedback, parameterization, or treatment effect correct.
