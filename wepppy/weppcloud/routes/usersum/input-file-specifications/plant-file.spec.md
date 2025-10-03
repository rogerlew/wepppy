# WEPP Plant/Management Input File
The plant/management input file contains all of the information needed by the WEPP model related to plant parameters (rangeland plant communities and cropland annual and perennial crops), tillage sequences and tillage implement parameters, plant and residue management, initial conditions, contouring, subsurface drainage, and crop rotations.

For readability, the WEPP management file is structured into **Sections**. A **Section** is a group of data which are related in some manner. The WEPP management file can become very complex, especially for multiple OFE simulations. It is recommend to use the WEPP user interface or other software to assist in creating these files.

Although the rangeland section formatting is still accepted, the WEPP model has not been updated for rangeland applications. The WEPP cropland management scenarios can be adapted for some rangeland applications. Another option is to use the more recently developed USDAARS RHEM model for rangeland applications.

The management file contains the following **Sections** in the following order:
* **Information Section** contains the WEPP version.
* **Plant Growth Section** - plant growth parameters.
* **Operation Section** - tillage and other implement parameters.
* **Initial Condition Section** - contains initial conditions and parameters which are OFE or channel specific.
* **Surface Effects Section** tillage sequences and other surface-disturbing datedsequences of implements.
* **Contour Section** - contouring parameters.
* **Drainage Section** - drainage parameters.
* **Yearly Section** - management information.
* **Management Section** - indexes into the Yearly Scenarios.

Within **Sections**, there may be several instances of data groupings. Each unique data grouping is referred to as a **Scenario**. For instance, the Contour **Section** may contain several different groups of contouring parameters. Each unique contour grouping is called a Contour **Scenario**. Likewise, each unique plant used by WEPP, and its associated parameters is called a Plant **Scenario**.

By arranging data into **Scenarios**, information which is accessed frequently by WEPP need only be stored once in the management file. When WEPP needs scenario information, it will access it through an index into the appropriate scenario. Similarly, scenarios may also be accessed by other scenarios within the management file. For example, the Surface Effects scenarios will index into an Operation **Scenario** when it needs to reference a specific operation. The Yearly **Scenario** can index into the Surface Effects, and Contouring scenarios. All scenarios are ultimately used by the Management **Section** through indices into the Yearly scenarios. With this scenario hierarchy, simple scenarios are found toward the top of the management file; more complex ones below them.

Some management file conventions:
1.  At most 10 data values per line.
2.  WEPP expects the following to be on lines by themselves: text information (such as scenario names and comments), looping parameters (such as `nini`, `ntill`, etc.), option flags (such as `lanuse`, `imngmt`, etc.), dates, and scenario indexes.
3.  Anything on a line after the `#` character is a comment. Comments may not follow text information that is read by the model.

## wepppy Management parser and 2016.3+ downgrade conversion

`wepppy/wepp/management/managements.py` implements the high-level parser for WEPP plant/management files. The parser mirrors the manual by reading each section in canonical order—plants, operations, initial conditions, surface effects, contours, drains, yearly scenarios, and the management loop. Each scenario is represented by loop classes that hold both metadata and typed parameter blocks, allowing downstream code to manipulate scenarios without string parsing while enforcing the specification (option bounds, expected line lengths, and required values).

### 2016.3/2017.1 awareness

Recent updates teach the parser about parameters introduced in the 2016.3/2017.1 formats, including release canopy cover (`rcc`), residue resurfacing fractions (`resurf1`/`resurnf1`), understory cover fractions in initial conditions, and the optional permanent-contour flag. These values are ingested into the in-memory management objects so newer management libraries preserve the richer behaviour during simulations.

### Downgrading managements to 98.4

`convert_to_98_4_format` constructs a sanitized copy of a parsed management and exports it using the 98.4 layout. Two downgrade modes are available. Strict mode aborts as soon as an unsupported 2016.3 feature is encountered (for example a non-zero resurfacing fraction or herbicide operation code 17). Fallback mode zeroes resurfacing fractions, maps herbicide operations to code 4 (`other`), and injects comment notes documenting the original values so users understand the loss in fidelity. The helper writes the explanatory comments at the top of the downgraded file before emitting the standard 98.4 content.

### Multi-OFE stacking utilities

`wepppy/wepp/management/utils/multi_ofe.py` provides helpers for synthesizing multi-OFE (Overland Flow Element) managements programmatically. The `ManagementMultipleOfeSynth` class takes an existing single-OFE management, replicates the management loop, and stitches together multiple OFE variants while preserving consistent plant, operation, and initial-condition references—allowing automated generation of multi-element hillslope scenarios without manual editing.

## Plant/Management Input File Sections
The general form of a **Section** is:
* `Scen.number` - the number of scenarios declared
* `Scen.loop.name` - the scenario name
* `Scen.loop.description` - text comments
* `Scen.loop.data` - the scenario data parameters

To read a scenario, WEPP will loop the number of times specified by the value `Scen.number`, reading the "loop" data into memory for future use.

The plant/management file for WEPP v95.7 is described in Table 16. Please note that although this management file convention allows the "mixing" of **Scenarios** of different land usage, this flexibility is not currently supported by the WEPP erosion model. Also, there are several scenarios that have empty "slots" where information will eventually be placed when WEPP supports those options.

