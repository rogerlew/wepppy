# WEPPcloud FAQ (Legacy Draft)

## How do you calibrate the WEPP model?

The WEPP model is a process-based model where most of the key parameters can be directly measured, estimated, or acquired from common spatially explicit data sources (for example, STATSGO and SSURGO). Many improvements to the web interface have focused on providing the model with high-resolution spatial weather data using publicly available mapping datasets, since a key issue in hydrologic models is capturing variability in precipitation and temperature across a landscape. Soil parameters are extracted directly from the soil survey and do not rely on statistical decay coefficients or exponents that can only be fixed using historic observed data.

This approach is commonly used because the model is often applied as a decision-support tool in ungauged basins where calibration is not possible. Manual and automated calibration can be performed (for example with PEST), but reasonable predictions are often obtained without extensive calibration, especially for runoff.

## How accurate is the WEPP model?

Differences in observed soil erosion rates from duplicate hillslope plots side by side are often on the order of 50%. Natural variability and landscape complexity can never be fully captured in a model. Annual or monthly predictions (for example, annual water yield or sediment load) are likely to be more reliable than daily predictions. Sub-watershed and hillslope-scale predictions are likely less accurate than watershed basin predictions. Absolute accuracy is typically poorer than WEPP's ability to predict relative variability across a basin and in response to treatments.

The hillslope version of WEPP has been validated for post-fire conditions with field-collected hillslope erosion data (Robichaud et al. 2016). The watershed version of WEPP has been validated after the 2011 Wallow Fire in Arizona (Quinn 2018). A 50% variability rule of thumb is often used for explicit model accuracy.

## What are the most sensitive parameters in the model?

Other than precipitation and temperature inputs, soil parameters (soil depth, hydraulic conductivity of the lower restrictive layer, and effective hydraulic conductivity of the surface soil layer) are often among the most sensitive for predicting runoff.

For soil erosion rates, sensitive parameters commonly include soil surface cover, interrill erodibility, rill erodibility, and critical shear. Late-summer streamflows and hydrograph shape are often sensitive to lateral hydraulic conductivity and the baseflow recession coefficient. The baseflow recession coefficient is typically stable across a region and can be constrained using streamflow from a nearby gage. Soil surface cover is relatively easy to measure and generally requires estimating recovery or disturbance impacts to ground cover.

## How is vegetative recovery and residue decay simulated?

Without nitrogen and carbon cycling, vegetative growth and residue decay are based on soil-moisture and temperature relationships. Other models such as RHESSYS can be used to predict vegetative regrowth. With RHESSYS, either direct vegetative characteristic maps (for example, LAI and canopy cover) can be fed to WEPP, or regrowth curves can be extracted if time-series outputs are desired rather than probabilistic outputs.

## How well does WEPP predict stream channel erosion?

Stream channel erosion in WEPP is simulated using a simpler approach than advanced hydrodynamic stream channel models (for example, CONCEPTS, CCHE1D, HEC-6), because stream cross-sectional characteristics are empirically assigned by stream order.

Particle size of the bed, critical shear, bank/bed erodibility, and depth to an impermeable layer are defined for each stream based on dominant soil type along the channel and stream order. Channel erosion simulation capability has historically been tested for watersheds greater than 1 square mile. Results from forested watersheds in Idaho, Arizona, and Lake Tahoe, California have indicated agreement between measured and observed sediment load and treatment or wildfire response in sediment load.

## Is carbon/nitrogen cycling included in the model?

No. The WEPP watershed interface does not simulate changes in soil carbon or nitrogen cycling. Beta versions with related algorithms have existed in research contexts but are still under development.

## How does the model generate probabilistic runoff and erosion output for each year following a disturbance (for example, post-fire)?

The model provides exceedance probabilities by repeatedly running the model under the same vegetative and soil conditions with multiple weather realizations. Historically this has been described as 100 realizations per condition. Using these realizations, exceedance probabilities and return periods are calculated for magnitude events (for example, 2-year return period). Each year following disturbance or treatment may have unique vegetation and soil conditions, and each condition is evaluated with multiple weather scenarios to produce probabilistic outputs.

## What is the largest size watershed someone should run with WEPP?

Current recommended guidance is to stay below 2500 hillslopes and about 50 square miles (or less) per watershed run.

Practical constraints still apply:

- Simulation runtime increases with watershed size.
- Channel algorithms assume runoff generated within a day exits the watershed in the same day (no channel storage routing).
- Simplified in-stream sediment transport algorithms are not intended for complex large-river transport dynamics.
- Large delineations can produce long hillslopes where erosion may be dominated by gully processes that WEPP is less suited to represent than rill/interrill erosion.

If the objective is hillslope erosion mapping rather than outlet sediment load or peak-flow prediction, larger watersheds may still be used, with caution in interpreting outlet-scale outputs.

