# WEPP Management File Parameters
Derived from `wepppy/wepp/management/managements.py` __repr__ outputs with definitions from `plant-file.spec.md`.
The heading line is the default `usersum <parameter>` description; bullets expand on extended details or notes.

## Plant Section
### Cropland (`PlantLoopCropland`)
#### `crunit` — Cropland harvest units label (text)
- **Loop**: `plant` cropland
- **Extended**: Harvest units such as bu/ac, kg/ha, or t/ac; up to 15 characters.

#### `bb` — Cropland canopy cover coefficient (real)
- **Loop**: `plant` cropland
- **Extended**: Coefficient controlling crop canopy cover development.

#### `bbb` — Cropland canopy height parameter (real)
- **Loop**: `plant` cropland
- **Extended**: Parameter value for the canopy height equation.

#### `beinp` — Cropland biomass energy ratio (real)
- **Loop**: `plant` cropland
- **Extended**: Ratio relating biomass production to energy input.

#### `btemp` — Cropland base daily air temperature (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Base daily air temperature for crop growth calculations.

#### `cf` — Cropland flat residue cover coefficient (m²/kg, real)
- **Loop**: `plant` cropland
- **Extended**: Parameter for the flat residue cover equation factoring wind, snow, etc.

#### `crit` — Cropland growing degree days to emergence (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Heat units required before crop emergence occurs.

#### `critvm` — Cropland critical live biomass threshold (kg/m², real)
- **Loop**: `plant` cropland
- **Extended**: Minimum live biomass below which grazing is not permitted.

#### `cuthgt` — Cropland post-harvest standing residue height (m, real)
- **Loop**: `plant` cropland
- **Extended**: Height of standing residue after harvest; cutting height.

#### `decfct` — Cropland canopy remaining after senescence (fraction, real)
- **Loop**: `plant` cropland
- **Extended**: Fraction of canopy cover remaining after senescence (0-1).

#### `diam` — Cropland stem diameter at maturity (m, real)
- **Loop**: `plant` cropland
- **Extended**: Average plant stem diameter when mature.

#### `dlai` — Cropland LAI decline trigger (fraction, real)
- **Loop**: `plant` cropland
- **Extended**: Heat unit index at which leaf area index begins to decline.

#### `dropfc` — Cropland biomass remaining after senescence (fraction, real)
- **Loop**: `plant` cropland
- **Extended**: Fraction of biomass that remains after senescence (0-1).

#### `extnct` — Cropland radiation extinction coefficient (real)
- **Loop**: `plant` cropland
- **Extended**: Extinction coefficient used in radiation interception calculations.

#### `fact` — Cropland standing-to-flat residue adjustment (real)
- **Loop**: `plant` cropland
- **Extended**: Adjustment factor translating standing residue to flat residue effects.

#### `flivmx` — Cropland maximum live-plant friction factor (real)
- **Loop**: `plant` cropland
- **Extended**: Maximum Darcy–Weisbach friction factor attributed to living canopy.

#### `gddmax` — Cropland growing degree days for season (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Total growing degree days that define the crop growing season.

#### `hi` — Cropland harvest index (real)
- **Loop**: `plant` cropland
- **Extended**: Fraction of total biomass allocated to harvested yield.

#### `hmax` — Cropland maximum canopy height (m, real)
- **Loop**: `plant` cropland
- **Extended**: Maximum plant height reached by the crop canopy.

#### `mfocod` — Cropland fragile/non-fragile operation code (integer)
- **Loop**: `plant` cropland
- **Extended**: Selects which operation intensity set to use: 1=fragile crops, 2=non-fragile.

#### `oratea` — Cropland above-ground biomass decomposition constant (real)
- **Loop**: `plant` cropland
- **Extended**: Constant governing mass change of surface or buried above-ground biomass.

#### `orater` — Cropland root biomass decomposition constant (real)
- **Loop**: `plant` cropland
- **Extended**: Constant governing mass change of root biomass.

#### `otemp` — Cropland optimum growth temperature (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Optimal air temperature for plant growth.

#### `pltol` — Cropland plant drought tolerance factor (real)
- **Loop**: `plant` cropland
- **Extended**: Crop-specific drought tolerance factor.

#### `pltsp` — Cropland in-row plant spacing (m, real)
- **Loop**: `plant` cropland
- **Extended**: Spacing between plants within the row.

#### `rdmax` — Cropland maximum root depth (m, real)
- **Loop**: `plant` cropland
- **Extended**: Greatest depth reached by the crop root system.

#### `rsr` — Cropland root-to-shoot ratio (real)
- **Loop**: `plant` cropland
- **Extended**: Ratio of below-ground to above-ground biomass.

#### `rtmmax` — Cropland maximum perennial root mass (kg/m², real)
- **Loop**: `plant` cropland
- **Extended**: Upper limit on root biomass for perennial crops.