### Information Section
* **Info.version:**
    * 1.1) WEPP version, (up to) 8 characters - (`datver`)
        * `95.7` Initial version
        * `98.4` - Update
        * `2016.3` and `2017.1` Residue management updates, additional parameters
        * ***Note*** `datver` is used to detect older management file formats, which are incompatible with the current WEPP erosion model.
* **Info.header**
    * 2.1) number of Overland Flow Elements for hillslopes, integer (`nofe`), or number of channels for watershed (`nchan`)
    * 3.1) number of TOTAL years in simulation, integer (`nyears` * `nrots`)

### Plant Growth Section
***Note*** `ncrop` is the number of unique plant types grown during the simulation period. For example, if the crops grown during the simulation are corn and wheat, `ncrop` = 2. A different type of residue on a field besides the current crop growth being simulated also needs to be assigned a crop number. For example if you are planting continuous corn into a field that is coming out of set-aside acreage that had a clover cover crop present the fall before that was killed with herbicides that fall, you need to input the clover crop parameters so that the decomposition section of the model will have the correct parameters (thus `ncrop` would be 2).
* **Plant.number:**
    * 0.1) number of unique plant types, integer (`ncrop`)
* **Plant.loop.name:**
    * 1.1) plant name, (up to) 35 characters (`crname`)
* **Plant.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Plant.loop.landuse:**
    * 5.1) for use on land type..., integer - (`iplant`)
        * 1) crop
        * 2) range
        * 3) forest
        * 4) roads

#### Plant.loop.cropland: (read when iplant=1; cropland)
* 6.1) harvest units, (i.e., bu/a, kg/ha, t/a, etc.) up to 15 characters - (`crunit`)
* 7.1) canopy cover coefficient, real - (`bb`)
* 7.2) parameter value for canopy height equation, real - (`bbb`)
* 7.3) biomass energy ratio, real - (`beinp`)
* 7.4) base daily air temperature (degrees C), real - (`btemp`)
* 7.5) parameter for flat residue cover equation ($m^2/kg$), real - (`cf`)
* 7.6) growing degree days to emergence (degrees C), real - (`crit`)
* 7.7) critical live biomass value below which grazing is not allowed ($kg/m^2$), real - (`critvm`)
* 7.8) height of post-harvest standing residue; cutting height (m), real - (`cuthgt`)
* 7.9) fraction canopy remaining after senescence (0-1), real (`decfct`)
* 7.10) plant stem diameter at maturity (m), real - (`diam`)
* 8.1) heat unit index when leaf area index starts to decline (0-1), real - (`dlai`)
* 8.2) fraction of biomass remaining after senescence (0-1), real - (`dropfc`)
* 8.3) radiation extinction coefficient, real - (`extnct`)
* 8.4) standing to flat residue adjustment factor (wind, snow, etc.), real (`fact`)
* 8.5) maximum Darcy Weisbach friction factor for living plant, real - (`flivmx`)
* 8.6) growing degree days for growing season (degrees C), real - (`gddmax`)
* 8.7) harvest index, real - (`hi`)
* 8.8) maximum canopy height (m), real - (`hmax`)
* 9.1) use fragile or non-fragile operation mfo values, integer - (`mfocod`)
    * 1) fragile
    * 2) non-fragile
* 10.1) decomposition constant to calculate mass change of above-ground biomass (surface or buried), real - (`oratea`)
* 10.2) decomposition constant to calculate mass change of root-biomass, real - (`orater`)
* 10.3) optimal temperature for plant growth (degrees C), real (`otemp`)
* 10.4) plant specific drought tolerance, real (`pitol`)
* 10.5) in-row plant spacing (m), real - (`pltsp`)
* 10.6) maximum root depth (m), real - (`rdmax`)
* 10.7) root to shoot ratio, real - (`rsr`)
* 10.8) maximum root mass for a perennial crop ($kg/m^2$), real - (`rtmmax`)
* 10.9) period over which senescence occurs (days), integer (`spriod`)
* 10.10) maximum temperature that stops the growth of a perennial crop (degrees C), real (`tmpmax`)
* 11.1) critical freezing temperature for a perennial crop (degrees C), real - (`tmpmin`)
* 11.2) maximum leaf area index, real - (`xmxlai`)
* 11.3) optimum yield under no stress conditions ($kg/m^2$), real - (`yld`)
* 11.4) Release canopy cover, real (version 2016.3) - (`rcc`)
* ***Note*** (input 0.0 on Line 11.3 to use model calculated optimum yield)

