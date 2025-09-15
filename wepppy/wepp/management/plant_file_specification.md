# WEPP Plant/Management Input File
The plant/management input file contains all of the information needed by the WEPP model related to plant parameters (rangeland plant communities and cropland annual and perennial crops), tillage sequences and tillage implement parameters, plant and residue management, initial conditions, contouring, subsurface drainage, and crop rotations[cite: 717].

For readability, the WEPP management file is structured into **Sections**[cite: 718]. A **Section** is a group of data which are related in some manner[cite: 719]. The WEPP management file can become very complex, especially for multiple OFE simulations[cite: 720]. It is recommend to use the WEPP user interface or other software to assist in creating these files[cite: 721].

Although the rangeland section formatting is still accepted, the WEPP model has not been updated for rangeland applications[cite: 722]. The WEPP cropland management scenarios can be adapted for some rangeland applications[cite: 723]. Another option is to use the more recently developed USDAARS RHEM model for rangeland applications[cite: 724].

The management file contains the following **Sections** in the following order[cite: 725]:
* **Information Section** contains the WEPP version[cite: 726].
* **Plant Growth Section** - plant growth parameters[cite: 727].
* **Operation Section** - tillage and other implement parameters[cite: 728].
* **Initial Condition Section** - contains initial conditions and parameters which are OFE or channel specific[cite: 729].
* **Surface Effects Section** tillage sequences and other surface-disturbing datedsequences of implements[cite: 730].
* **Contour Section** - contouring parameters[cite: 731].
* **Drainage Section** - drainage parameters[cite: 732].
* **Yearly Section** - management information[cite: 733].
* **Management Section** - indexes into the Yearly Scenarios[cite: 734].

Within **Sections**, there may be several instances of data groupings[cite: 735]. Each unique data grouping is referred to as a **Scenario**[cite: 735]. For instance, the Contour **Section** may contain several different groups of contouring parameters[cite: 736]. Each unique contour grouping is called a Contour **Scenario**[cite: 737]. Likewise, each unique plant used by WEPP, and its associated parameters is called a Plant **Scenario**[cite: 737].

By arranging data into **Scenarios**, information which is accessed frequently by WEPP need only be stored once in the management file[cite: 738, 741]. When WEPP needs scenario information, it will access it through an index into the appropriate scenario[cite: 741]. Similarly, scenarios may also be accessed by other scenarios within the management file[cite: 742]. For example, the Surface Effects scenarios will index into an Operation **Scenario** when it needs to reference a specific operation[cite: 743]. The Yearly **Scenario** can index into the Surface Effects, and Contouring scenarios[cite: 744]. All scenarios are ultimately used by the Management **Section** through indices into the Yearly scenarios[cite: 745]. With this scenario hierarchy, simple scenarios are found toward the top of the management file; more complex ones below them[cite: 746].

Some management file conventions[cite: 747]:
1.  At most 10 data values per line[cite: 749].
2.  WEPP expects the following to be on lines by themselves: text information (such as scenario names and comments), looping parameters (such as `nini`, `ntill`, etc.), option flags (such as `lanuse`, `imngmt`, etc.), dates, and scenario indexes[cite: 751].
3.  Anything on a line after the `#` character is a comment[cite: 752]. Comments may not follow text information that is read by the model[cite: 753].

## Plant/Management Input File Sections
The general form of a **Section** is[cite: 755]:
* `Scen.number` - the number of scenarios declared [cite: 756]
* `Scen.loop.name` - the scenario name [cite: 756]
* `Scen.loop.description` - text comments [cite: 756]
* `Scen.loop.data` - the scenario data parameters [cite: 756]

To read a scenario, WEPP will loop the number of times specified by the value `Scen.number`, reading the "loop" data into memory for future use[cite: 758].

The plant/management file for WEPP v95.7 is described in Table 16[cite: 759]. Please note that although this management file convention allows the "mixing" of **Scenarios** of different land usage, this flexibility is not currently supported by the WEPP erosion model[cite: 759]. Also, there are several scenarios that have empty "slots" where information will eventually be placed when WEPP supports those options[cite: 760].

### Information Section [cite: 764]
* **Info.version:**
    * 1.1) WEPP version, (up to) 8 characters - (`datver`) [cite: 766]
        * `95.7` Initial version [cite: 767]
        * `98.4` - Update [cite: 768]
        * `2016.3` Residue management updates, additional parameters [cite: 769]
        * ***Note*** `datver` is used to detect older management file formats, which are incompatible with the current WEPP erosion model[cite: 770].
* **Info.header** [cite: 771]
    * 2.1) number of Overland Flow Elements for hillslopes, integer (`nofe`), or number of channels for watershed (`nchan`) [cite: 772]
    * 3.1) number of TOTAL years in simulation, integer (`nyears` * `nrots`) [cite: 773]

### Plant Growth Section [cite: 774]
***Note*** `ncrop` is the number of unique plant types grown during the simulation period[cite: 775]. For example, if the crops grown during the simulation are corn and wheat, `ncrop` = 2[cite: 776]. A different type of residue on a field besides the current crop growth being simulated also needs to be assigned a crop number[cite: 776]. For example if you are planting continuous corn into a field that is coming out of set-aside acreage that had a clover cover crop present the fall before that was killed with herbicides that fall, you need to input the clover crop parameters so that the decomposition section of the model will have the correct parameters (thus `ncrop` would be 2)[cite: 777].
* **Plant.number:**
    * 0.1) number of unique plant types, integer (`ncrop`) [cite: 779]
* **Plant.loop.name:**
    * 1.1) plant name, (up to) 35 characters (`crname`) [cite: 781]
* **Plant.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 783]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 784]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 785]
* **Plant.loop.landuse:**
    * 5.1) for use on land type..., integer - (`iplant`) [cite: 787]
        * 1) crop [cite: 788]
        * 2) range [cite: 789]
        * 3) forest [cite: 790]
        * 4) roads [cite: 791]