#### `spriod` — Cropland senescence duration (days, integer)
- **Loop**: `plant` cropland
- **Extended**: Number of days over which senescence occurs.

#### `tmpmax` — Cropland maximum temperature for growth (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Temperature threshold that halts perennial crop growth.

#### `tmpmin` — Cropland critical freezing temperature (°C, real)
- **Loop**: `plant` cropland
- **Extended**: Critical low temperature triggering damage to perennials.

#### `xmxlai` — Cropland maximum leaf area index (real)
- **Loop**: `plant` cropland
- **Extended**: Upper bound on LAI used in simulations.

#### `yld` — Cropland optimum yield under no stress (kg/m², real)
- **Loop**: `plant` cropland
- **Extended**: Target yield when no stress is applied; set 0.0 to let WEPP compute.

#### `rcc` — Cropland release canopy cover (real, 2016.3+)
- **Loop**: `plant` cropland
- **Extended**: Release canopy cover parameter introduced in the 2016.3 file format.

### Rangeland (`PlantLoopRangeland`)
#### `aca` — Rangeland surface residue mass change coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Coefficient describing how surface residue mass changes.

#### `aleaf` — Rangeland leaf area index coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Coefficient used in rangeland leaf area index calculations.

#### `ar` — Rangeland root mass change coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Controls seasonal change in root mass.

#### `bbb` — Rangeland canopy height parameter (real)
- **Loop**: `plant` rangeland
- **Extended**: Same canopy height equation parameter used for rangeland plants.

#### `bugs` — Rangeland insect residue removal rate (real)
- **Loop**: `plant` rangeland
- **Extended**: Daily fraction of surface residue removed by insects.

#### `cf1` — Rangeland first peak fraction of growing season (real)
- **Loop**: `plant` rangeland
- **Extended**: Fraction associated with the first seasonal biomass peak.

#### `cf2` — Rangeland second peak fraction of growing season (real)
- **Loop**: `plant` rangeland
- **Extended**: Fraction associated with the second seasonal biomass peak.

#### `cn` — Rangeland residue and root C:N ratio (real)
- **Loop**: `plant` rangeland
- **Extended**: Carbon-to-nitrogen ratio for residues and roots.

#### `cold` — Rangeland biomass at full canopy cover (kg/m², real)
- **Loop**: `plant` rangeland
- **Extended**: Standing biomass level where canopy cover reaches 100%.

#### `ffp` — Rangeland frost-free period (days, integer)
- **Loop**: `plant` rangeland
- **Extended**: Number of frost-free days per year.

#### `gcoeff` — Rangeland grass projected area coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Projected plant area coefficient for grasses.

#### `gdiam` — Rangeland grass canopy diameter (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average canopy diameter for grasses along the transect.

#### `ghgt` — Rangeland grass height (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average height of grasses.

#### `gpop` — Rangeland grass population density (real)
- **Loop**: `plant` rangeland
- **Extended**: Average number of grasses along a 100 m belt transect.

#### `gtemp` — Rangeland minimum growth temperature (°C, real)
- **Loop**: `plant` rangeland
- **Extended**: Minimum temperature required to initiate growth.

#### `hmax` — Rangeland maximum herbaceous plant height (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Maximum height attained by herbaceous plants.

#### `plive` — Rangeland maximum standing live biomass (kg/m², real)
- **Loop**: `plant` rangeland
- **Extended**: Upper limit on live biomass for rangeland stands.

#### `pltol` — Rangeland drought tolerance factor (real)
- **Loop**: `plant` rangeland
- **Extended**: Plant drought tolerance factor for rangeland species.

#### `pscday` — Rangeland day of first peak standing crop (Julian, integer)
- **Loop**: `plant` rangeland
- **Extended**: Julian day when the first seasonal biomass peak occurs.

#### `rgcmin` — Rangeland minimum live biomass (kg/m², real)
- **Loop**: `plant` rangeland
- **Extended**: Minimum amount of live biomass maintained in the stand.

#### `root10` — Rangeland root biomass in top 10 cm (kg/m², real)
- **Loop**: `plant` rangeland
- **Extended**: Root biomass contained within the upper 10 cm of soil.

#### `rootf` — Rangeland starting root mass fraction (real)
- **Loop**: `plant` rangeland
- **Extended**: Fraction of maximum root mass present at the start of the year.

#### `scday2` — Rangeland day of second peak standing crop (Julian, integer)
- **Loop**: `plant` rangeland
- **Extended**: Julian day when the second seasonal biomass peak occurs.

#### `scoeff` — Rangeland shrub projected area coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Projected area coefficient used for shrubs.

#### `sdiam` — Rangeland shrub canopy diameter (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average canopy diameter for shrubs.

#### `shgt` — Rangeland shrub height (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average shrub height.

#### `spop` — Rangeland shrub population density (real)
- **Loop**: `plant` rangeland
- **Extended**: Average number of shrubs along a 100 m belt transect.