#### Plant.loop.rangeland: (read when iplant = 2; rangeland)
* 6.1) change in surface residue mass coefficient, real - (`aca`)
* 6.2) coefficient for leaf area index, real - (`aleaf`)
* 6.3) change in root mass coefficient, real - (`ar`)
* 6.4) parameter value for canopy height equation, real - (`bbb`)
* 6.5) daily removal of surface residue by insects, real - (`bugs`)
* 6.6) frac. of 1st peak of growing season, real - (`cf1`)
* 6.7) frac. of 2nd peak of growing season, real - (`cf2`)
* 6.8) c:n ratio of residue and roots, real - (`cn`)
* 6.9) standing biomass where canopy cover is 100%, ($kg/m^2$) real - (`cold`)
* 6.10) frost free period, (days) integer - (`ffp`)
* 7.1) projected plant area coefficient for grasses, real - (`gcoeff`)
* 7.2) average. canopy diameter for grasses, (m) real - (`gdiam`)
* 7.3) average height for grasses (m), real (`ghgt`)
* 7.4) average number of grasses along a 100 m belt transect, real - (`gpop`)
* 7.5) minimum temperature to initiate growth, (degrees C) real - (`gtemp`)
* 7.6) maximum herbaceous plant height (m), real - (`hmax`)
* 7.7) maximum standing live biomass, ($kg/m^2$) real - (`plive`)
* 7.8) plant drought tolerance factor, real (`pitol`)
* 7.9) day of peak standing crop, 1st peak, (julian day) integer - (`pscday`)
* 7.10) minimum amount of live biomass, ($kg/m^2$) real - (`rgcmin`)
* 8.1) root biomass in top 10 cm, ($kg/m^2$) real (`root10`)
* 8.2) fraction of live and dead roots from maximum at start of year, real - (`rootf`)
* 8.3) day on which peak occurs, 2nd growing season (julian day), integer - (`scday2`)
* 8.4) projected plant area coefficient for shrubs, real - (`scoeff`)
* 8.5) average canopy diameter for shrubs (m), real - (`sdiam`)
* 8.6) average height of shrubs (m), real (`shgt`)
* 8.7) average number of shrubs along a 100 m belt transect, real - (`spop`)
* 8.8) projected plant area coefficient for trees, real - (`tcoeff`)
* 8.9) average canopy diameter for trees (m), real - (`tdiam`)
* 8.10) minimum temperature to initiate senescence, (degrees C) real - (`tempmn`)
* 9.1) average height for trees (m), real - (`thgt`)
* 9.2) average number of trees along a 100 m belt transect, real - (`tpop`)
* 9.3) fraction of initial standing woody biomass, real - (`wood`)

#### Plant.loop.forest: (read when iplant = 3; forest)
* ***Note*** no values; plants for Forestland not yet supported.

#### Plant.loop.roads: (read when iplant = 4; roads)
* ***Note*** no values; plants for Roads not yet supported.

***Note*** Plant.loop values repeat `ncrop` times.

### Operation Section
* **Op.number:**
    * 0.1) number of unique operation types, integer (`nop`)
* **Op.loop.name:**
    * 1.1) operation name, (up to) 35 characters (`opname`)
* **Op.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Op.loop.landuse:**
    * 5.1) for use on land type, integer - (`iop`)
        * 1) crop
        * 2) range
        * 3) forest
        * 4) roads

#### Op.loop.cropland: (read when iop=1; cropland)
* 6.1) interrill tillage intensity for fragile crops, real - (`mfo1`)
* 6.2) interrill tillage intensity for non-fragile crops, real (`mfo2`)
* 6.3) number of rows of tillage implement, integer - (`numof`)
* 7.1) implement/residue code, integer - (`code1`/`resma1`)
    * 1) planter
    * 2) drill
    * 3) cultivator
    * 4) other
    * Note: Following codes only valid for version 2016.3
        * 10) residue addition without surface disturbance
        * 11) residue removal (flat only) without surface disturbance
        * 12) residue addition with disturbance
        * 13) residue removal (flat only) with disturbance
        * 14) shredding/cutting
        * 15) burning
        * 16) silage
        * 17) herbicide application
        * 18) residue removal by fraction (standing and flat) without surface disturbance
        * 19) residue removal by fraction (standing and flat) - with surface disturbance
* 7.2) cultivator position, integer - (`cltpos`) (read when `code1`/`resma1` = 3; cultivator)
    * 1) front mounted
    * 2) rear mounted
* 8.1) ridge height value after tillage (m), real - (`rho`)
* 8.2) ridge interval (m), real - (`rint`)
* 8.3) rill tillage intensity for fragile crops, real - (`rmfo1`)
* 8.4) rill tillage intensity for non-fragile crops, real - (`rmfo2`)
* 8.5) random roughness value after tillage (m), real - (`rro`)
* 8.6) fraction of surface area disturbed (0-1), real - (`surdis`)
* 8.7) mean tillage depth (m), real - (`tdmean`)
* Note: Resurface parameters only for version 2016.3 format
    * 8.8) Fraction residue resurfaced for fragile crops (0-1), real - (`resurf1`)
    * 8.9) Fraction residue resurfaced for non-fragile crop (0-1), real - (`resurnf1`)
* Note: Lines 9 and 10 only for version 2016.3 format
* 9.1) Read when `resma1` is 10,11,12,13,14,15,18,19:
    * When `resma1` = 10,12: crop index specifying residue type - (`iresa1`)
    * When `resma1` = 11,13: fraction of residue removed (0-1) - (`frmov1`)
    * When `resma1` = 14: fraction of residue shredded (0-1) - (`frmov1`)
    * When `resma1` = 15: fraction of standing residue burned (0-1) (`fbma1`)
    * When `resma1` = 18,19: fraction of flat residue removed (0-1) (`frfmov1`)
* 10.1) Read when `resma1` is 10, 12, 15, 18, 19:
    * When `resma1` = 10,12: amount of residue added (kg/m^2) - (`resad1`)
    * When `resma1` = 15: fraction of flat residue burned (0-1) (`fbrnol`)
    * When `resma1` = 18,19: fraction of standing residue removed (0-1) (`frsmov1`)

#### Op.loop.rangeland: (read when iop=2; rangeland)
* ***Note*** no values; operations for Rangeland not yet supported.

#### Op.loop.forest: (read when iop=3; forest)
* ***Note*** no values; operations for Forestland not yet supported.