## Can WEPP predict debris flows or landslides?

The WEPPcloud watershed interface can estimate debris-flow probability and magnitude after wildfire using the Cannon et al. (2010) model. Caution is recommended because empirical parameters may not be appropriate for all watersheds.

The USGS provides current post-fire debris-flow hazard information for the US:  
<https://www.usgs.gov/programs/landslide-hazards/science/postfire-debris-flow-hazards>

WEPP does not predict landslides directly. Related tools historically referenced include LISA and D-LISA on the Forest Service WEPP site:  
<https://forest.moscowfsl.wsu.edu/engr/slopesw.html>

## What is the difference between all these WEPP Tools (ERMiT, Disturbed WEPP, FSWEPP, GEOWEPP, QWEPP, WEPPcloud)?

These tools share WEPP heritage, but they are not equivalent in model generation, preprocessing, or watershed workflow:

- ERMiT and Disturbed WEPP are legacy hillslope tools built around `wepp_2012` and pre-2006 soil parameterizations.
- Legacy watershed toolchains (for example FS-WEPP watershed workflows and related GIS wrappers) have historically depended on TOP2WEPP-style preprocessing.
- WEPPcloud is the only watershed workflow in this tool family that does not use TOP2WEPP. It uses ground-up topological processing and watershed abstraction with WEPPcloud-WBT and PERIDOT.
- WEPPcloud is also the only one in this list using the `wepp-forest` watershed model stack with deep-seepage and baseflow routines.

Tool choice should be based on scope: quick legacy hillslope screening versus full watershed analysis with modern topology, routing abstraction, and expanded hydrologic routines.

## Can WEPP simulate reservoirs and their effect on settling out sediments and modifying peak flows?

WEPP includes an option to simulate small sediment ponds downstream of agricultural fields. Historically this has not been incorporated into the online watershed interface and has seen limited application. It was not developed for impacts of large reservoirs on sediment and peak flows.

## Can the WEPP watershed interface simulate the impacts of roads on runoff and sediment delivery to a watershed?

WEPP has long been used for road-network erosion analysis. Legacy practice commonly used FS-WEPP tools (including WEPP:Road and WEPP:Road Batch) after manual road-segment delineation in a watershed (Brooks et al. 2016).

### WEPPcloud:Roads

WEPPcloud:Roads brings road analysis directly into a WEPPcloud watershed project. Instead of evaluating road segments separately and then interpreting those results by hand, users can work from an existing watershed run, add roads, and review how those roads may affect runoff and sediment delivery.

In practice, the workflow is intended to feel like a natural extension of the watershed interface: run the watershed model, add a road network, review the road settings, and then run a roads scenario. WEPPcloud:Roads keeps those road results separate from the baseline run so users can compare watershed outputs, review road-specific summaries, and understand where roads are contributing the most change across the landscape.

For full model contract and artifacts, see [WEPPcloud:Roads README](../../../../nodb/mods/roads/README.md).

## References

A dedicated references page is also available at [WEPPcloud References](references.md).

Brooks E.S., Dobre M., Elliot W.J., Wu J.Q., Boll J. 2016. Watershed-scale evaluation of the Water Erosion Prediction Project (WEPP) model in the Lake Tahoe basin. *Journal of Hydrology*, 533, 389-402.

Cannon S.H., Gartner J.E., Rupert M.G., Michael J.A., Rea A.H., Parrett C. 2010. Predicting the probability and volume of postwildfire debris flows in the intermountain western United States. *GSA Bulletin*, 122(1/2), 127-144.

Cochrane, T.A., Flanagan, D.C. (2005). Effect of DEM resolutions in the runoff and soil loss predictions of the WEPP watershed model. *Transactions of the ASAE*, 48(1), 109-120.

Flanagan D.C., Nearing M.A. 1995. USDA-Water Erosion Prediction Project. Hillslope profile and watershed model documentation. NSERL Report No. 10. USDA-ARS National Soil Erosion Research Laboratory, West Lafayette, Indiana.

Miller M.E., MacDonald L.H., Robichaud P.R., Elliot W.J. 2011. Predicting post-fire hillslope erosion in forest lands of the western United States. *International Journal of Wildland Fire*, 20, 982-999.

Nearing M.A., Foster G.R., Lane L.J., Finkner S.C. 1989. A process-based soil erosion model for USDA-Water Erosion Prediction Project technology. *Transactions of the ASAE*, 32(5), 1587-1590.

Quinn D.S. 2018. *Simulation of post-fire watershed hydrology and erosion responses with the physically based WEPP model*. MS Thesis, University of Idaho.

Robichaud P.R., Elliot W.J., Lewis S.A., Miller M.E. 2016. Validation of a probabilistic post-fire erosion model. *International Journal of Wildland Fire*, 25(3), 337-350. <http://dx.doi.org/10.1071/WF14171>