#### `tcoeff` — Rangeland tree projected area coefficient (real)
- **Loop**: `plant` rangeland
- **Extended**: Projected plant area coefficient for trees.

#### `tdiam` — Rangeland tree canopy diameter (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average tree canopy diameter.

#### `tempmn` — Rangeland minimum senescence temperature (°C, real)
- **Loop**: `plant` rangeland
- **Extended**: Minimum temperature that initiates senescence.

#### `thgt` — Rangeland tree height (m, real)
- **Loop**: `plant` rangeland
- **Extended**: Average height of trees.

#### `tpop` — Rangeland tree population density (real)
- **Loop**: `plant` rangeland
- **Extended**: Average number of trees along a 100 m belt transect.

#### `wood` — Rangeland standing woody biomass fraction (real)
- **Loop**: `plant` rangeland
- **Extended**: Fraction of the initial standing woody biomass.
## Operation Section
### Cropland (`OpLoopCropland`)
#### `mfo1` — Cropland interrill tillage intensity for fragile crops (real)
- **Loop**: `op` cropland
- **Extended**: Interrill tillage intensity value applied to fragile crops.

#### `mfo2` — Cropland interrill tillage intensity for non-fragile crops (real)
- **Loop**: `op` cropland
- **Extended**: Interrill tillage intensity value applied to non-fragile crops.

#### `numof` — Cropland tillage implement row count (integer)
- **Loop**: `op` cropland
- **Extended**: Number of rows on the tillage implement.

#### `pcode` — Cropland implement/residue code (integer)
- **Loop**: `op` cropland
- **Extended**: Operation or residue-handling code: 1=planter, 2=drill, 3=cultivator, 4=other; 10=addition without surface disturbance, 11=flat residue removal without disturbance, 12=addition with disturbance, 13=flat residue removal with disturbance. The 2016.3 specification also reserves codes 14–19 for additional residue options.

#### `cltpos` — Cropland cultivator position (integer)
- **Loop**: `op` cropland
- **Extended**: Mounting position when `pcode`=3 (1=front-mounted, 2=rear-mounted).

#### `rho` — Cropland ridge height after tillage (m, real)
- **Loop**: `op` cropland
- **Extended**: Ridge height value immediately following the operation.

#### `rint` — Cropland ridge interval (m, real)
- **Loop**: `op` cropland
- **Extended**: Spacing between ridges after tillage.

#### `rmfo1` — Cropland rill tillage intensity for fragile crops (real)
- **Loop**: `op` cropland
- **Extended**: Rill tillage intensity used for fragile crops.

#### `rmfo2` — Cropland rill tillage intensity for non-fragile crops (real)
- **Loop**: `op` cropland
- **Extended**: Rill tillage intensity used for non-fragile crops.

#### `rro` — Cropland random roughness after tillage (m, real)
- **Loop**: `op` cropland
- **Extended**: Random roughness value immediately after the operation.

#### `surdis` — Cropland disturbed surface fraction (real)
- **Loop**: `op` cropland
- **Extended**: Fraction of the surface area that is disturbed (0–1).

#### `tdmean` — Cropland mean tillage depth (m, real)
- **Loop**: `op` cropland
- **Extended**: Average depth of the tillage pass.

#### `frmove` — Cropland residue removal fraction (real)
- **Loop**: `op` cropland
- **Extended**: Fraction of residue removed when `pcode` equals 11 or 13 (2016.3 residue removal operations).

#### `iresad` — Cropland residue addition crop index (integer)
- **Loop**: `op` cropland
- **Extended**: Plant scenario index specifying the residue type when `pcode` is 10 or 12 (residue addition).

#### `amtres` — Cropland residue addition amount (kg/m², real)
- **Loop**: `op` cropland
- **Extended**: Mass of residue added when `pcode` is 10 or 12.
## Initial Condition Section
### Cropland (`IniLoopCropland`)
#### `bdtill` — Cropland bulk density after last tillage (g/cm³, real)
- **Loop**: `ini` cropland
- **Extended**: Bulk density immediately following the most recent tillage operation.

#### `cancov` — Cropland initial canopy cover (fraction, real)
- **Loop**: `ini` cropland
- **Extended**: Fractional canopy cover at simulation start (0–1).

#### `daydis` — Cropland days since last tillage (days, real)
- **Loop**: `ini` cropland
- **Extended**: Elapsed days since the last tillage pass.

#### `dsharv` — Cropland days since last harvest (integer)
- **Loop**: `ini` cropland
- **Extended**: Elapsed days since the last harvest event.

#### `frdp` — Cropland initial frost depth (m, real)
- **Loop**: `ini` cropland
- **Extended**: Frost depth present on day one of the simulation.

#### `inrcov` — Cropland initial interrill cover (fraction, real)
- **Loop**: `ini` cropland
- **Extended**: Fractional interrill cover at the simulation start (0–1).