#### Op.loop.roads: (read when iop = 4; roads)
* ***Note*** no values; operations for Roads not yet supported.

***Note*** Op.loop values repeat `nop` times.

### Initial Condition Section
***Note*** `nini` is the number of different initial conditions to be read into the WEPP model. The initial conditions are the conditions which exist at the beginning of the simulation. Estimates of the initial conditions for a continuous simulation can be made by using long term average conditions which exist on January 1st. For a single storm simulation, the user must input the correct values for initial conditions since they will greatly affect the model output. For continuous model simulations, especially ones in which significant soil and residue disturbance are caused by tillage and the simulation is for several years, the effect of initial conditions on model output is minimal.¹
¹ The WEPP Shell Interface can optionally create these scenarios from WEPP model runs.

* **Ini.number:**
    * 0.1) number of initial condition scenarios, integer - (`nini`)
* **Ini.loop.name:**
    * 1.1) scenario name, (up to) 8 characters (`oname`)
* **Ini.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Ini.loop.landuse:**
    * 5.1) land use, integer - (`lanuse`)
        * 1) crop
        * 2) range
        * 3) forest
        * 4) roads

#### Ini.loop.landuse.cropland: (read when lanuse = 1; cropland)
* 6.1) bulk density after last tillage ($g/cm^3$), real - (`bdtill`)
* 6.2) initial canopy cover (0-1), real - (`cancov`)
* 6.3) days since last tillage, real - (`daydis`)
* 6.4) days since last harvest, integer - (`dsharv`)
* 6.5) initial frost depth (m), real - (`frdp`)
* 6.6) initial interrill cover (0-1), real - (`inrcov`)
* 7.1) Plant Growth Scenario index of initial residue type, integer - (`iresd`)
* ***Note*** `iresd` refers to a Plant Growth Scenario.
* 8.1) initial residue cropping system, integer - (`imngmt`)
    * 1) annual
    * 2) perennial
    * 3) fallow
* 9.1) cumulative rainfall since last tillage (mm), real - (`rfcum`)
* 9.2) initial ridge height after last tillage (m), real - (`rhinit`)
* 9.3) initial rill cover (0-1), real - (`rilcov`)
* 9.4) initial ridge roughness after last tillage (m), real - (`rrinit`)
* 9.5) rill spacing (m), real - (`rspace`)
* ***Note*** if `rspace` is 0.0 or less, WEPP will set rill spacing to 1.0 meter.
* 10.1) rill width type, integer - (`rtyp`)
    * 1) temporary
    * 2) permanent
* ***Note*** For most cases, input a value of "1" for rill width type. To use a constant rill width, unaffected by flow or tillage, input "2" here for permanent rills.
* 11.1) initial snow depth (m), real - (`snodpy`)
* 11.2) initial depth of thaw (m), real - (`thdp`)
* 11.3) depth of secondary tillage layer (m), real - (`tillay(1)`)
* 11.4) depth of primary tillage layer (m), real - (`tillay(2)`)
* 11.5) initial rill width (m), real (`width`)
* ***Note*** The primary tillage layer (`tillay(2)`) is the depth of the deepest tillage operation. The secondary tillage layer is the average depth of all secondary tillage operations. If no tillage, set `tillay(1)`=0.1 and `tillay(2)`=0.2. The current version of WEPP (v95.7/v2012/v2024) internally fixes tillay(1)=0.1 and tillay(2)=0.2, so the input values here at present have no impact on model simulations.
* ***Note*** If rill width type (`rtyp`) is temporary, WEPP will estimate a value for rill width as a function of flow discharge rate for each storm, and reset rill width to 0.0 when a tillage occurs. If `width` is 0.0 and rill width type (`rtyp`) is permanent, WEPP will set the permanent rill width to the rill spacing, functionally forcing the model to assume broad sheet flow for flow shear stress and transport computations.
* 12.1) initial total dead root mass ($kg/m^2$) real - (`sumrtm`)
* 12.2) initial total submerged residue mass ($kg/m^2$), real - (`sumsrm`)
* Note: Forest understory parameters only for version 2016.3 format
    * 12.3) Initial understory interrill cover (0-1), real - (`usinrcol`)
    * 12.4) Initial understory rill cover (0-1), real - (`usrilcol`)
* ***Note*** See page (100) for information on estimating `sumrtm` and `sumsrm`.

#### Ini.loop.landuse.rangeland: (read when lanuse = 2; rangeland)
* 6.1) initial frost depth (m), real - (`frdp`)
* 6.2) average rainfall during growing season (m), real - (`pptg`)
* 6.3) initial residue mass above the ground ($kg/m^2$), real - (`rmagt`)
* 6.4) initial residue mass on the ground ($kg/m^2$), real - (`rmogt`)
* 6.5) initial random roughness for rangeland (m), real (`rrough`)
* 6.6) initial snow depth (m), real - (`snodpy`)
* 6.7) initial depth of thaw (m), real - (`thdp`)
* 6.8) depth of secondary tillage layer (m), real - (`tillay(1)`)
* 6.9) depth of primary tillage layer (m), real - (`tillay(2)`)
* ***Note*** The primary tillage layer (`tillay(2)`) is the depth of the deepest tillage operation. The secondary tillage layer is the average depth of all secondary tillage operations. If no tillage, set `tillay(1)`=0.1 and `tillay(2)`=0.2. The current version of WEPP (v95.7) internally fixes `tillay(1)` = 0.1 and `tillay(2)`=0.2, so the input values here at present have no impact on model simulations.
* 7.1) interrill litter surface cover (0-1), real - (`resi`)
* 7.2) interrill rock surface cover (0-1), real - (`roki`)
* 7.3) interrill basal surface cover (0-1), real - (`basi`)
* 7.4) interrill cryptogamic surface cover (0-1), real - (`cryi`)
* 7.5) rill litter surface cover (0-1), real - (`resr`)
* 7.6) rill rock surface cover (0-1), real - (`rokr`)
* 7.7) rill basal surface cover (0-1), real - (`basr`)
* 7.8) rill cryptogamic surface cover (0-1), real - (`cryr`)
* 7.9) total foliar (canopy) cover (0-1), real (`cancov`)