#### Plant.loop.cropland: (read when iplant=1; cropland) [cite: 794]
* 6.1) harvest units, (i.e., bu/a, kg/ha, t/a, etc.) up to 15 characters - (`crunit`) [cite: 795]
* 7.1) canopy cover coefficient, real - (`bb`) [cite: 796]
* 7.2) parameter value for canopy height equation, real - (`bbb`) [cite: 797]
* 7.3) biomass energy ratio, real - (`beinp`) [cite: 798]
* 7.4) base daily air temperature (degrees C), real - (`btemp`) [cite: 799]
* 7.5) parameter for flat residue cover equation ($m^2/kg$), real - (`cf`) [cite: 800]
* 7.6) growing degree days to emergence (degrees C), real - (`crit`) [cite: 800]
* 7.7) critical live biomass value below which grazing is not allowed ($kg/m^2$), real - (`critvm`) [cite: 800, 804]
* 7.8) height of post-harvest standing residue; cutting height (m), real - (`cuthgt`) [cite: 800, 801]
* 7.9) fraction canopy remaining after senescence (0-1), real (`decfct`) [cite: 802]
* 7.10) plant stem diameter at maturity (m), real - (`diam`) [cite: 803]
* 8.1) heat unit index when leaf area index starts to decline (0-1), real - (`dlai`) [cite: 805]
* 8.2) fraction of biomass remaining after senescence (0-1), real - (`dropfc`) [cite: 805]
* 8.3) radiation extinction coefficient, real - (`extnct`) [cite: 805]
* 8.4) standing to flat residue adjustment factor (wind, snow, etc.), real (`fact`) [cite: 806]
* 8.5) maximum Darcy Weisbach friction factor for living plant, real - (`flivmx`) [cite: 806]
* 8.6) growing degree days for growing season (degrees C), real - (`gddmax`) [cite: 806]
* 8.7) harvest index, real - (`hi`) [cite: 806]
* 8.8) maximum canopy height (m), real - (`hmax`) [cite: 807]
* 9.1) use fragile or non-fragile operation mfo values, integer - (`mfocod`) [cite: 808]
    * 1) fragile [cite: 809]
    * 2) non-fragile [cite: 809]
* 10.1) decomposition constant to calculate mass change of above-ground biomass (surface or buried), real - (`oratea`) [cite: 810, 811]
* 10.2) decomposition constant to calculate mass change of root-biomass, real - (`orater`) [cite: 812]
* 10.3) optimal temperature for plant growth (degrees C), real (`otemp`) [cite: 813]
* 10.4) plant specific drought tolerance, real (`pitol`) [cite: 814]
* 10.5) in-row plant spacing (m), real - (`pltsp`) [cite: 815]
* 10.6) maximum root depth (m), real - (`rdmax`) [cite: 816]
* 10.7) root to shoot ratio, real - (`rsr`) [cite: 817]
* 10.8) maximum root mass for a perennial crop ($kg/m^2$), real - (`rtmmax`) [cite: 818]
* 10.9) period over which senescence occurs (days), integer (`spriod`) [cite: 819]
* 10.10) maximum temperature that stops the growth of a perennial crop (degrees C), real (`tmpmax`) [cite: 820, 821]
* 11.1) critical freezing temperature for a perennial crop (degrees C), real - (`tmpmin`) [cite: 822]
* 11.2) maximum leaf area index, real - (`xmxlai`) [cite: 823]
* 11.3) optimum yield under no stress conditions ($kg/m^2$), real - (`yld`) [cite: 824]
* 11.4) Release canopy cover, real (version 2016.3) - (`rcc`) [cite: 825]
* ***Note*** (input 0.0 on Line 11.3 to use model calculated optimum yield) [cite: 826]

#### Plant.loop.rangeland: (read when iplant = 2; rangeland) [cite: 829]
* 6.1) change in surface residue mass coefficient, real - (`aca`) [cite: 830]
* 6.2) coefficient for leaf area index, real - (`aleaf`) [cite: 831]
* 6.3) change in root mass coefficient, real - (`ar`) [cite: 832]
* 6.4) parameter value for canopy height equation, real - (`bbb`) [cite: 833]
* 6.5) daily removal of surface residue by insects, real - (`bugs`) [cite: 834]
* 6.6) frac. of 1st peak of growing season, real - (`cf1`) [cite: 835]
* 6.7) frac. of 2nd peak of growing season, real - (`cf2`) [cite: 836]
* 6.8) c:n ratio of residue and roots, real - (`cn`) [cite: 837]
* 6.9) standing biomass where canopy cover is 100%, ($kg/m^2$) real - (`cold`) [cite: 838]
* 6.10) frost free period, (days) integer - (`ffp`) [cite: 839]
* 7.1) projected plant area coefficient for grasses, real - (`gcoeff`) [cite: 840]
* 7.2) average. canopy diameter for grasses, (m) real - (`gdiam`) [cite: 841]
* 7.3) average height for grasses (m), real (`ghgt`) [cite: 842]
* 7.4) average number of grasses along a 100 m belt transect, real - (`gpop`) [cite: 843]
* 7.5) minimum temperature to initiate growth, (degrees C) real - (`gtemp`) [cite: 844]
* 7.6) maximum herbaceous plant height (m), real - (`hmax`) [cite: 845]
* 7.7) maximum standing live biomass, ($kg/m^2$) real - (`plive`) [cite: 846]
* 7.8) plant drought tolerance factor, real (`pitol`) [cite: 847]
* 7.9) day of peak standing crop, 1st peak, (julian day) integer - (`pscday`) [cite: 848]
* 7.10) minimum amount of live biomass, ($kg/m^2$) real - (`rgcmin`) [cite: 849]
* 8.1) root biomass in top 10 cm, ($kg/m^2$) real (`root10`) [cite: 850]
* 8.2) fraction of live and dead roots from maximum at start of year, real - (`rootf`) [cite: 851]
* 8.3) day on which peak occurs, 2nd growing season (julian day), integer - (`scday2`) [cite: 852]
* 8.4) projected plant area coefficient for shrubs, real - (`scoeff`) [cite: 853]
* 8.5) average canopy diameter for shrubs (m), real - (`sdiam`) [cite: 854]
* 8.6) average height of shrubs (m), real (`shgt`) [cite: 855]
* 8.7) average number of shrubs along a 100 m belt transect, real - (`spop`) [cite: 856]
* 8.8) projected plant area coefficient for trees, real - (`tcoeff`) [cite: 857]
* 8.9) average canopy diameter for trees (m), real - (`tdiam`) [cite: 858]
* 8.10) minimum temperature to initiate senescence, (degrees C) real - (`tempmn`) [cite: 859]
* 9.1) average height for trees (m), real - (`thgt`) [cite: 860]
* 9.2) average number of trees along a 100 m belt transect, real - (`tpop`) [cite: 861]
* 9.3) fraction of initial standing woody biomass, real - (`wood`) [cite: 862]

#### Plant.loop.forest: (read when iplant = 3; forest) [cite: 863]
* ***Note*** no values; plants for Forestland not yet supported[cite: 864].