#### `iresd` — Cropland initial residue plant scenario index (integer)
- **Loop**: `ini` cropland
- **Extended**: Index of the Plant Growth Scenario that defines initial residue type.

#### `imngmt` — Cropland initial residue system (integer)
- **Loop**: `ini` cropland
- **Extended**: Initial residue cropping system flag (1=annual, 2=perennial, 3=fallow).

#### `rfcum` — Cropland cumulative rainfall since last tillage (mm, real)
- **Loop**: `ini` cropland
- **Extended**: Total rainfall accrued since the previous tillage pass.

#### `rhinit` — Cropland initial ridge height (m, real)
- **Loop**: `ini` cropland
- **Extended**: Ridge height at the start of the simulation.

#### `rilcov` — Cropland initial rill cover (fraction, real)
- **Loop**: `ini` cropland
- **Extended**: Fractional rill cover at simulation start (0–1).

#### `rrinit` — Cropland initial ridge roughness (m, real)
- **Loop**: `ini` cropland
- **Extended**: Ridge roughness height immediately after the last tillage.

#### `rspace` — Cropland rill spacing (m, real)
- **Loop**: `ini` cropland
- **Extended**: Spacing between rills; WEPP enforces 1.0 m if the input is ≤0.

#### `rtyp` — Cropland rill width type (integer)
- **Loop**: `ini` cropland
- **Extended**: Rill width behavior flag (1=temporary, 2=permanent constant width).

#### `snodpy` — Cropland initial snow depth (m, real)
- **Loop**: `ini` cropland
- **Extended**: Snow depth present at the start of the simulation.

#### `thdp` — Cropland initial depth of thaw (m, real)
- **Loop**: `ini` cropland
- **Extended**: Depth of thawed soil at the simulation start.

#### `tillay1` — Cropland secondary tillage layer depth (m, real)
- **Loop**: `ini` cropland
- **Extended**: Depth associated with secondary tillage; current WEPP versions internally fix this to 0.1 m.

#### `tillay2` — Cropland primary tillage layer depth (m, real)
- **Loop**: `ini` cropland
- **Extended**: Depth of the deepest tillage operation; current WEPP versions internally fix this to 0.2 m.

#### `width` — Cropland initial rill width (m, real)
- **Loop**: `ini` cropland
- **Extended**: Initial rill width; for permanent rills, 0.0 defaults to the rill spacing.

#### `sumrtm` — Cropland initial total dead root mass (kg/m², real)
- **Loop**: `ini` cropland
- **Extended**: Mass of dead roots present at the start of the simulation.

#### `sumsrm` — Cropland initial submerged residue mass (kg/m², real)
- **Loop**: `ini` cropland
- **Extended**: Mass of submerged residue present at the start of the simulation.

#### `usinrco` — Cropland initial understory interrill cover (fraction, real)
- **Loop**: `ini` cropland
- **Extended**: Understory interrill cover (0–1) available in the 2016.3 file format.

#### `usrilco` — Cropland initial understory rill cover (fraction, real)
- **Loop**: `ini` cropland
- **Extended**: Understory rill cover (0–1) available in the 2016.3 file format.

### Rangeland (`IniLoopRangeland`)
#### `frdp` — Rangeland initial frost depth (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Frost depth present at the start of the simulation.

#### `pptg` — Rangeland growing-season rainfall (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Average rainfall during the growing season.

#### `rmagt` — Rangeland initial above-ground residue mass (kg/m², real)
- **Loop**: `ini` rangeland
- **Extended**: Mass of standing residue above the ground surface at the start of the simulation.

#### `rmogt` — Rangeland initial ground residue mass (kg/m², real)
- **Loop**: `ini` rangeland
- **Extended**: Mass of residue lying on the ground surface at the start of the simulation.

#### `rrough` — Rangeland initial random roughness (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Random surface roughness for the rangeland condition.

#### `snodpy` — Rangeland initial snow depth (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Snow depth present at the start of the simulation.

#### `thdp` — Rangeland initial depth of thaw (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Depth of thawed soil for the initial condition.

#### `tillay1` — Rangeland secondary tillage layer depth (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Depth associated with secondary tillage; current WEPP versions internally fix this to 0.1 m.

#### `tillay2` — Rangeland primary tillage layer depth (m, real)
- **Loop**: `ini` rangeland
- **Extended**: Depth of the deepest tillage operation; current WEPP versions internally fix this to 0.2 m.

#### `resi` — Rangeland interrill litter cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional litter cover in interrill areas (0–1).

#### `roki` — Rangeland interrill rock cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional rock cover in interrill areas (0–1).

#### `basi` — Rangeland interrill basal cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional basal cover in interrill areas (0–1).

#### `cryi` — Rangeland interrill cryptogamic cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional cryptogamic cover in interrill areas (0–1).

#### `resr` — Rangeland rill litter cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional litter cover in rill areas (0–1).