#### Ini.loop.landuse.forest: (read when lanuse = 3; forest)
* ***Note*** no values; initial conditions for Forestland not yet supported.

#### Ini.loop.landuse.roads: (read when lanuse=4; roads)
* ***Note*** no values; initial conditions for Roads not yet supported.

***Note*** Ini.loop values repeat `nini` times.

### Surface Effects Section
***Note*** A Surface Effect Scenario is a sequence of surface-disturbing (tillage) operations performed on one field or overland flow element during one calendar year.

* **Surf.number:**
    * 0.1) number of Surface Effect Scenarios, integer (`nseq`)
* **Surf.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`sname`)
* **Surf.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Surf.loop.landuse:**
    * 5.1) for use on land type, integer - (`iseq`)
        * 1) crop
        * 2) range
        * 3) forest
        * 4) roads
* **Surf.loop.number:**
    * 6.1) number of operations for surface effect scenario, integer - (`ntill`)

#### Surf.loop.loop.cropland: (read when iseq = 1; cropland)
* 7.1) day of tillage (julian), integer - (`mdate`)
* 8.1) Operation Scenario index, integer - (`op`)
* ***Note*** `op` refers to the Operation Scenario.
* 9.1) tillage depth (m), real - (`tildep`)
* 10.1) tillage type, integer (`typtil`)
    * 1) primary
    * 2) secondary
* ***Note*** Primary tillage is the operation which tills to the maximum depth. Secondary tillage is all other tillage operations.

#### Surf.loop.loop.rangeland: (read when iseq = 2; rangeland)
* ***Note*** no values; surface effects for Rangeland not yet supported.

#### Surf.loop.loop.forest: (read when iseq = 3; forest)
* ***Note*** no values; surface effects for Forestland not yet supported.

#### Surf.loop.loop.roads: (read when iseq = 4; roads)
* ***Note*** no values; surface effects for Roads not yet supported.

***Note*** Surf.loop.loop values repeat `ntill` times. Surf.loop values repeat `nseq` times.

### Contour Section
***Note*** A Contour Scenario is the combination of slope length, slope steepness, and ridge height which is associated with one (or more) overland flow element(s) or a field in a hillslope simulation. Contour Scenarios are used when the effects of contour farming or cross-slope farming are to be examined. The contour routines within the WEPP model at this time are fairly simple. The inputs for the Contour Scenarios are the row grade of the contours (assumed uniform), the contour row spacing (distance between ridges), the contour row length (the distance runoff flows down a contour row), and the contour ridge height. WEPP computes the amount of water storage within a contour row. If the runoff produced by a rainfall event exceeds the storage the contours are predicted to fail and a message is sent to the output which informs the user that his contour system has failed. There are now two options for contour simulations, and what happens when contours are predicted to fail. In v2012.8 and earlier versions of WEPP, erosion estimates are made continuing to assume that all flow is down the contour rows (even when they were predicted to fail). The model will count the number of contour failures and report this to the user in the output file. A newer contour simulation option available in v2024 predicts runoff and soil loss up-and-down a hillslope profile after contour failure. Erosion estimates will continue to be made up-and-down the profile until a subsequent tillage operation occurs that will reset the simulation, so that predictions will again made down the contour rows. For the NRCS web-based interface, NRCS set the contour row spacing equal to the rill spacing, set the contour row length to 50 feet, set the contour ridge height to the OFE soil ridge height, and forced contour failure if the ridge height on a day was 2 inches or less. There is an option setting within the updated Windows interface allowing a user to choose which contour simulation option they prefer. If a user receives a message that their contour system has failed, their options are to redesign the contour system so that the contour rows are shorter and/or the contour ridge height is greater, or use the watershed application of WEPP to simulate the flow down the contour rows then into the failure channel, gully, or grassed waterway. When the contour option is used, all of the flow and sediment for an overland flow element are assumed to be routed to the side of the slope. When contours hold on an OFE, no sediment will be predicted to exit the bottom of that overland flow element, and an average detachment rate is calculated at the 100 points down the hillside based on the sediment exiting off the side of the OFE. Users are advised not to simulate contoured OFEs below non-contoured ones, since there is a large likelihood of failure of the contours due to inflow of water from above overtopping the contour ridges.

* **Cont.number:**
    * 0.1) number of Contour Scenarios - (`ncnt`)
* **Cont.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`cname`)
* **Cont.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Cont.loop.landuse:**
    * 5.1) for use on land type..., integer - (`icont`)
        * 1) crop
        * ***Note*** `icont` must be 1, as only cropland supports contouring.