#### Plant.loop.roads: (read when iplant = 4; roads) [cite: 865]
* ***Note*** no values; plants for Roads not yet supported[cite: 866].

***Note*** Plant.loop values repeat `ncrop` times[cite: 867].

### Operation Section [cite: 869]
* **Op.number:**
    * 0.1) number of unique operation types, integer (`nop`) [cite: 872]
* **Op.loop.name:**
    * 1.1) operation name, (up to) 35 characters (`opname`) [cite: 874]
* **Op.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 876]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 877]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 878]
* **Op.loop.landuse:**
    * 5.1) for use on land type, integer - (`iop`) [cite: 880]
        * 1) crop [cite: 881]
        * 2) range [cite: 882]
        * 3) forest [cite: 883]
        * 4) roads [cite: 884]

#### Op.loop.cropland: (read when iop=1; cropland) [cite: 885]
* 6.1) interrill tillage intensity for fragile crops, real - (`mfo1`) [cite: 886]
* 6.2) interrill tillage intensity for non-fragile crops, real (`mfo2`) [cite: 886]
* 6.3) number of rows of tillage implement, integer - (`numof`) [cite: 887]
* 7.1) implement/residue code, integer - (`code1`/`resma1`) [cite: 888]
    * 1) planter [cite: 889]
    * 2) drill [cite: 889]
    * 3) cultivator [cite: 890]
    * 4) other [cite: 891]
    * Note: Following codes only valid for version 2016.3 [cite: 892]
        * 10) residue addition without surface disturbance [cite: 893]
        * 11) residue removal (flat only) without surface disturbance [cite: 894]
        * 12) residue addition with disturbance [cite: 895]
        * 13) residue removal (flat only) with disturbance [cite: 896]
        * 14) shredding/cutting [cite: 897]
        * 15) burning [cite: 898]
        * 16) silage [cite: 899]
        * 17) herbicide application [cite: 900]
        * 18) residue removal by fraction (standing and flat) without surface disturbance [cite: 901]
        * 19) residue removal by fraction (standing and flat) - with surface disturbance [cite: 902]
* 7.2) cultivator position, integer - (`cltpos`) (read when `code1`/`resma1` = 3; cultivator) [cite: 905, 906]
    * 1) front mounted [cite: 907]
    * 2) rear mounted [cite: 908]
* 8.1) ridge height value after tillage (m), real - (`rho`) [cite: 909]
* 8.2) ridge interval (m), real - (`rint`) [cite: 910]
* 8.3) rill tillage intensity for fragile crops, real - (`rmfo1`) [cite: 911]
* 8.4) rill tillage intensity for non-fragile crops, real - (`rmfo2`) [cite: 911]
* 8.5) random roughness value after tillage (m), real - (`rro`) [cite: 911]
* 8.6) fraction of surface area disturbed (0-1), real - (`surdis`) [cite: 911]
* 8.7) mean tillage depth (m), real - (`tdmean`) [cite: 911]
* Note: Resurface parameters only for version 2016.3 format [cite: 912]
    * 8.8) Fraction residue resurfaced for fragile crops (0-1), real - (`resurf1`) [cite: 912]
    * 8.9) Fraction residue resurfaced for non-fragile crop (0-1), real - (`resurnf1`) [cite: 912]
* Note: Lines 9 and 10 only for version 2016.3 format [cite: 913]
* 9.1) Read when `resma1` is 10,11,12,13,14,15,18,19: [cite: 914]
    * When `resma1` = 10,12: crop index specifying residue type - (`iresa1`) [cite: 915]
    * When `resma1` = 11,13: fraction of residue removed (0-1) - (`frmov1`) [cite: 915]
    * When `resma1` = 14: fraction of residue shredded (0-1) - (`frmov1`) [cite: 915]
    * When `resma1` = 15: fraction of standing residue burned (0-1) (`fbma1`) [cite: 915]
    * When `resma1` = 18,19: fraction of flat residue removed (0-1) (`frfmov1`) [cite: 915]
* 10.1) Read when `resma1` is 10, 12, 15, 18, 19: [cite: 916]
    * When `resma1` = 10,12: amount of residue added (kg/m^2) - (`resad1`) [cite: 917]
    * When `resma1` = 15: fraction of flat residue burned (0-1) (`fbrnol`) [cite: 917]
    * When `resma1` = 18,19: fraction of standing residue removed (0-1) (`frsmov1`) [cite: 917]

#### Op.loop.rangeland: (read when iop=2; rangeland) [cite: 918]
* ***Note*** no values; operations for Rangeland not yet supported[cite: 919].

#### Op.loop.forest: (read when iop=3; forest) [cite: 920]
* ***Note*** no values; operations for Forestland not yet supported[cite: 921].

#### Op.loop.roads: (read when iop = 4; roads) [cite: 922]
* ***Note*** no values; operations for Roads not yet supported[cite: 923].

***Note*** Op.loop values repeat `nop` times[cite: 924].

### Initial Condition Section [cite: 926]
***Note*** `nini` is the number of different initial conditions to be read into the WEPP model[cite: 928]. The initial conditions are the conditions which exist at the beginning of the simulation[cite: 929]. Estimates of the initial conditions for a continuous simulation can be made by using long term average conditions which exist on January 1st[cite: 930]. For a single storm simulation, the user must input the correct values for initial conditions since they will greatly affect the model output[cite: 931]. For continuous model simulations, especially ones in which significant soil and residue disturbance are caused by tillage and the simulation is for several years, the effect of initial conditions on model output is minimal.¹ [cite: 932]
¹ The WEPP Shell Interface can optionally create these scenarios from WEPP model runs[cite: 959].

* **Ini.number:**
    * 0.1) number of initial condition scenarios, integer - (`nini`) [cite: 934]
* **Ini.loop.name:**
    * 1.1) scenario name, (up to) 8 characters (`oname`) [cite: 936]
* **Ini.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 938]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 939]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 939]
* **Ini.loop.landuse:**
    * 5.1) land use, integer - (`lanuse`) [cite: 941]
        * 1) crop [cite: 942]
        * 2) range [cite: 943]
        * 3) forest [cite: 944]
        * 4) roads [cite: 945]