#### `rokr` — Rangeland rill rock cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional rock cover in rill areas (0–1).

#### `basr` — Rangeland rill basal cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional basal cover in rill areas (0–1).

#### `cryr` — Rangeland rill cryptogamic cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Fractional cryptogamic cover in rill areas (0–1).

#### `cancov` — Rangeland total foliar canopy cover (fraction, real)
- **Loop**: `ini` rangeland
- **Extended**: Total foliar canopy cover for the rangeland condition (0–1).
## Surface Effects Section
### Cropland (`SurfLoopCropland`)
#### `mdate` — Cropland tillage date (Julian day, integer)
- **Loop**: `surf` cropland
- **Extended**: Julian day on which the tillage or surface operation occurs.

#### `op` — Cropland surface operation scenario index (integer)
- **Loop**: `surf` cropland
- **Extended**: Index of the Operation Scenario executed on `mdate`.

#### `tildep` — Cropland tillage depth (m, real)
- **Loop**: `surf` cropland
- **Extended**: Depth of soil disturbance for the operation.

#### `typtil` — Cropland tillage type (integer)
- **Loop**: `surf` cropland
- **Extended**: Tillage classification (1=primary, 2=secondary).
## Contour Section
### Cropland (`ContourLoopCropland`)
#### `cntslp` — Cropland contour slope (m/m, real)
- **Loop**: `contour` cropland
- **Extended**: Slope of the contour rows expressed as rise over run.

#### `rdghgt` — Cropland contour ridge height (m, real)
- **Loop**: `contour` cropland
- **Extended**: Ridge height for the contour system.

#### `rowlen` — Cropland contour row length (m, real)
- **Loop**: `contour` cropland
- **Extended**: Flow length along the contour row.

#### `rowspc` — Cropland contour row spacing (m, real)
- **Loop**: `contour` cropland
- **Extended**: Spacing between adjacent contour ridges.
## Drainage Section
### Cropland (`DrainLoopCropland`)
#### `ddrain` — Cropland depth to tile drain (m, real)
- **Loop**: `drain` cropland
- **Extended**: Depth from the soil surface to the tile drain.

#### `drainc` — Cropland drainage coefficient (m/day, real)
- **Loop**: `drain` cropland
- **Extended**: Design drainage capacity expressed as depth per day.

#### `drdiam` — Cropland drain tile diameter (m, real)
- **Loop**: `drain` cropland
- **Extended**: Diameter of the tile drain.

#### `sdrain` — Cropland drain tile spacing (m, real)
- **Loop**: `drain` cropland
- **Extended**: Spacing between tile laterals.
## Yearly Section
### Cropland Base (`YearLoopCropland`)
#### `itype` — Cropland plant scenario index (integer)
- **Loop**: `year` cropland
- **Extended**: Index into the Plant Growth Scenarios referenced by the yearly record.

#### `tilseq` — Cropland surface effect scenario index (integer)
- **Loop**: `year` cropland
- **Extended**: Index into the Surface Effect Scenarios (tillage sequence) used that year.

#### `conset` — Cropland contour scenario index (integer)
- **Loop**: `year` cropland
- **Extended**: Index into the Contour Scenarios assigned to the management year.

#### `drset` — Cropland drainage scenario index (integer)
- **Loop**: `year` cropland
- **Extended**: Index into the Drainage Scenarios associated with the year.

#### `imngmt` — Cropland cropping system flag (integer)
- **Loop**: `year` cropland
- **Extended**: Management system selector (1=annual crop, 2=perennial crop, 3=fallow). Values 1 and 3 populate the annual/fallow branch; value 2 populates the perennial branch.

### Cropland Base (`YearLoopCropland`) — Nested Branch Indicators
#### `annualfallow` — Cropland annual/fallow branch (object)
- **Loop**: `year` cropland
- **Extended**: Present when `imngmt` is 1 or 3; contains the annual/fallow scenario defined above.

#### `perennial` — Cropland perennial branch (object)
- **Loop**: `year` cropland
- **Extended**: Present when `imngmt` is 2; contains the perennial scenario and its cutting or grazing data.


### Cropland Annual Fallow (`YearLoopCroplandAnnualFallow`)
#### `jdharv` — Cropland annual/fallow harvest or fallow end date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Julian day for harvest or the end of the fallow period.

#### `jdplt` — Cropland annual/fallow planting or fallow start date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Julian day when planting occurs or the fallow period begins.

#### `rw` — Cropland annual/fallow row width (m, real)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Row spacing associated with the annual or fallow management.

#### `resmgt` — Cropland annual/fallow residue management option (integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Residue management action (1=herbicide, 2=burning, 3=silage, 4=cutting, 5=residue removal). Additional variants in the 2016.3 format are handled by operation records.