#### Cont.loop.cropland: (read when icont = 1; cropland)
* 6.1) contour slope ($m/m$), real - (`cntslp`)
* 6.2) contour ridge height (m), real - (`rdghgt`)
* 6.3) contour row length (m), real - (`rowlen`)
* 6.4) contour row spacing (m), real - (`rowspc`)
* Note: permanent flag is only for 2016.3 format
    * 6.5) permanent flag (0 or 1), integer (`contours_perm`)

***Note*** Cont.loop values repeat `ncnt` times.

### Drainage Section
* **Drain.number:**
    * 0.1) number of Drainage Scenarios - (`ndrain`)
* **Drain.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`dname`)
* **Drain.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Drain.loop.landuse:**
    * 5.1) for use on land type..., integer - (`dcont`)
        * 1) crop
        * 2) range
        * 4) roads
        * ***Note*** `dcont` must be 1, 2, or 4, as forestland does not support drainage.

#### Drain.loop.drainage: (read when dcont = 1; cropland)
* 6.1) depth to tile drain (m), real - (`ddrain`)
* 6.2) drainage coefficient ($m/day$), real - (`drainc`)
* 6.3) drain tile diameter (m), real - (`drdiam`)
* 6.4) drain tile spacing (m), real - (`sdrain`)

#### Drain.loop.rangeland: (read when dcont = 2; rangeland)
* ***Note*** no values; drainage for Rangeland not yet supported.

#### Drain.loop.roads: (read when dcont = 4; roads)
* ***Note*** no values; drainage for Roads not yet supported.

***Note*** Drain.loop values repeat `ndrain` times.

### Yearly Section
***Note*** `nscen` is the number of management scenarios used by the simulation. A management scenario contains all information associated with a particular Year/OFE/Crop - its Surface Effect, Contour, Drainage, Plant Growth scenarios and management data.

* **Year.number:**
    * 0.1) number of Yearly Scenarios - (`nscen`)
* **Year.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`mname`)
* **Year.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Year.loop.landuse:**
    * 5.1) for use on land type..., integer - (`iscen`)
        * 1) crop
        * 2) range
        * 3) forest
        * 4) roads

#### Year.loop.cropland: (read when iscen = 1; cropland)
* 6.1) Plant Growth Scenario index, integer (`itype`)
* ***Note*** `itype` refers to a Plant Growth Scenario. The value for `itype` corresponds to the order that the plants are read into WEPP from the Plant Growth Section. For example, if the plants being grown are corn and soybeans and in the Plant Growth Section the first plant read in is corn and the second soybeans, then corn will have a reference index of 1 and soybeans will have a reference index of 2. So for any year when corn is being grown, `itype` will equal 1 and for any year when soybeans are being grown, `itype` will equal 2.
* 7.1) Surface Effect Scenario index, integer - (`tilseq`)
* ***Note*** `tilseq` refers to a Surface Effects Scenario order number index. If `nseq` = 0, then `tilseq` must be 0.
* 8.1) Contour Scenario index, integer (`conset`)
* ***Note*** `conset` refers to a Contour Scenario order number index. If `ncnt` = 0 on line 0.1 of the Contour Section, then `conset` must be 0.
* 9.1) Drainage Scenario index, integer - (`drset`)
* ***Note*** `drset` refers to a Drainage Scenario order number index. If `ndrain` = 0 on line 0.1 of the Drainage Section, then `drset` must be 0.
* 10.1) cropping system, integer - (`imngmt`)
    * 1) annual
    * 2) perennial
    * 3) fallow

##### Year.loop.cropland.annual/fallow: (read when imngmt = 1 or imngmt = 3; annual/fallow crops)
* 11.1) harvesting date or end of fallow period (julian day), integer - (`jdharv`)
* 12.1) planting date or start of fallow period (julian day), integer - (`jdplt`)
* 13.1) row width (m), real - (`rw`)
* 14.1) residue management option, integer - (`resmgt`)
* Note: Options 1-6 only for version 95.7 and 98.4 format. For 2016.3 format see the operation section for more options.
    * 1) herbicide application
    * 2) burning
    * 3) silage
    * 4) shredding or cutting
    * 5) residue removal
    * 6) none
    * 7) annual cutting - only in version 2016.3

###### Year.loop.cropland.annual/fallow.herb: (read when resmgt = 1; herbicide application)
* 15.1) herbicide application date (julian), integer - (`jdherb`)
* ***Note*** Herbicide application here refers to use of a contact herbicide which the WEPP model will simulate as immediately converting all standing live biomass to dead residue.
* Note only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow herbicide applications.

###### Year.loop.cropland.annual/fallow.burn: (read when resmgt = 2; burning)
* 15.1) residue burning date (julian day), integer - (`jdburn`)
* 16.1) fraction of standing residue lost by burning (0-1), real - (`fbmag`)
* 17.1) fraction of flat residue lost by burning (0-1), real - (`fbrnog`)
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify annual/fallow burning operations.

###### Year.loop.cropland.annual/fallow.silage: (read when resmgt = 3; silage)
* 15.1) silage harvest date (julian day), integer - (`jdslge`)
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow silage operation.

###### Year.loop.cropland.annual/fallow.cut: (read when resmgt = 4; cutting)
* 15.1) standing residue shredding or cutting date (julian day), integer - (`jdcut`)
* 16.1) fraction of standing residue shredded or cut (0-1), real - (`frcut`)
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow residue shredding or cutting operation.

###### Year.loop.cropland.annual/fallow.remove: (read when resmgt = 5; residue removal)
* 15.1) residue removal date (julian day), integer - (`jdmove`)
* 16.1) fraction of flat residue removed (0-1), real - (`frmove`)
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow residue removal operation.