#### Ini.loop.landuse.cropland: (read when lanuse = 1; cropland) [cite: 946]
* 6.1) bulk density after last tillage ($g/cm^3$), real - (`bdtill`) [cite: 947]
* 6.2) initial canopy cover (0-1), real - (`cancov`) [cite: 948]
* 6.3) days since last tillage, real - (`daydis`) [cite: 949]
* 6.4) days since last harvest, integer - (`dsharv`) [cite: 950]
* 6.5) initial frost depth (m), real - (`frdp`) [cite: 951]
* 6.6) initial interrill cover (0-1), real - (`inrcov`) [cite: 952]
* 7.1) Plant Growth Scenario index of initial residue type, integer - (`iresd`) [cite: 953]
* ***Note*** `iresd` refers to a Plant Growth Scenario[cite: 954].
* 8.1) initial residue cropping system, integer - (`imngmt`) [cite: 955]
    * 1) annual [cite: 956]
    * 2) perennial [cite: 956]
    * 3) fallow [cite: 957]
* 9.1) cumulative rainfall since last tillage (mm), real - (`rfcum`) [cite: 958]
* 9.2) initial ridge height after last tillage (m), real - (`rhinit`) [cite: 962]
* 9.3) initial rill cover (0-1), real - (`rilcov`) [cite: 963]
* 9.4) initial ridge roughness after last tillage (m), real - (`rrinit`) [cite: 964]
* 9.5) rill spacing (m), real - (`rspace`) [cite: 965]
* ***Note*** if `rspace` is 0.0 or less, WEPP will set rill spacing to 1.0 meter[cite: 966].
* 10.1) rill width type, integer - (`rtyp`) [cite: 967]
    * 1) temporary [cite: 968]
    * 2) permanent [cite: 968]
* ***Note*** For most cases, input a value of "1" for rill width type[cite: 969]. To use a constant rill width, unaffected by flow or tillage, input "2" here for permanent rills[cite: 970].
* 11.1) initial snow depth (m), real - (`snodpy`) [cite: 971]
* 11.2) initial depth of thaw (m), real - (`thdp`) [cite: 972]
* 11.3) depth of secondary tillage layer (m), real - (`tillay(1)`) [cite: 973]
* 11.4) depth of primary tillage layer (m), real - (`tillay(2)`) [cite: 974]
* 11.5) initial rill width (m), real (`width`) [cite: 975]
* ***Note*** The primary tillage layer (`tillay(2)`) is the depth of the deepest tillage operation[cite: 976]. The secondary tillage layer is the average depth of all secondary tillage operations[cite: 977]. If no tillage, set `tillay(1)`=0.1 and `tillay(2)`=0.2[cite: 978]. The current version of WEPP (v95.7/v2012/v2024) internally fixes tillay(1)=0.1 and tillay(2)=0.2, so the input values here at present have no impact on model simulations[cite: 978].
* ***Note*** If rill width type (`rtyp`) is temporary, WEPP will estimate a value for rill width as a function of flow discharge rate for each storm, and reset rill width to 0.0 when a tillage occurs[cite: 979]. If `width` is 0.0 and rill width type (`rtyp`) is permanent, WEPP will set the permanent rill width to the rill spacing, functionally forcing the model to assume broad sheet flow for flow shear stress and transport computations[cite: 980].
* 12.1) initial total dead root mass ($kg/m^2$) real - (`sumrtm`) [cite: 981]
* 12.2) initial total submerged residue mass ($kg/m^2$), real - (`sumsrm`) [cite: 982]
* Note: Forest understory parameters only for version 2016.3 format [cite: 983]
    * 12.3) Initial understory interrill cover (0-1), real - (`usinrcol`) [cite: 983]
    * 12.4) Initial understory rill cover (0-1), real - (`usrilcol`) [cite: 983]
* ***Note*** See page (100) for information on estimating `sumrtm` and `sumsrm`[cite: 984].

#### Ini.loop.landuse.rangeland: (read when lanuse = 2; rangeland) [cite: 984]
* 6.1) initial frost depth (m), real - (`frdp`) [cite: 985]
* 6.2) average rainfall during growing season (m), real - (`pptg`) [cite: 986]
* 6.3) initial residue mass above the ground ($kg/m^2$), real - (`rmagt`) [cite: 986]
* 6.4) initial residue mass on the ground ($kg/m^2$), real - (`rmogt`) [cite: 986]
* 6.5) initial random roughness for rangeland (m), real (`rrough`) [cite: 986]
* 6.6) initial snow depth (m), real - (`snodpy`) [cite: 989]
* 6.7) initial depth of thaw (m), real - (`thdp`) [cite: 990]
* 6.8) depth of secondary tillage layer (m), real - (`tillay(1)`) [cite: 991]
* 6.9) depth of primary tillage layer (m), real - (`tillay(2)`) [cite: 992]
* ***Note*** The primary tillage layer (`tillay(2)`) is the depth of the deepest tillage operation[cite: 993]. The secondary tillage layer is the average depth of all secondary tillage operations[cite: 994]. If no tillage, set `tillay(1)`=0.1 and `tillay(2)`=0.2[cite: 995]. The current version of WEPP (v95.7) internally fixes `tillay(1)` = 0.1 and `tillay(2)`=0.2, so the input values here at present have no impact on model simulations[cite: 995].
* 7.1) interrill litter surface cover (0-1), real - (`resi`) [cite: 996]
* 7.2) interrill rock surface cover (0-1), real - (`roki`) [cite: 997]
* 7.3) interrill basal surface cover (0-1), real - (`basi`) [cite: 998, 999]
* 7.4) interrill cryptogamic surface cover (0-1), real - (`cryi`) [cite: 1000]
* 7.5) rill litter surface cover (0-1), real - (`resr`) [cite: 1001]
* 7.6) rill rock surface cover (0-1), real - (`rokr`) [cite: 1002]
* 7.7) rill basal surface cover (0-1), real - (`basr`) [cite: 1003]
* 7.8) rill cryptogamic surface cover (0-1), real - (`cryr`) [cite: 1004]
* 7.9) total foliar (canopy) cover (0-1), real (`cancov`) [cite: 1005]

#### Ini.loop.landuse.forest: (read when lanuse = 3; forest) [cite: 1006]
* ***Note*** no values; initial conditions for Forestland not yet supported[cite: 1007].

#### Ini.loop.landuse.roads: (read when lanuse=4; roads) [cite: 1008]
* ***Note*** no values; initial conditions for Roads not yet supported[cite: 1009].

***Note*** Ini.loop values repeat `nini` times[cite: 1010].

### Surface Effects Section [cite: 1011]
***Note*** A Surface Effect Scenario is a sequence of surface-disturbing (tillage) operations performed on one field or overland flow element during one calendar year[cite: 1012].