### Annual Fallow — Herbicide (`YearLoopCroplandAnnualFallowHerb`)
#### `jdherb` — Cropland herbicide application date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Julian day when the herbicide converts standing live biomass to dead residue.

### Annual Fallow — Burning (`YearLoopCroplandAnnualFallowBurn`)
#### `jdburn` — Cropland residue burning date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Date on which residues are burned.

#### `fbrnag` — Cropland fraction of standing residue burned (real)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Fraction of standing residue removed by burning (0–1).

#### `fbrnog` — Cropland fraction of flat residue burned (real)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Fraction of flat residue removed by burning (0–1).

### Annual Fallow — Silage (`YearLoopCroplandAnnualFallowSillage`)
#### `jdslge` — Cropland silage harvest date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Julian day when silage is harvested.

### Annual Fallow — Cutting (`YearLoopCroplandAnnualFallowCut`)
#### `jdcut` — Cropland residue shredding or cutting date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Date when standing residue is shredded or cut.

#### `frcut` — Cropland fraction of residue shredded or cut (real)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Fraction of standing residue affected by cutting (0–1).

### Annual Fallow — Residue Removal (`YearLoopCroplandAnnualFallowRemove`)
#### `jdmove` — Cropland residue removal date (Julian day, integer)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Date when flat residue is removed.

#### `frmove` — Cropland fraction of flat residue removed (real)
- **Loop**: `year` cropland annual/fallow
- **Extended**: Fraction of flat residue taken off the field (0–1).
### Cropland Perennial (`YearLoopCroplandPerennial`)
#### `jdharv` — Cropland perennial senescence or harvest date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Date when a perennial crop reaches senescence or is harvested; 0 indicates no senescence.

#### `jdplt` — Cropland perennial planting date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Date when the perennial crop is planted; set to 0 if already established.

#### `jdstop` — Cropland perennial termination date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Date when the perennial crop is permanently killed (e.g., tillage or herbicide); 0 if not terminated.

#### `rw` — Cropland perennial row width (m, real)
- **Loop**: `year` cropland perennial
- **Extended**: Row spacing for the perennial crop (0 defaults to in-row plant spacing).

#### `mgtopt` — Cropland perennial management option (integer)
- **Loop**: `year` cropland perennial
- **Extended**: Management flag (1=cutting, 2=grazing, 3=not harvested). The 2016.3 specification adds height-based options handled through operation records.

### Perennial — Cutting (`YearLoopCroplandPerennialCut`)
#### `ncut` — Perennial number of cuttings (integer)
- **Loop**: `year` cropland perennial
- **Extended**: Count of cutting events listed when `mgtopt`=1; appears immediately before the sequence of cut records.

#### `cutday` — Perennial cutting date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Julian day for each cutting in the sequence.

### Perennial — Grazing (`YearLoopCroplandPerennialGraze`)
#### `ncycle` — Perennial number of grazing cycles (integer)
- **Loop**: `year` cropland perennial
- **Extended**: Count of grazing cycles when `mgtopt`=2; appears before the grazing loop records.

#### `animal` — Perennial grazing animal units (real)
- **Loop**: `year` cropland perennial
- **Extended**: Number of animal units grazing during the cycle.

#### `area` — Perennial grazing field size (m², real)
- **Loop**: `year` cropland perennial
- **Extended**: Field area accessible to the grazing cycle.

#### `bodywt` — Perennial grazing animal body weight (kg, real)
- **Loop**: `year` cropland perennial
- **Extended**: Average body weight per animal unit.

#### `digest` — Perennial grazing digestibility (real)
- **Loop**: `year` cropland perennial
- **Extended**: Maximum digestibility fraction for grazed forage (0–1).

#### `gday` — Perennial grazing start date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Julian day marking the beginning of the grazing period.

#### `gend` — Perennial grazing end date (Julian day, integer)
- **Loop**: `year` cropland perennial
- **Extended**: Julian day marking the end of the grazing period.
### Rangeland Base (`YearLoopRangeland`)
#### `itype` — Rangeland plant scenario index (integer)
- **Loop**: `year` rangeland
- **Extended**: Index into the Plant Growth Scenarios used for the rangeland year.

#### `tilseq` — Rangeland surface effect scenario index (integer)
- **Loop**: `year` rangeland
- **Extended**: Index into the Surface Effect Scenarios (tillage sequences) applied.

#### `drset` — Rangeland drainage scenario index (integer)
- **Loop**: `year` rangeland
- **Extended**: Index into the Drainage Scenarios; use 0 when no drainage scenario is assigned.

#### `grazig` — Rangeland grazing flag (integer)
- **Loop**: `year` rangeland
- **Extended**: Indicates whether grazing management is active (0=no grazing, 1=grazing).

#### `ihdate` — Rangeland herbicide application date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Julian day for herbicide application when `grazig`=0; 0 skips the herbicide branch.

#### `jfdate` — Rangeland burn trigger date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Julian day on which a burn is evaluated when herbicide is inactive; 0 skips the burn branch.