###### Year.loop.cropland.annual.cut: (read when resmgt = 7; annual plant cutting)
* Note: Option 7 for annual cutting is only available for 2016.3 file format.
* 15.1) annual cutting removal flag
    * 1) Annual cutting based on fractional height with removal from field
    * 4) Annual cutting based on fractional height, biomass left on field
    * 5) Annual cutting based on crop cutting height, with removal from field
    * 6) Annual cutting based on crop cutting height, biomass left on field
* 16.1) Number of annual cuttings
* 17.1) Julian day of cutting
* 17.2) Cutting height amount fraction
* ***Note*** (Line 17 repeats for number of cuttings indicated on Line 16.1).

##### Year.loop.cropland.perennial: (read when imngmt = 2; perennial crops)
* 11.1) approximate date to reach senescence (julian day), integer - (`jdharv`)
* ***Note*** Enter 0 if the plants do not senesce. This parameter is only important in situations in which the perennial plant is neither cut nor grazed.
* 12.1) planting date (julian day) integer (`jdplt`)
* ***Note*** Set `jdplt` = 0 if there is no planting date (this means the perennial is already established).
* 13.1) perennial crop growth stop date, if any (julian), integer - (`jdstop`)
* ***Note*** The perennial growth stop date is the date on which the perennial crop is permanently killed, either by tillage or herbicides (not frost). For example, if a bromegrass field is to be prepared for a subsequent corn crop, the date which the bromegrass is plowed under or killed with herbicides must be entered. A zero (0) is entered if the perennial crop is not killed during the year.
* 14.1) row width (m), real - (`rw`)
* ***Note*** (set `rw`=0.0 if unknown or seed broadcast - WEPP model then sets `rw` = `pltsp`).
* 15.1) crop management option, integer - (`mgtopt`)
    * 1) cutting
    * 2) grazing
    * 3) not harvested or grazed
    * Note: Options 4-7 are only available in 2016.3 format file
        * 4) cutting based on plant cutting height, biomass left on field
        * 5) grazing with cycles based on fraction of height removed
        * 6) grazing with fixed days based on fraction of height removed
        * 7) cutting with fixed days based on fraction of height removed, biomass left on field

###### Year.loop.cropland.perennial.cut: (read when mgtopt = 1; cutting)
* 16.1) number of cuttings, integer - (`ncut`)
* **Year.loop.cropland.perennial.cut.loop:**
    * 17.1) cutting date (julian), integer - (`cutday`)
    * ***Note*** Man.loop.cropland.perennial.cut.loop values repeat `ncut` times.

###### Year.loop.cropland.perennial.graze: (read when mgtopt = 2: grazing)
* 16.1) number of grazing cycles, integer - (`ncycle`)
* **Year.loop.cropland.perennial.graze.loop:**
    * 17.1) number of animal units, real - (`animal`)
    * 17.2) field size ($m^2$), real - (`area`)
    * 17.3) unit animal body weight (kg), real - (`bodywt`)
    * 17.4) digestibility, real - (`digest`)
    * 18.1) date grazing begins (julian day), integer - (`gday`)
    * 19.1) date grazing ends (julian day), integer - (`gend`)
    * ***Note*** Year.loop.cropland.perennial.graze.loop values repeat `ncycle` times.
* Note: Options 5,6,7 only available for format 2016.3 management file
    * If `mgtopt` = 5 (grazing cycles based on height percent removal)
        * 17.1) fraction of plant height removed
        * 18.1) date grazing begins (julian day), integer - (`gday`)
        * 19.1) date grazing ends (julian day), integer (`gend`)
    * If `mgtopt` = 6 (grazing fixed days based on plant height percent removal)
        * 17.1) day of grazing (Julian)
        * 17.2) fraction of plant height removed (real)
    * If `mgtopt` = 7 (cutting fixed days based on percent height removal, biomass left on field)
        * 17.1) day of cutting (Julian)
        * 17.2) fraction of plant height removed which is then left on field (real)

#### Year.loop.rangeland: (read when iscen = 2; rangeland)
* 6.1) Plant Growth Scenario index, integer - (`itype`)
* ***Note*** `itype` refers to a Plant Growth Scenario order index.
* 7.1) Surface Effects Scenario index, integer - (`tilseq`)
* ***Note*** `tilseq` refers to the Surface Effects Scenario order index.
* 8.1) Drainage Scenario index, integer - (`drset`)
* ***Note*** `drset` refers to a Drainage Scenario order index. If `ndrain` = 0, `drset` must be 0.
* 9.1) grazing flag, integer (`grazig`)
    * 0) no grazing
    * 1) grazing

##### Year.loop.rangeland.graze: (section read when grazig=1)
* 10.1) pasture area ($m^2$), real - (`area`)
* 10.2) fraction of forage available for consumption (0-1), real (`access`)
* 10.3) maximum digestibility of forage (0-1), real - (`digmax`)
* 10.4) minimum digestibility of forage (0-1), real - (`digmin`)
* 10.5) average amount of supplemental feed per day (kg/day), real - (`suppmt`)
* 11.1) number of grazing cycles per year, integer - (`jgraz`)