* **Surf.number:**
    * 0.1) number of Surface Effect Scenarios, integer (`nseq`) [cite: 1014]
* **Surf.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`sname`) [cite: 1016]
* **Surf.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 1018]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 1019]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 1020]
* **Surf.loop.landuse:**
    * 5.1) for use on land type, integer - (`iseq`) [cite: 1024]
        * 1) crop [cite: 1025]
        * 2) range [cite: 1026]
        * 3) forest [cite: 1027]
        * 4) roads [cite: 1028]
* **Surf.loop.number:**
    * 6.1) number of operations for surface effect scenario, integer - (`ntill`) [cite: 1030]

#### Surf.loop.loop.cropland: (read when iseq = 1; cropland) [cite: 1031]
* 7.1) day of tillage (julian), integer - (`mdate`) [cite: 1032]
* 8.1) Operation Scenario index, integer - (`op`) [cite: 1033]
* ***Note*** `op` refers to the Operation Scenario[cite: 1034].
* 9.1) tillage depth (m), real - (`tildep`) [cite: 1035]
* 10.1) tillage type, integer (`typtil`) [cite: 1036]
    * 1) primary [cite: 1037]
    * 2) secondary [cite: 1038]
* ***Note*** Primary tillage is the operation which tills to the maximum depth. Secondary tillage is all other tillage operations[cite: 1039].

#### Surf.loop.loop.rangeland: (read when iseq = 2; rangeland) [cite: 1040]
* ***Note*** no values; surface effects for Rangeland not yet supported[cite: 1041].

#### Surf.loop.loop.forest: (read when iseq = 3; forest) [cite: 1042]
* ***Note*** no values; surface effects for Forestland not yet supported[cite: 1043].

#### Surf.loop.loop.roads: (read when iseq = 4; roads) [cite: 1044]
* ***Note*** no values; surface effects for Roads not yet supported[cite: 1045].

***Note*** Surf.loop.loop values repeat `ntill` times. Surf.loop values repeat `nseq` times[cite: 1046].

### Contour Section [cite: 1047]
***Note*** A Contour Scenario is the combination of slope length, slope steepness, and ridge height which is associated with one (or more) overland flow element(s) or a field in a hillslope simulation[cite: 1048]. Contour Scenarios are used when the effects of contour farming or cross-slope farming are to be examined[cite: 1049]. The contour routines within the WEPP model at this time are fairly simple[cite: 1050, 1053]. The inputs for the Contour Scenarios are the row grade of the contours (assumed uniform), the contour row spacing (distance between ridges), the contour row length (the distance runoff flows down a contour row), and the contour ridge height[cite: 1053]. WEPP computes the amount of water storage within a contour row[cite: 1054]. If the runoff produced by a rainfall event exceeds the storage the contours are predicted to fail and a message is sent to the output which informs the user that his contour system has failed[cite: 1055]. There are now two options for contour simulations, and what happens when contours are predicted to fail[cite: 1056]. In v2012.8 and earlier versions of WEPP, erosion estimates are made continuing to assume that all flow is down the contour rows (even when they were predicted to fail)[cite: 1057]. The model will count the number of contour failures and report this to the user in the output file[cite: 1058]. A newer contour simulation option available in v2024 predicts runoff and soil loss up-and-down a hillslope profile after contour failure[cite: 1059]. Erosion estimates will continue to be made up-and-down the profile until a subsequent tillage operation occurs that will reset the simulation, so that predictions will again made down the contour rows[cite: 1060]. For the NRCS web-based interface, NRCS set the contour row spacing equal to the rill spacing, set the contour row length to 50 feet, set the contour ridge height to the OFE soil ridge height, and forced contour failure if the ridge height on a day was 2 inches or less[cite: 1061]. There is an option setting within the updated Windows interface allowing a user to choose which contour simulation option they prefer[cite: 1062]. If a user receives a message that their contour system has failed, their options are to redesign the contour system so that the contour rows are shorter and/or the contour ridge height is greater, or use the watershed application of WEPP to simulate the flow down the contour rows then into the failure channel, gully, or grassed waterway[cite: 1063]. When the contour option is used, all of the flow and sediment for an overland flow element are assumed to be routed to the side of the slope[cite: 1064]. When contours hold on an OFE, no sediment will be predicted to exit the bottom of that overland flow element, and an average detachment rate is calculated at the 100 points down the hillside based on the sediment exiting off the side of the OFE[cite: 1065]. Users are advised not to simulate contoured OFEs below non-contoured ones, since there is a large likelihood of failure of the contours due to inflow of water from above overtopping the contour ridges[cite: 1066].

* **Cont.number:**
    * 0.1) number of Contour Scenarios - (`ncnt`) [cite: 1068]
* **Cont.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`cname`) [cite: 1070]
* **Cont.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 1072]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 1073]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 1074]
* **Cont.loop.landuse:**
    * 5.1) for use on land type..., integer - (`icont`) [cite: 1076]
        * 1) crop [cite: 1077]
        * ***Note*** `icont` must be 1, as only cropland supports contouring[cite: 1078].

#### Cont.loop.cropland: (read when icont = 1; cropland) [cite: 1081]
* 6.1) contour slope ($m/m$), real - (`cntslp`) [cite: 1082]
* 6.2) contour ridge height (m), real - (`rdghgt`) [cite: 1082]
* 6.3) contour row length (m), real - (`rowlen`) [cite: 1082]
* 6.4) contour row spacing (m), real - (`rowspc`) [cite: 1082]
* Note: permanent flag is only for 2016.3 format [cite: 1083]
    * 6.5) permanent flag (0 or 1), integer (`contours_perm`) [cite: 1084]

***Note*** Cont.loop values repeat `ncnt` times[cite: 1085].

### Drainage Section [cite: 1086]
* **Drain.number:**
    * 0.1) number of Drainage Scenarios - (`ndrain`) [cite: 1088]
* **Drain.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`dname`) [cite: 1090]
* **Drain.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 1092]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 1093]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 1094]
* **Drain.loop.landuse:**
    * 5.1) for use on land type..., integer - (`dcont`) [cite: 1096]
        * 1) crop [cite: 1097]
        * 2) range [cite: 1098]
        * 4) roads [cite: 1099]
        * ***Note*** `dcont` must be 1, 2, or 4, as forestland does not support drainage[cite: 1100].