### Rangeland Grazing (`YearLoopRangelandGraze`)
#### `area` — Rangeland pasture area (m², real)
- **Loop**: `year` rangeland
- **Extended**: Area available for grazing during the year.

#### `access` — Rangeland forage accessibility (real)
- **Loop**: `year` rangeland
- **Extended**: Fraction of forage accessible to animals (0–1).

#### `digmax` — Rangeland maximum digestibility (real)
- **Loop**: `year` rangeland
- **Extended**: Maximum digestibility of available forage (0–1).

#### `digmin` — Rangeland minimum digestibility (real)
- **Loop**: `year` rangeland
- **Extended**: Minimum digestibility threshold for forage (0–1).

#### `suppmt` — Rangeland supplemental feed (kg/day, real)
- **Loop**: `year` rangeland
- **Extended**: Average supplemental feed supplied per day.

#### `jgraz` — Rangeland number of grazing cycles (integer)
- **Loop**: `year` rangeland
- **Extended**: Count of grazing cycles executed in the year.

### Rangeland Grazing (`YearLoopRangelandGraze`) — Nested Cycles
#### `loops` — Rangeland grazing cycle records (list)
- **Loop**: `year` rangeland
- **Extended**: Sequence of `YearLoopRangelandGrazeLoop` entries describing each grazing cycle.

### Rangeland Grazing Cycles (`YearLoopRangelandGrazeLoop`)
#### `animal` — Rangeland grazing animal units (real)
- **Loop**: `year` rangeland
- **Extended**: Number of animal units participating in the grazing cycle.

#### `bodywt` — Rangeland animal body weight (kg, real)
- **Loop**: `year` rangeland
- **Extended**: Average body weight per animal unit.

#### `gday` — Rangeland grazing start date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Start day of the grazing cycle.

#### `gend` — Rangeland grazing end date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: End day of the grazing cycle.

#### `send` — Rangeland supplemental feeding end date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Julian day when supplemental feeding concludes.

#### `ssday` — Rangeland supplemental feeding start date (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Julian day when supplemental feeding begins.

### Rangeland Herbicide (`YearLoopRangelandHerb`)
#### `active` — Rangeland herbicide activation flag (integer)
- **Loop**: `year` rangeland
- **Extended**: Indicates whether herbicide effects are applied (0=inactive, 1=active).

#### `dleaf` — Rangeland live biomass reduction fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fractional reduction in live biomass due to herbicide (0–1).

#### `herb` — Rangeland evergreen biomass change fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fractional change applied to evergreen biomass (0–1).

#### `regrow` — Rangeland above/below ground biomass change fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fraction applied to combined above- and below-ground biomass (0–1).

#### `update` — Rangeland foliage increase fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fractional increase applied to foliage (0–1).

#### `woody` — Rangeland standing-dead decomposition flag (integer)
- **Loop**: `year` rangeland
- **Extended**: Flag controlling decomposition of standing dead biomass after herbicide.

#### `jfdate` — Rangeland burn evaluation date after herbicide (Julian day, integer)
- **Loop**: `year` rangeland
- **Extended**: Julian day used to trigger the burn branch if greater than 0.

### Rangeland Burn (`YearLoopRangelandBurn`)
#### `alter` — Rangeland post-burn accessible biomass fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fraction of live biomass accessible after burning (0–1).

#### `burned` — Rangeland standing wood reduction fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fractional reduction in standing woody biomass due to burning (0–1).

#### `change` — Rangeland potential biomass change fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fractional change applied to potential above-ground biomass (0–1).

#### `hurt` — Rangeland evergreen biomass remaining fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fraction of evergreen biomass that remains after burning (0–1).

#### `reduce` — Rangeland non-evergreen biomass remaining fraction (real)
- **Loop**: `year` rangeland
- **Extended**: Fraction of non-evergreen biomass that remains after burning (0–1).
## Management Section
### Management Scenario (`ManagementLoop`)
#### `name` — Management scenario name (text)
- **Loop**: `man`
- **Extended**: Identifier for the management scenario (up to eight characters).

#### `description` — Management scenario description lines (text)
- **Loop**: `man`
- **Extended**: Three 55-character comment lines describing the scenario.

#### `nofes` — Management number of OFEs (integer)
- **Loop**: `man`
- **Extended**: Number of overland flow elements (or channels) represented in the rotation.

#### `ofeindx` — Management initial-condition indices (list of integers)
- **Loop**: `man`
- **Extended**: Sequence of Initial Condition Scenario indices assigned to each OFE.

#### `nrots` — Management rotation repeat count (integer)
- **Loop**: `man`
- **Extended**: Number of times the management rotation is repeated.

#### `loops` — Management rotation definitions (`ManagementLoopMan`)
- **Loop**: `man`
- **Extended**: Nested rotation objects holding yearly schedules for each rotation pass.