###### Year.loop.rangeland.graze.loop: (section read when grazig=1)
* 12.1) number of animals grazing (animal units per year), real - (`animal`)
* 12.2) average body weight of an animal (kg), real - (`bodywt`)
* 13.1) start of grazing period (julian date), integer - (`gday`)
* 14.1) end of grazing period (julian date), integer - (`gend`)
* 15.1) end of supplemental feeding day (julian day), integer - (`send`)
* 16.1) start of supplemental feeding day (julian day), integer - (`ssday`)
* ***Note*** Year.loop.rangeland.graze.loop values repeat `jgraz` times.
* 10.1) herbicide application date, integer - (`ihdate`)

##### Year.loop.rangeland.herb: (section read when ihdate > 0)
* 11.1) flag for activated herbicides, integer - (`active`)
* 12.1) fraction reduction in live biomass, real - (`dleaf`)
* 12.2) fraction of change in evergreen biomass, real - (`herb`)
* 12.3) fraction of change in above and below ground biomass, real - (`regrow`)
* 12.4) fraction increase of foliage, real - (`update`)
* 13.1) flag for decomp. of standing dead biomass due to herbicide application, integer - (`woody`)
* 11.1) rangeland burning date, integer - (`jfdate`)

##### Year.loop.rangeland.burn: (section read when jfdate > 0)
* 12.1) live biomass fraction accessible for consumption following burning, real - (`alter`)
* 12.2) fraction reduction in standing wood mass due to the burning, real (`burned`)
* 12.3) fraction change in potential above ground biomass, real - (`change`)
* 12.4) fraction evergreen biomass remaining after burning, real - (`hurt`)
* 12.5) fraction non-evergreen biomass remaining after burning, real - (`reduce`)

#### Year.loop.forest: (read when iscen = 3; forest)
* ***Note*** no values; yearly information for Forestland not yet supported.

#### Year.loop.roads: (read when iscen=4; roads)
* ***Note*** no values; yearly information for Roads not yet supported.

***Note*** Year.loop values repeat `nscen` times.

### Management Section
***Note*** The management scenario contains all information associated with a single WEPP simulation. The yearly scenarios are used to build this final scenario. The yearly scenarios were built from the earlier scenarios - plants, tillage sequences, contouring, drainage, and management practices.

* **Man.name:**
    * 1.1) scenario name, (up to) 8 characters - (`mname`)
* **Man.description:**
    * 2.1) description, (up to) 55 characters (may be blank)
    * 3.1) description, (up to) 55 characters (may be blank)
    * 4.1) description, (up to) 55 characters (may be blank)
* **Man.ofes:**
    * 5.1) number of ofes in the rotation, integer - (`nofe`)
* **Man.OFE.loop.ofe:**
    * 6.1) Initial Condition Scenario index used for this OFE, integer - (`ofeindx`)
    * ***Note*** `ofeindx` is an index of one of the defined Initial Condition Scenarios. Man.OFE.loop values repeat `nofe` times.
* **Man.repeat:**
    * 7.1) number of times the rotation is repeated, integer - (`nrots`)
* **Man.MAN.loop.years:**
    * 8.1) number of years in a single rotation, integer - (`nyears`)
* **Man.MAN.loop.loop.crops:**
    * 9.1) number of crops per year, integer (`nycrop`)
    * **Note** `nycrop` is the number of crops grown during the current year for a field or overland flow element. For the case of continuous corn, `nycrop` = 1. If two crops are grown in a year, then `nycrop` = 2. The number of crops for a year, for the purpose of WEPP model inputs, is determined in the following manner: For a single crop planted in the spring and harvested in the fall, the value of `nycrop` is 1. However, any time during a year that another crop is present on a field, it must be counted as another crop. For example, for a continuous winter wheat rotation, the wheat growing from January 1 to a harvest date in July is crop number 1, while the wheat planted in October and growing to December 31 is crop number 2. Another example would be a perennial alfalfa growing from January 1 to March 30, plowing the alfalfa under on March 30, a corn crop planted on April 25 and harvested on October 11, then planting a winter wheat crop on October 17. Here the alfalfa would be crop number 1, the corn would be crop number 2, and the wheat would be crop number 3. For areas in which the field lies fallow for periods of time in conjunction with planting of winter annuals, care must be taken to include a fallow crop at the beginning of the calendar year as crop number 1, followed by the winter annual planted that fall as crop number 2.
* **Man.MAN.loop.loop.loop.man:**
    * 10.1) Yearly Scenario index used this Year on this OFE with this Crop, integer - (`manindx`)
    * ***Note*** `manindx` is an index of one of the defined ordered Management Scenarios.
    * ***Notes*** Man.MAN.loop.loop.loop (line 10.1) values repeat for the total number of crops grown during the current year on the current OFE (`nycrop`).
    * Man.MAN.loop.loop.loop values repeat `nofe` times.
    * Man.MAN.loop.loop values repeat `nyears` times.
    * Man.MAN.loop values repeat `nrots` times.


## Markdown Generation

This was generated from https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum2024.pdf using Gemini/AI Pro 2.5 and the following prompt

```
Pages 31-51 document the plant (management) files for wepp. I would like to convert this file specification to markdown format to support LLM use.

Please convert Plant/Management Input File section to markdown being careful to capture all the content, without changing, adding, or omitting content related to the file specification. Keeping the spelling and wording exactly as in this document. Use markdown conventions that will support use in frontier language models like LLMs and will be human readable
```

## [cite: ##] tag removal

```bash
sed -E -i 's/ ?\[cite: [^]]*\]//g'  plant_file_specification.md 
```