#### Drain.loop.drainage: (read when dcont = 1; cropland) [cite: 1101]
* 6.1) depth to tile drain (m), real - (`ddrain`) [cite: 1102]
* 6.2) drainage coefficient ($m/day$), real - (`drainc`) [cite: 1103]
* 6.3) drain tile diameter (m), real - (`drdiam`) [cite: 1103]
* 6.4) drain tile spacing (m), real - (`sdrain`) [cite: 1103]

#### Drain.loop.rangeland: (read when dcont = 2; rangeland) [cite: 1104]
* ***Note*** no values; drainage for Rangeland not yet supported[cite: 1105].

#### Drain.loop.roads: (read when dcont = 4; roads) [cite: 1106]
* ***Note*** no values; drainage for Roads not yet supported[cite: 1109].

***Note*** Drain.loop values repeat `ndrain` times[cite: 1110].

### Yearly Section [cite: 1111]
***Note*** `nscen` is the number of management scenarios used by the simulation[cite: 1112]. A management scenario contains all information associated with a particular Year/OFE/Crop - its Surface Effect, Contour, Drainage, Plant Growth scenarios and management data[cite: 1113].

* **Year.number:**
    * 0.1) number of Yearly Scenarios - (`nscen`) [cite: 1115]
* **Year.loop.name:**
    * 1.1) scenario name, (up to) 8 characters - (`mname`) [cite: 1117]
* **Year.loop.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 1119]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 1120]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 1121]
* **Year.loop.landuse:**
    * 5.1) for use on land type..., integer - (`iscen`) [cite: 1123]
        * 1) crop [cite: 1124]
        * 2) range [cite: 1125]
        * 3) forest [cite: 1126]
        * 4) roads [cite: 1127]

#### Year.loop.cropland: (read when iscen = 1; cropland) [cite: 1128]
* 6.1) Plant Growth Scenario index, integer (`itype`) [cite: 1129]
* ***Note*** `itype` refers to a Plant Growth Scenario[cite: 1130]. The value for `itype` corresponds to the order that the plants are read into WEPP from the Plant Growth Section[cite: 1130]. For example, if the plants being grown are corn and soybeans and in the Plant Growth Section the first plant read in is corn and the second soybeans, then corn will have a reference index of 1 and soybeans will have a reference index of 2[cite: 1131]. So for any year when corn is being grown, `itype` will equal 1 and for any year when soybeans are being grown, `itype` will equal 2[cite: 1131].
* 7.1) Surface Effect Scenario index, integer - (`tilseq`) [cite: 1132]
* ***Note*** `tilseq` refers to a Surface Effects Scenario order number index[cite: 1133]. If `nseq` = 0, then `tilseq` must be 0[cite: 1134].
* 8.1) Contour Scenario index, integer (`conset`) [cite: 1137]
* ***Note*** `conset` refers to a Contour Scenario order number index[cite: 1138]. If `ncnt` = 0 on line 0.1 of the Contour Section, then `conset` must be 0[cite: 1139].
* 9.1) Drainage Scenario index, integer - (`drset`) [cite: 1140]
* ***Note*** `drset` refers to a Drainage Scenario order number index[cite: 1141]. If `ndrain` = 0 on line 0.1 of the Drainage Section, then `drset` must be 0[cite: 1142].
* 10.1) cropping system, integer - (`imngmt`) [cite: 1143]
    * 1) annual [cite: 1144]
    * 2) perennial [cite: 1144]
    * 3) fallow [cite: 1145]

##### Year.loop.cropland.annual/fallow: (read when imngmt = 1 or imngmt = 3; annual/fallow crops) [cite: 1146]
* 11.1) harvesting date or end of fallow period (julian day), integer - (`jdharv`) [cite: 1147]
* 12.1) planting date or start of fallow period (julian day), integer - (`jdplt`) [cite: 1148]
* 13.1) row width (m), real - (`rw`) [cite: 1149]
* 14.1) residue management option, integer - (`resmgt`) [cite: 1150]
* Note: Options 1-6 only for version 95.7 and 98.4 format. For 2016.3 format see the operation section for more options[cite: 1151].
    * 1) herbicide application [cite: 1152]
    * 2) burning [cite: 1153]
    * 3) silage [cite: 1154]
    * 4) shredding or cutting [cite: 1157]
    * 5) residue removal [cite: 1155]
    * 6) none [cite: 1156]
    * 7) annual cutting - only in version 2016.3 [cite: 1158]

###### Year.loop.cropland.annual/fallow.herb: (read when resmgt = 1; herbicide application) [cite: 1159]
* 15.1) herbicide application date (julian), integer - (`jdherb`) [cite: 1160]
* ***Note*** Herbicide application here refers to use of a contact herbicide which the WEPP model will simulate as immediately converting all standing live biomass to dead residue[cite: 1161].
* Note only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow herbicide applications[cite: 1162].

###### Year.loop.cropland.annual/fallow.burn: (read when resmgt = 2; burning) [cite: 1165]
* 15.1) residue burning date (julian day), integer - (`jdburn`) [cite: 1166]
* 16.1) fraction of standing residue lost by burning (0-1), real - (`fbmag`) [cite: 1167]
* 17.1) fraction of flat residue lost by burning (0-1), real - (`fbrnog`) [cite: 1168]
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify annual/fallow burning operations[cite: 1169].

###### Year.loop.cropland.annual/fallow.silage: (read when resmgt = 3; silage) [cite: 1170]
* 15.1) silage harvest date (julian day), integer - (`jdslge`) [cite: 1171]
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow silage operation[cite: 1172].

###### Year.loop.cropland.annual/fallow.cut: (read when resmgt = 4; cutting) [cite: 1173]
* 15.1) standing residue shredding or cutting date (julian day), integer - (`jdcut`) [cite: 1174]
* 16.1) fraction of standing residue shredded or cut (0-1), real - (`frcut`) [cite: 1174]
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow residue shredding or cutting operation[cite: 1175].

###### Year.loop.cropland.annual/fallow.remove: (read when resmgt = 5; residue removal) [cite: 1176]
* 15.1) residue removal date (julian day), integer - (`jdmove`) [cite: 1177]
* 16.1) fraction of flat residue removed (0-1), real - (`frmove`) [cite: 1177]
* Note - only for management file version 98.4, for the 2016.3 file format use the operation records to specify an annual/fallow residue removal operation[cite: 1178].