### Rotation Definition (`ManagementLoopMan`)
#### `nyears` — Years per rotation (integer)
- **Loop**: `man`
- **Extended**: Number of simulation years contained within a single rotation cycle.

#### `years` — Rotation year matrices (`ManagementLoopManLoop`)
- **Loop**: `man`
- **Extended**: Collection of yearly OFE/crop records for each year in the rotation.

### Year/OFE Crop Assignment (`ManagementLoopManLoop`)
#### `nycrop` — Number of crops for the year (integer)
- **Loop**: `man`
- **Extended**: Count of crop segments grown on the OFE during the given year.

#### `manindx` — Yearly scenario indices (list of integers)
- **Loop**: `man`
- **Extended**: Yearly Management Scenario indices applied to each crop segment (1-based indices into `YearLoop`).
## Scenario Metadata
### Scenario Wrapper (`Loop` and derived classes)
#### `name` — Scenario loop name (text)
- **Loop**: wrapper
- **Extended**: Identifier for the scenario loop (plant, operation, initial condition, etc.).

#### `description` — Scenario loop description lines (text)
- **Loop**: wrapper
- **Extended**: Up to three comment lines documenting the scenario.

#### `landuse` — Scenario land use code (integer)
- **Loop**: wrapper
- **Extended**: Land use selector (0=not set, 1=cropland, 2=rangeland, 3=forest, 4=roads).

#### `ntill` — Surface effect operation count (integer)
- **Loop**: wrapper
- **Extended**: Number of operations within a Surface Effects sequence; present only for surface loops.

#### `data` — Scenario payload (object)
- **Loop**: wrapper
- **Extended**: Embedded data structure (loop or record) containing the parameters listed for the specific land use.

### Scenario Reference (`ScenarioReference`)
#### `index` — Scenario reference index (1-based integer)
- **Loop**: reference
- **Extended**: Numeric index into the referenced section; printed as the leading value in the `ScenarioReference` representation.

#### `section_type` — Referenced section enumeration
- **Loop**: reference
- **Extended**: Indicates which section (Plant, Op, Ini, Surf, Contour, Drain, Year) the index targets.

#### `loop_name` — Referenced loop name (text)
- **Loop**: reference
- **Extended**: Name of the loop resolved by the reference (if the index is non-zero).
### Management File Object (`Management`)
#### `datver` — Management file version string (text)
- **Loop**: management file
- **Extended**: Version identifier read from the .man file (e.g., 95.7, 98.4, 2016.3, 2024).

#### `nofe` — Management file OFE count (integer)
- **Loop**: management file
- **Extended**: Number of overland flow elements or channels declared in the file header.

#### `sim_years` — Management file simulation years (integer)
- **Loop**: management file
- **Extended**: Total number of simulation years (`nyears * nrots`) declared in the header.

#### `ncrop` — Plant scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Plant Growth Scenarios (`PlantLoop`).

#### `plants` — Plant scenario collection (`PlantLoops`)
- **Loop**: management file
- **Extended**: Complete set of plant scenarios; see Plant Section parameters.

#### `nop` — Operation scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Operation Scenarios (`OpLoop`).

#### `ops` — Operation scenario collection (`OpLoops`)
- **Loop**: management file
- **Extended**: Complete set of operation scenarios; see Operation Section parameters.

#### `nini` — Initial condition scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Initial Condition Scenarios (`IniLoop`).

#### `inis` — Initial condition scenario collection (`IniLoops`)
- **Loop**: management file
- **Extended**: Complete set of initial condition scenarios; see Initial Condition Section parameters.

#### `nseq` — Surface effect scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Surface Effect Scenarios (`SurfLoop`).

#### `surfs` — Surface effect scenario collection (`SurfLoops`)
- **Loop**: management file
- **Extended**: Complete set of surface effect sequences; see Surface Effects Section parameters.

#### `ncnt` — Contour scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Contour Scenarios (`ContourLoop`).

#### `contours` — Contour scenario collection (`ContourLoops`)
- **Loop**: management file
- **Extended**: Complete set of contour scenarios; see Contour Section parameters.

#### `ndrain` — Drainage scenario count (integer)
- **Loop**: management file
- **Extended**: Number of Drainage Scenarios (`DrainLoop`).

#### `drains` — Drainage scenario collection (`DrainLoops`)
- **Loop**: management file
- **Extended**: Complete set of drainage scenarios; see Drainage Section parameters.

#### `nscen` — Yearly management scenario count (integer)
- **Loop**: management file
- **Extended**: Number of yearly management scenarios (`YearLoop`).

#### `years` — Yearly scenario collection (`YearLoops`)
- **Loop**: management file
- **Extended**: Complete set of yearly management scenarios; see Yearly Section parameters.

#### `man` — Management rotation block (`ManagementLoop`)
- **Loop**: management file
- **Extended**: Final management rotation data; see Management Section parameters above.