###### Year.loop.cropland.annual.cut: (read when resmgt = 7; annual plant cutting) [cite: 1179]
* Note: Option 7 for annual cutting is only available for 2016.3 file format[cite: 1180].
* 15.1) annual cutting removal flag [cite: 1181]
    * 1) Annual cutting based on fractional height with removal from field [cite: 1182]
    * 4) Annual cutting based on fractional height, biomass left on field [cite: 1182]
    * 5) Annual cutting based on crop cutting height, with removal from field [cite: 1182]
    * 6) Annual cutting based on crop cutting height, biomass left on field [cite: 1182]
* 16.1) Number of annual cuttings [cite: 1185]
* 17.1) Julian day of cutting [cite: 1186]
* 17.2) Cutting height amount fraction [cite: 1187]
* ***Note*** (Line 17 repeats for number of cuttings indicated on Line 16.1)[cite: 1188].

##### Year.loop.cropland.perennial: (read when imngmt = 2; perennial crops) [cite: 1189]
* 11.1) approximate date to reach senescence (julian day), integer - (`jdharv`) [cite: 1190]
* ***Note*** Enter 0 if the plants do not senesce. This parameter is only important in situations in which the perennial plant is neither cut nor grazed[cite: 1191].
* 12.1) planting date (julian day) integer (`jdplt`) [cite: 1192]
* ***Note*** Set `jdplt` = 0 if there is no planting date (this means the perennial is already established)[cite: 1193].
* 13.1) perennial crop growth stop date, if any (julian), integer - (`jdstop`) [cite: 1194]
* ***Note*** The perennial growth stop date is the date on which the perennial crop is permanently killed, either by tillage or herbicides (not frost)[cite: 1195]. For example, if a bromegrass field is to be prepared for a subsequent corn crop, the date which the bromegrass is plowed under or killed with herbicides must be entered[cite: 1196]. A zero (0) is entered if the perennial crop is not killed during the year[cite: 1197].
* 14.1) row width (m), real - (`rw`) [cite: 1198]
* ***Note*** (set `rw`=0.0 if unknown or seed broadcast - WEPP model then sets `rw` = `pltsp`)[cite: 1199].
* 15.1) crop management option, integer - (`mgtopt`) [cite: 1200]
    * 1) cutting [cite: 1201]
    * 2) grazing [cite: 1202]
    * 3) not harvested or grazed [cite: 1203]
    * Note: Options 4-7 are only available in 2016.3 format file [cite: 1204]
        * 4) cutting based on plant cutting height, biomass left on field [cite: 1205]
        * 5) grazing with cycles based on fraction of height removed [cite: 1206]
        * 6) grazing with fixed days based on fraction of height removed [cite: 1207]
        * 7) cutting with fixed days based on fraction of height removed, biomass left on field [cite: 1208]

###### Year.loop.cropland.perennial.cut: (read when mgtopt = 1; cutting) [cite: 1211]
* 16.1) number of cuttings, integer - (`ncut`) [cite: 1212]
* **Year.loop.cropland.perennial.cut.loop:** [cite: 1213]
    * 17.1) cutting date (julian), integer - (`cutday`) [cite: 1214]
    * ***Note*** Man.loop.cropland.perennial.cut.loop values repeat `ncut` times[cite: 1215].

###### Year.loop.cropland.perennial.graze: (read when mgtopt = 2: grazing) [cite: 1216]
* 16.1) number of grazing cycles, integer - (`ncycle`) [cite: 1217]
* **Year.loop.cropland.perennial.graze.loop:** [cite: 1218]
    * 17.1) number of animal units, real - (`animal`) [cite: 1219]
    * 17.2) field size ($m^2$), real - (`area`) [cite: 1220]
    * 17.3) unit animal body weight (kg), real - (`bodywt`) [cite: 1221]
    * 17.4) digestibility, real - (`digest`) [cite: 1222]
    * 18.1) date grazing begins (julian day), integer - (`gday`) [cite: 1223]
    * 19.1) date grazing ends (julian day), integer - (`gend`) [cite: 1224]
    * ***Note*** Year.loop.cropland.perennial.graze.loop values repeat `ncycle` times[cite: 1225].
* Note: Options 5,6,7 only available for format 2016.3 management file [cite: 1226]
    * If `mgtopt` = 5 (grazing cycles based on height percent removal) [cite: 1227]
        * 17.1) fraction of plant height removed [cite: 1228]
        * 18.1) date grazing begins (julian day), integer - (`gday`) [cite: 1229]
        * 19.1) date grazing ends (julian day), integer (`gend`) [cite: 1230]
    * If `mgtopt` = 6 (grazing fixed days based on plant height percent removal) [cite: 1231]
        * 17.1) day of grazing (Julian) [cite: 1232]
        * 17.2) fraction of plant height removed (real) [cite: 1233]
    * If `mgtopt` = 7 (cutting fixed days based on percent height removal, biomass left on field) [cite: 1234]
        * 17.1) day of cutting (Julian) [cite: 1235]
        * 17.2) fraction of plant height removed which is then left on field (real) [cite: 1236]

#### Year.loop.rangeland: (read when iscen = 2; rangeland) [cite: 1239]
* 6.1) Plant Growth Scenario index, integer - (`itype`) [cite: 1240]
* ***Note*** `itype` refers to a Plant Growth Scenario order index[cite: 1241].
* 7.1) Surface Effects Scenario index, integer - (`tilseq`) [cite: 1242]
* ***Note*** `tilseq` refers to the Surface Effects Scenario order index[cite: 1243].
* 8.1) Drainage Scenario index, integer - (`drset`) [cite: 1244]
* ***Note*** `drset` refers to a Drainage Scenario order index. If `ndrain` = 0, `drset` must be 0[cite: 1245, 1246].
* 9.1) grazing flag, integer (`grazig`) [cite: 1247]
    * 0) no grazing [cite: 1248]
    * 1) grazing [cite: 1248]

##### Year.loop.rangeland.graze: (section read when grazig=1) [cite: 1249]
* 10.1) pasture area ($m^2$), real - (`area`) [cite: 1250]
* 10.2) fraction of forage available for consumption (0-1), real (`access`) [cite: 1251]
* 10.3) maximum digestibility of forage (0-1), real - (`digmax`) [cite: 1252]
* 10.4) minimum digestibility of forage (0-1), real - (`digmin`) [cite: 1253]
* 10.5) average amount of supplemental feed per day (kg/day), real - (`suppmt`) [cite: 1254]
* 11.1) number of grazing cycles per year, integer - (`jgraz`) [cite: 1255]

###### Year.loop.rangeland.graze.loop: (section read when grazig=1) [cite: 1256]
* 12.1) number of animals grazing (animal units per year), real - (`animal`) [cite: 1257]
* 12.2) average body weight of an animal (kg), real - (`bodywt`) [cite: 1257]
* 13.1) start of grazing period (julian date), integer - (`gday`) [cite: 1258]
* 14.1) end of grazing period (julian date), integer - (`gend`) [cite: 1259]
* 15.1) end of supplemental feeding day (julian day), integer - (`send`) [cite: 1260]
* 16.1) start of supplemental feeding day (julian day), integer - (`ssday`) [cite: 1261]
* ***Note*** Year.loop.rangeland.graze.loop values repeat `jgraz` times[cite: 1262].
* 10.1) herbicide application date, integer - (`ihdate`) [cite: 1263]

##### Year.loop.rangeland.herb: (section read when ihdate > 0) [cite: 1266]
* 11.1) flag for activated herbicides, integer - (`active`) [cite: 1267]
* 12.1) fraction reduction in live biomass, real - (`dleaf`) [cite: 1268]
* 12.2) fraction of change in evergreen biomass, real - (`herb`) [cite: 1269]
* 12.3) fraction of change in above and below ground biomass, real - (`regrow`) [cite: 1270]
* 12.4) fraction increase of foliage, real - (`update`) [cite: 1271]
* 13.1) flag for decomp. of standing dead biomass due to herbicide application, integer - (`woody`) [cite: 1272, 1273]
* 11.1) rangeland burning date, integer - (`jfdate`) [cite: 1274]

##### Year.loop.rangeland.burn: (section read when jfdate > 0) [cite: 1275]
* 12.1) live biomass fraction accessible for consumption following burning, real - (`alter`) [cite: 1276]
* 12.2) fraction reduction in standing wood mass due to the burning, real (`burned`) [cite: 1276]
* 12.3) fraction change in potential above ground biomass, real - (`change`) [cite: 1277]
* 12.4) fraction evergreen biomass remaining after burning, real - (`hurt`) [cite: 1278]
* 12.5) fraction non-evergreen biomass remaining after burning, real - (`reduce`) [cite: 1279]

#### Year.loop.forest: (read when iscen = 3; forest) [cite: 1280]
* ***Note*** no values; yearly information for Forestland not yet supported[cite: 1281].

#### Year.loop.roads: (read when iscen=4; roads) [cite: 1282]
* ***Note*** no values; yearly information for Roads not yet supported[cite: 1283].

***Note*** Year.loop values repeat `nscen` times[cite: 1284].

### Management Section [cite: 1285]
***Note*** The management scenario contains all information associated with a single WEPP simulation[cite: 1286]. The yearly scenarios are used to build this final scenario[cite: 1287]. The yearly scenarios were built from the earlier scenarios - plants, tillage sequences, contouring, drainage, and management practices[cite: 1288].

* **Man.name:**
    * 1.1) scenario name, (up to) 8 characters - (`mname`) [cite: 1290]
* **Man.description:**
    * 2.1) description, (up to) 55 characters (may be blank) [cite: 1292]
    * 3.1) description, (up to) 55 characters (may be blank) [cite: 1292]
    * 4.1) description, (up to) 55 characters (may be blank) [cite: 1292]
* **Man.ofes:**
    * 5.1) number of ofes in the rotation, integer - (`nofe`) [cite: 1296]
* **Man.OFE.loop.ofe:**
    * 6.1) Initial Condition Scenario index used for this OFE, integer - (`ofeindx`) [cite: 1298]
    * ***Note*** `ofeindx` is an index of one of the defined Initial Condition Scenarios. Man.OFE.loop values repeat `nofe` times[cite: 1299].
* **Man.repeat:**
    * 7.1) number of times the rotation is repeated, integer - (`nrots`) [cite: 1301]
* **Man.MAN.loop.years:**
    * 8.1) number of years in a single rotation, integer - (`nyears`) [cite: 1303]
* **Man.MAN.loop.loop.crops:**
    * 9.1) number of crops per year, integer (`nycrop`) [cite: 1305]
    * **Note** `nycrop` is the number of crops grown during the current year for a field or overland flow element[cite: 1306]. For the case of continuous corn, `nycrop` = 1[cite: 1307]. If two crops are grown in a year, then `nycrop` = 2[cite: 1307]. The number of crops for a year, for the purpose of WEPP model inputs, is determined in the following manner: For a single crop planted in the spring and harvested in the fall, the value of `nycrop` is 1[cite: 1307]. However, any time during a year that another crop is present on a field, it must be counted as another crop[cite: 1307]. For example, for a continuous winter wheat rotation, the wheat growing from January 1 to a harvest date in July is crop number 1, while the wheat planted in October and growing to December 31 is crop number 2[cite: 1308]. Another example would be a perennial alfalfa growing from January 1 to March 30, plowing the alfalfa under on March 30, a corn crop planted on April 25 and harvested on October 11, then planting a winter wheat crop on October 17[cite: 1308]. Here the alfalfa would be crop number 1, the corn would be crop number 2, and the wheat would be crop number 3[cite: 1308, 1309]. For areas in which the field lies fallow for periods of time in conjunction with planting of winter annuals, care must be taken to include a fallow crop at the beginning of the calendar year as crop number 1, followed by the winter annual planted that fall as crop number 2[cite: 1309].
* **Man.MAN.loop.loop.loop.man:**
    * 10.1) Yearly Scenario index used this Year on this OFE with this Crop, integer - (`manindx`) [cite: 1311]
    * ***Note*** `manindx` is an index of one of the defined ordered Management Scenarios[cite: 1312].
    * ***Notes*** Man.MAN.loop.loop.loop (line 10.1) values repeat for the total number of crops grown during the current year on the current OFE (`nycrop`)[cite: 1313].
    * Man.MAN.loop.loop.loop values repeat `nofe` times[cite: 1314].
    * Man.MAN.loop.loop values repeat `nyears` times[cite: 1314].
    * Man.MAN.loop values repeat `nrots` times[cite: 1314].


## Markdown Generation

This was generated from https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum2024.pdf using Gemini/AI Pro 2.5 and the following prompt

```
Pages 31-51 document the plant (management) files for wepp. I would like to convert this file specification to markdown format to support LLM use.

Please convert Plant/Management Input File section to markdown being careful to capture all the content, without changing, adding, or omitting content related to the file specification. Keeping the spelling and wording exactly as in this document. Use markdown conventions that will support use in frontier language models like LLMs and will be human readable
```