# Windows WEPP User Summary 2024

Cleaned Markdown reference for the Water Erosion Prediction Project (WEPP)
user summary distributed with legacy and current WEPP model/interface
materials.

## Document Status

- This page is a cleaned, scan-friendly Markdown version of a PDF-derived
  WEPP user summary.
- The source material spans legacy WEPP versions `95.7` and `98.4`, plus
  2024 Windows release materials.
- The goal of this copy is readability and machine parsing, not exact
  page-for-page reproduction of the source PDF.
- Some figure-heavy or table-heavy source sections are abbreviated or omitted
  where the converted Markdown did not preserve them cleanly.
- Treat this page as a historical and technical reference. For current
  line-by-line file formats in Usersum, prefer the separate plant, soil, and
  climate specification pages linked below.

## Related File Specifications

For canonical field-by-field file formats, use these pages instead of relying
on this legacy summary alone:

- [Plant File Specification](../input-file-specifications/plant-file.spec.md)
- [Soil File Specification](../input-file-specifications/soil-file.spec.md)
- [Climate Input File Specification](../input-file-specifications/climate-file.spec.md)
- [CLIGEN Station Statistics Input File Format](../input-file-specifications/cligenparms.md)

## How To Use This Page

- Start with [Quick Start](#quick-start) if you need installation context for
  the Windows interface.
- Use [Model Description](#model-description) to understand hillslope versus
  watershed scope, required inputs, and output types.
- Use [Plant and Irrigation Inputs](#plant-and-irrigation-inputs) for crop
  parameters and irrigation file formats.
- Use [Impoundment File](#impoundment-file) and
  [Supplemental WEPP Input Files](#supplemental-wepp-input-files) for
  specialized inputs.
- Use [Appendix](#appendix) for sample values and example plant/management
  files.
- Use [Related File Specifications](#related-file-specifications) when you need
  the current canonical input-file formats used in Usersum.

## Publication Metadata

- Report family: NSERL Report No. 11.
- Original publication date named in the source material: July 1995.
- Release packet years named in the source material: 1995, 2012, and 2024.
- Agencies named in the source material: USDA Agricultural Research Service,
  USDA Natural Resources Conservation Service, USDA Forest Service, and USDI
  Bureau of Land Management.
- The original cover illustration contrasts hillslope erosion processes with
  watershed routing elements such as OFEs, channels, impoundments, and the
  watershed outlet.

## Support and Credits

This user summary document is part of a packet of material released with the
WEPP erosion prediction model, interface, file builders, graphics plotting
programs, and sample data sets.

**WEPP Technical Support**

- USDA-ARS National Soil Erosion Research Laboratory
- 275 South Russell St.
- West Lafayette, IN 47907
- Phone: `(765) 494-8673`
- Fax: `(765) 494-5948`
- Email: <wepp@ecn.purdue.edu>
- Web:
  <https://www.ars.usda.gov/midwest-area/west-lafayette-in/national-soil-erosion-research/docs/wepp/research/>

**Editors:** Dennis C. Flanagan and Stanley J. Livingston

**Contributors**

- James C. Ascough
- Claire Baffaut
- Billy Barfield
- Lois A. Deer-Ascough
- Dennis C. Flanagan
- Mary R. Kidwell
- Eugene R. Kottwitz
- John M. Laflen
- Mark Lindley
- Stanley J. Livingston
- Mark A. Nearing
- Arlin D. Nicks
- M. Reza Savabi
- Anda Singher
- Diane E. Stott
- Mark A. Weltz
- David A. Whittemore
- Jim Frankenberger
- Joan Wu
- Shuhui Dun
- Anurag Srivastava

**Disclaimer:** All information, computer software, and databases contained in
the accompanying install package are believed to be accurate and reliable. The
United States Department of Agriculture and the Agricultural Research Service
accept no liability or responsibility of any kind to any user, other person, or
entity as a result of installation or operation of this software. The software
is provided "AS IS," and the user assumes all risks when using it.

The WEPP programs, databases, and other information were developed with funds
from agencies of the United States Government and may not be copyrighted.

## Quick Start

### System Requirements

This version of the Water Erosion Prediction Project (WEPP) model is designed
to run on Microsoft Windows 10 and 11 PCs. The WEPP model is also available for
Ubuntu Linux systems. The model is compatible with both 32-bit and 64-bit
systems.

### Installation

Download the WEPP model and interface from:

<https://www.ars.usda.gov/midwest-area/west-lafayette-in/national-soil-erosion-research/docs/wepp/wepp-downloads/>

The Windows installer is typically named `weppwin-2024-installer.exe`.

The recommended WEPP install package requires administrator privileges. In
addition to the WEPP model software, the WEPP user interface requires the
Microsoft Visual C++ redistributable. This Microsoft package is installed
automatically when needed.

If you do not have administrator privileges, the non-admin WEPP install package
can be used. It will attempt to use whatever compatible Microsoft Visual C++
redistributable is already installed on the system. If no compatible Microsoft
package is installed, the full WEPP installation must be done as an
administrator.

## Introduction

The objective of the Water Erosion Prediction Project is "to develop new
generation water erosion prediction technology for use by the USDA-Soil
Conservation Service, USDA-Forest Service, and USDI-Bureau of Land Management,
and other organizations involved in soil and water conservation and
environmental planning and assessment" (Foster and Lane, 1987).

The computer programs in the install package are a major step toward meeting
that objective. The WEPP erosion model represents prediction technology based
on fundamental hydrologic and erosion mechanics science. WEPP allows both
spatial and temporal estimates of erosion and deposition on watersheds
consisting of hillslopes, channels, and impoundments. These watersheds may
range from very simple and uniform to very complex and nonuniform.

The satellite programs accompanying WEPP include a user interface, file
builders, and graphics programs. The interface is intended to make it easier to
organize WEPP runs and input/output files. The file builders allow rapid
creation or modification of model input files. The graphics programs allow the
user to view predicted detachment and deposition on the profile, along with
other variables through time.

## Model Description

### Model Summary

The WEPP model may be used in both hillslope and watershed applications. It is
a distributed-parameter, continuous-simulation erosion prediction model
implemented as a set of computer programs for personal computers.

Distributed input parameters include rainfall amounts and intensity, soil
texture, plant growth parameters, residue decomposition parameters, tillage
effects on soil properties and residue amounts, slope shape, steepness,
orientation, and soil erodibility parameters.

Continuous simulation means that the model simulates multiple years, with each
day having its own climatic inputs. On each simulation day a storm may occur.
That storm may or may not produce runoff. If runoff is predicted, the model
calculates soil loss, sediment deposition, sediment delivery off-site, and
sediment enrichment for the event, then adds those values to running totals.
At the end of the simulation period, average values for detachment, deposition,
sediment delivery, and enrichment are determined by dividing by the selected
time interval.

The entire set of important erosion-related parameters is updated daily,
including soil roughness, surface residue cover, canopy height, canopy cover,
and soil moisture. This continuous updating relieves the user of the difficult
task of estimating temporal distributions for important parameters such as
cover values.

In watershed applications, the WEPP model applies to field areas that include
ephemeral gullies that may be farmed over and are known as concentrated flow
gullies, or constructed waterways such as terrace channels and grassed
waterways. For rangeland applications, it applies to areas that include
gullies up to about 1 to 2 meters (3 to 6 ft) wide and about 1 meter (3 ft)
deep.

The hillslope routines of WEPP are used for the overland-flow portion of the
area, and the watershed routines are used for channels and impoundments. The
procedure does not apply to areas having permanent channels such as classical
gullies and perennial streams.

A watershed is defined as one or more hillslopes draining into one or more
channels and/or impoundments. The smallest possible watershed includes one
hillslope and one channel. Runoff characteristics, soil loss, and deposition
are first calculated on each hillslope with the hillslope component of WEPP for
the entire simulation period. Main results are saved in a pass file that is
used during watershed routing.

The model then combines results from each hillslope and performs runoff and
sediment routing through the channels and impoundments each time runoff is
produced on one of the hillslopes or channels, or when there is outflow from
one of the impoundments. Channel and impoundment parameters such as canopy
height and impoundment water level are updated daily.

The major WEPP inputs are:

- a climate data file,
- a slope data file,
- a soil data file,
- a cropping/management data file.

If irrigation is being simulated, additional input files are required.
Watershed applications also require files describing watershed configuration,
channel characteristics, and impoundment characteristics.

The climate file can be built using the CLIGEN program, either inside the WEPP
interface or independently, with access to more than 2700 U.S. weather
stations. The slope, soil, and cropping/management files can be created either
through interface file builders or with a text editor.

Beyond hillslope inputs, a watershed simulation requires additional files to
describe:

- watershed configuration (`structure` file),
- channel topography (`channel slope` file),
- channel soils (`channel soil` file),
- channel management practices (`channel management` file),
- channel hydraulic characteristics (`channel` file).

If the user chooses to simulate impoundments and/or irrigation, an impoundment
file and/or irrigation file is also required.

The WEPP computer program produces many kinds of output, in varying quantity
depending on user choices. The most basic output contains runoff and erosion
summary information, which may be produced on a storm-by-storm, monthly,
annual, or average annual basis.

The time-integrated estimates of runoff, erosion, sediment delivery, and
sediment enrichment are contained in this output, along with the spatial
distribution of erosion on the hillslope. The program predicts detachment or
deposition at a minimum of 100 points on a hillslope. The sum totals of these
values are divided by the number of simulation years to give average annual
detachment or deposition at each point.

Some points on a hillslope may experience detachment during some rainfall
events and deposition during others. The output file is clearly divided into an
on-site section and an off-site section.

The on-site section includes:

- average annual soil loss over areas experiencing net soil loss,
- average sediment deposition occurring on the hillslope,
- a table of detachment/deposition at a minimum of 100 points.

The off-site section includes:

- estimated average annual sediment delivery from the hillslope,
- particle-size distributions of detached sediment and delivered sediment,
- an estimate of enrichment of the sediment specific surface area.

This information can be useful in assessing impacts of management systems on
sediment and sediment-borne pollutants reaching waterways.

For watershed applications, the watershed component of WEPP also produces
several output types. The most basic is erosion and runoff summary output for
the whole watershed on a monthly, annual, or average annual basis.

That output includes:

- runoff and sediment yield estimates for each watershed element,
- summary results for the whole watershed,
- sediment delivery ratio,
- enrichment ratio,
- specific surface index,
- particle-size distribution of sediment leaving the area.

If impoundments are present, an impoundment output file may also be created.
That file can report, on annual and average annual bases, incoming and outgoing
runoff and sediment volumes, including incoming and outgoing volumes for each
sediment particle class.

Abbreviated summary information for each runoff event can also be generated.
This event output file is similar to the hillslope event output file.
Similarly, a large graphical output data file can be created for plotting
different variables. Other outputs include detailed soil, plant, water balance,
crop, yield, winter, and rangeland files for users who want to inspect model
behavior under specific conditions.

For each hillslope, spatial detachment/deposition information may also be
written to a plotting output file. When used with the plotting program, this
allows the user to view the hillslope profile shape and the predicted locations
of detachment and deposition.

## WEPP Interface Program

### Purpose

The purpose of the WEPP interface program is to give users an easier way to
interact with the WEPP erosion model. The interface provides tools to:

- create and modify model inputs,
- organize sets of model simulation runs,
- view and interpret model outputs quickly.

### Hardware and Setup Requirements

This version of the Water Erosion Prediction Project (WEPP) model is designed
to run on Microsoft Windows personal computers. The source material describes
support for 32-bit and 64-bit Windows 7, Windows 10, and Windows 11 systems.

### Windows Interface Installation

For installation instructions and examples, see the WEPP Windows Interface
Tutorials:

- 2013 version:
  <https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/wepp-tutorial-2013.pdf>
- 2024 version:
  <https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/wepp-tutorial-2024.pdf>

## Plant and Irrigation Inputs

### Plant-Specific Parameters for Cropland

For the canonical plant/management file format used in Usersum, start with
[Plant File Specification](../input-file-specifications/plant-file.spec.md).
The material below is preserved from the Windows WEPP user summary because it
adds parameter interpretation and historical context beyond the schema alone.

The WEPP crop growth model is a modification of the EPIC crop growth model
(Williams et al., 1989) that accounts for water and temperature stress on
biomass production and harvested yield. The WEPP crop component was designed so
that parameters may be adjusted for different crops and for variation within
crop varieties.

Table 17 in the original source materials, along with the WEPP management file
builder, includes estimates of crop parameters for many major U.S. crops that
should provide realistic results. Since the crop growth component was not
intended to serve as a crop yield prediction model, parameter adjustment should
be done carefully and only when supported by data or research need.

When actual yield or biomass differs substantially from WEPP predictions, or
when parameters are unavailable for a crop of interest, plant parameters may be
adjusted with care. Before doing so, other possible sources of error should be
considered. Crop inputs are generally best modified for research or sensitivity
analysis.

The crop residue decomposition component of WEPP is based on the RESMAN residue
management model (Stott and Rogers, 1990; Stott and Barrett, 1993; Stott,
1991). This component estimates the amount of residue present daily as
standing, flat, or buried, as well as dead roots. It also estimates the amount
of surface cover provided by that residue.

When the crop of interest is not listed in the WEPP management file, it is
usually best to start from the parameters of a similar crop already present in
the crop file. If that is not feasible, such as for many vegetable crops, the
Crop Parameter Intelligent Database System (CPIDS) may be useful for
parameterization support. Any refinements should better represent actual field
growing conditions such as canopy cover, canopy height, and biomass, rather
than simply forcing crop yield.

Key parameters preserved from the source material:

- **BB**: Describes the relationship between canopy cover and vegetative
  biomass (see Figure 3 in the source materials). Increasing `BB` causes canopy
  cover to develop more rapidly as biomass accumulates. Adjust carefully and,
  when possible, use field biomass and canopy-cover data.
- **BBB**: Canopy height parameter. `BBB` defines the relationship between
  vegetative biomass and canopy height (see Figure 4 in the source materials).
  Higher values indicate greater canopy height for a given biomass. `BBB`
  affects the rate at which maximum canopy height is reached, not the maximum
  height itself.
- **BEINP (kg/MJ)**: Biomass energy ratio. This reflects the potential growth
  rate of a crop per unit of intercepted photosynthetically active radiation.
  `BEINP` can strongly affect growth rate, stress timing, and yield. Adjust it
  only when clearly justified by research data from unstressed cropping
  conditions.
- **BTEMP (deg C)**: Minimum or base daily air temperature required for plant
  growth. Base temperatures are generally stable within cultivars of a species.
  The source material recommends changing `GDDMAX`, not `BTEMP`, when modeling
  crops with different maturity timing.
- **CF (m^2/kg)**: Converts residue mass to percent surface cover. This is an
  important parameter because WEPP erosion routines are sensitive to percent
  surface cover.
- **CRIT (deg C days)**: Growing degree day accumulation from planting to
  emergence. WEPP considers plants emerged when `CRIT` is reached or at 14 days
  after planting, whichever comes first.
- **CRITVM (kg/m^2)**: Critical live biomass value of a perennial crop below
  which grazing is not allowed. If live biomass falls below `CRITVM`, grazing
  is disallowed for that day.

#### Adjusting the BEINP Plant Growth Parameter

In terms of erosion, one of the most important plant-growth factors is the
amount of biomass produced by the crop. `BEINP` is the biomass energy
conversion factor. Increasing `BEINP` increases biomass production, which in
turn increases both residue left at harvest and crop yield.

The relative amount of yield versus total biomass can be adjusted using the
harvest index. For example, if a corn variety produces 8000 lb/acre of residue
and 120 bu/acre of grain on average, a user may adjust `BEINP` and `HI` until
the model reproduces those amounts over a long-term simulation. If a different
variety produces more stalk residue at similar grain yield, `BEINP` may be
increased and `HI` reduced to reflect that difference.

Grain yield does not directly control erosion calculations, but residue left at
harvest has a significant effect on erosion. The WEPP interface management file
builder includes crop parameter data for low-, medium-, and high-productivity
corn and soybeans, as well as a lodging-resistant corn variety.

### Irrigation Input Files

Both stationary sprinkler and furrow irrigation can be simulated in a hillslope
profile application of the WEPP erosion model. Zero, one, or two irrigation
data files may be required depending on the irrigation scheduling option used.
Formats for these files depend on both irrigation method and scheduling
approach.

#### Depletion-Level Irrigation Scheduling

Table 18 in the source materials describes irrigation input parameters used
with depletion-level scheduling for both sprinkler and furrow irrigation.
Sample irrigation data files are referenced in the appendix of the source
materials.

Lines 1 and 2 contain variables used to confirm the file format. Line 3
contains variables that do not change during the simulation. Line 4 contains
variables that define operating parameters each time irrigation occurs. The
Line 3 and Line 4 formats differ between stationary sprinkler and furrow
systems.

**Table 18. Depletion-level scheduling irrigation input data file description**

| Line | Description |
| :--- | :--- |
| **Line 1** | version control number (`95.7`) - real (`datver`) |
| **Line 2** | a) number of overland flow elements - integer (`itemp`) |
| | b) flag indicating irrigation system type - integer (`jtemp`) |
| | `1` = stationary sprinkler |
| | `2` = furrow |
| | c) flag indicating irrigation scheduling type - integer (`ktemp`) |
| | `1` = depletion |
| **Line 3** | a) minimum irrigation depth (`m`) - real (`irdmin`) |
| | b) maximum irrigation depth (`m`) - real (`irdmax`) |
| | Note: Line 3b is not included in furrow irrigation data files. |
| **Stationary sprinkler irrigation systems (`jtemp = 1` on Line 2b)** | |
| **Line 4** | a) OFE identifier for the line - integer (`ofeflg`) |
| | b) irrigation application rate (`m/s`) - real (`irrate`) |
| | c) ratio of application depth to water needed to fill the soil profile to field capacity - real (`aprati`) |
| | d) maximum ratio of available soil water depletion to available water-holding capacity at which irrigation occurs - real (`deplev`) |
| | e) sprinkler nozzle impact energy factor - real (`nozzle`) |
| | f) Julian date at beginning of irrigation window - integer (`irbeg`) |
| | g) year at beginning of irrigation window - integer (`yrbeg`) |
| | h) Julian date at end of irrigation window - integer (`irend`) |
| | i) year at end of irrigation window - integer (`yrend`) |
| **Furrow irrigation systems (`jtemp = 2` on Line 2b)** | |
| **Line 4** | a) OFE identifier for the line - integer (`ofeflg`) |
| | b) identifier for the last OFE over which irrigation water should advance - integer (`endpln`) |
| | c) furrow supply rate (`m^3/s`) - real (`florat`) |
| | d) estimated supply duration to a furrow (`s`) - real (`timest`) |
| | e) number of supply-rate/duration combinations - integer (`depsrg`) |
| | `1` = continuous |
| | `2` = cutback |
| | `4` through `6` = surge |
| | f) ratio of desired application depth at lower end of furrow to water needed to fill soil profile to field capacity (`m/m`) - real (`filrat`) |
| | g) maximum ratio of available soil water depletion to available water-holding capacity at which irrigation occurs - real (`deplev`) |
| | h) Julian date at beginning of irrigation window - integer (`irbeg`) |
| | i) year at beginning of irrigation window - integer (`yrbeg`) |
| | j) Julian date at end of irrigation window - integer (`irend`) |
| | k) year at end of irrigation window - integer (`yrend`) |
| | Note: Line 4 is repeated as many times as needed to define all irrigation periods for all OFEs. |

#### Fixed-Date Irrigation Scheduling

Table 19 in the source materials describes irrigation input files for the
fixed-date scheduling option. Lines 1 and 2 are used to confirm file format.
Line 3 defines irrigation dates for specific OFEs.

For stationary sprinkler systems, Line 4 contains application rate, application
depth, and nozzle energy adjustment factor. For furrow systems, Line 4
contains the number of inflow-rate/duration combinations ("surges"), and
Line 5 contains the inflow-rate/duration information.

**Table 19. Fixed-date scheduling irrigation input data file description**

| Line | Description |
| :--- | :--- |
| **Line 1** | version control number (`95.7`) - real (`datver`) |
| **Line 2** | a) number of overland flow elements - integer (`itemp`) |
| | b) flag indicating irrigation system - integer (`jtemp`) |
| | `1` = stationary sprinkler |
| | `2` = furrow |
| | c) flag indicating irrigation scheduling type - integer (`ktemp`) |
| | `2` = fixed-date |
| **Line 3** | a) OFE identifier for the line - integer (`ofeflg`) |
| | b) Julian date of the irrigation event - integer (`irday`) |
| | c) year of the irrigation event - integer (`iryr`) |
| **For stationary sprinkler irrigation systems (`jtemp = 1` on Line 2b)** | |
| **Line 4** | a) application rate for current OFE (`m/s`) - real (`irint`) |
| | b) irrigation depth for current OFE (`m`) - real (`irdept`) |
| | c) nozzle energy adjustment factor - real (`nozzle`) |
| | Note: Lines 3 and 4 are repeated as many times as needed to define all irrigation periods for all OFEs. |
| **For furrow irrigation systems (`jtemp = 2` on Line 2b)** | |
| **Line 4** | a) number of inflow-rate/duration combinations - integer (`surges`) |
| | Note: maximum surges allowed is `20`. |
| **Line 5** | a) supply rate to furrow during time period (`m^3/s`) - real (`qspply`) |
| | b) beginning time from midnight for a particular supply rate (`s`) - real (`tstart`) |
| | c) ending time from midnight for a particular supply rate (`s`) - real (`tend`) |
| | d) duration of the depletion phase (`s`) - real (`tdepl`) |
| | Note: Lines 3, 4, and 5 are repeated as many times as needed to define all irrigation periods for all OFEs. |

## Run Files

### Hillslope Input Run File

The WEPP erosion model may be run in two ways:

- interactively, with the user typing responses to run-time questions;
- automatically, with those responses supplied through an input run file.

The WEPP user interface creates these run files automatically based on the run
description completed within the interface. Figure 17 in the source materials
shows the screen input flow structure for the WEPP hillslope erosion model
(`95.7`).

### Watershed Input Run File

Similarly, the watershed version may be run either interactively or
automatically by supplying a run file. The interface creates this file based on
user selections. Figure 18 in the source materials depicts the input flow for
two watershed options:

- channel routing only,
- hillslope simulation plus channel routing.

## Impoundment File

**Table 28. Impoundment input file description**

The full impoundment input table was figure-heavy in the source PDF conversion
and is not reproduced here in full. The subsections below preserve the main
parameter descriptions that remained readable in the converted source.

### Drop Spillway

A drop spillway is a common outflow structure used in farm ponds and sediment
detention basins. It consists of a vertical riser connected to a horizontal or
near-horizontal barrel. To define the outflow function, the following
dimensions are required:

- `DRS`: diameter of circular riser (`m`) for circular risers
- `LRS`: length of riser box section (`m`) for box-section risers
- `WRS`: width of riser box section (`m`) for box-section risers
- `HRS`: stage of riser inlet (`m`)
- `Cw`: weir coefficient, usually `3.0` to `3.2`
- `Co`: orifice coefficient, approximately `0.6`
- `DBL`: diameter of barrel (`m`) for circular barrels
- `HBL`: height of barrel box section (`m`) for box-section barrels
- `LBL`: length of barrel box section (`m`) for box-section barrels
- `HRH`: height of riser inlet above barrel bottom (`m`)
- `LBL`: flow length of barrel (`m`)
- `SBL`: slope of barrel (`m/m`)
- `HBLOT`: height of barrel outlet above outlet-channel bottom (`m`)
- `Ke`: entrance loss coefficient; see Figure 11 in the source materials
- `Kb`: bend loss coefficient; see Table 29 in the source materials
- `Kc`: head loss coefficient; see Table 30 in the source materials

### Perforated Riser

Perforated risers are often used to slowly empty terrace systems. A perforated
riser is similar to a drop spillway in that both have a riser that empties into
a subsurface conduit. The perforated riser includes a bottom orifice plate to
limit flow to the subsurface conduit and slots along the riser to allow
complete drainage of the terrace.

A typical perforated riser contains `N` horizontal rows of side orifices spaced
a uniform distance `S`. The side orifices have a total area `As` distributed
over a length `Hs`. This type of riser also includes a bottom orifice plate
with flow area `Ab` located a distance `h_b` below the slots.

Parameters needed to define the outflow function:

- `Hr`: stage of the riser opening (`m`)
- `Hb`: height below the datum of the restricting orifice (`m`)
- `Hs`: height of the slots (`m`)
- `Hd`: stage of the datum, meaning the bottom of the slots (`m`)
- `Dr`: diameter of the riser (`m`)
- `As`: total slot area (`m^2`)
- `Db`: diameter of the restricting orifice (`m`)
- `Cb`: orifice coefficient for the restricting orifice, approximately `0.6`
- `Cs`: orifice coefficient for the slots, approximately `0.611`

The following variables are the same as for the drop inlet spillway:

- `Hrh`: height of riser inlet above barrel bottom (`m`)
- `LBL`: flow length of barrel (`m`)
- `SBL`: slope of barrel (`m/m`)
- `DBL`: diameter of the barrel (`m`)
- `Cw`: weir coefficient, usually `3.0` to `3.2`
- `Co`: orifice coefficient, approximately `0.6`
- `Ke`: entrance loss coefficient
- `Kb`: bend loss coefficient
- `Kc`: head loss coefficient

### Culvert

Culverts, sometimes called trickle-tube spillways, can be used as outlet
structures for farm ponds and sediment basins. Culverts are also used to
control flow under roadways, often producing ponding upstream and forming an
impoundment.

WEPP allows the user to enter information on two sets of `Ncv` identical
culverts. For each set, the following dimensions are needed:

- `Ncv`: number of identical culvert outlet structures
- `Acv`: cross-sectional area of culvert (`m^2`)
- `HITcv`: cross-sectional height of culvert (`m`) for square conduits, or
  diameter for circular conduit
- `Hcv`: stage of culvert inlet (`m`)
- `Lcv`: flow length of culvert (`m`)
- `Scv`: slope of culvert (`m/m`)
- `Hcvot`: height of culvert outlet above outlet-channel bottom (`m`)
- `Ke`: entrance loss coefficient
- `Kb`: bend loss coefficient
- `Kc`: friction loss coefficient
- `K`, `M`, `c`, `Y`: inlet-control coefficients

### Emergency Spillways and Open Channels

In larger farm ponds and sediment basins, emergency spillways are used to route
excess runoff from large storms that cannot be routed through the principal
spillway. This reduces the risk of overtopping and breaching an earthen dam.

Emergency spillways typically have three sections:

- a sloped approach,
- a flat crest,
- a sloped exit.

In WEPP, open channels are defined as emergency spillways. Parameters needed to
define the outflow function include:

- `BWES`: bottom width of exit channel (`m`)
- `SSES`: side slopes of exit channel (`m/m`)
- `NES`: Manning's `n` for vegetation in the exit channel
- `HES`: stage of exit channel or stage of beginning of a user-defined
  stage-discharge relationship (`m`)
- `HMXES`: maximum stage for flow through the exit channel (`m`)
- `SES1`: slope of section 1 of the exit channel (`m/m`)
- `LES1`: length of section 1 of the exit channel (`m`)
- `SES2`: slope of section 2 of the exit channel (`m/m`)
- `LES2`: length of section 2 of the exit channel (`m`)
- `SES3`: slope of section 3 of the exit channel (`m/m`)

### Rock-Fill Check Dam

Construction, mining, and silviculture operations often need inexpensive
temporary sediment traps. Porous rock-fill check dams provide a relatively
simple solution. A porous rock-fill check dam is essentially a pile of rock
that obstructs the free flow of sediment-laden water.

To define the outflow function, the following parameters are needed:

- `LRF`: flow length of the rock-fill check dam (`m`)
- `HRF`: stage at which flow through the rock-fill check dam occurs (`m`)
- `HOTRF`: stage at which the rock-fill check dam is overtopped (`m`)
- `WRF`: cross-sectional width of the rock-fill check dam (`m`)
- `DRF`: average diameter of the rocks forming the check dam (`m`)

### Filter Fence, Straw Bales, and Trash Barriers

Check dams can also be constructed with straw bales or filter fence. These
structures are inexpensive and easy to build. A slurry flow rate is used to
determine discharge through a filter fence, straw bales, or a trash barrier.

The source material notes two cautions:

- slurry flow rates are estimates at best,
- if overtopping occurs, the structure should be redesigned or replaced with a
  more permanent structure.

Parameters needed to define the outflow function:

- `VSL`: slurry flow rate (`m/s`)
- `WFF`: average cross-sectional width of filter fence, straw bales, or trash
  barrier (`m`)
- `HFF`: stage at which flow through the structure begins (`m`)
- `HOTFF`: stage at which the structure is overtopped (`m`)

### General Impoundment Characteristics and Stage-Area-Length Relationships

Miscellaneous inputs include parameters that are not specific to one outflow
structure but are required for simulation. Stage-area-length relationships are
represented as power functions developed from discrete stage-area-length points
entered by the user. Since regression routines are used to develop these power
functions, the source material recommends entering as many points as possible,
ideally more than 10.

Parameters preserved from the source material:

- `HOT`: stage at which the overtop flag goes off (`m`). This flag alerts the
  user that simulated stage exceeded the chosen overtop stage.
- `HFULL`: stage at which the full-of-sediment flag goes off (`m`). This flag
  alerts the user that sediment has filled the impoundment above the designated
  full stage.
- `H`: stage at the beginning of the simulation (`m`), often the permanent
  pool stage.
- `DT`: initial time step (`hr`). The source suggests `0.1 hr`, or `0.01 hr`
  for filter fences.
- `QINF`: infiltration rate (`m/d`), defined either as the saturated hydraulic
  conductivity of a confining layer, or the conductivity of a porous layer over
  an impervious layer.
- `ISIZE`: structure size classification:
  - `1` indicates a small terrace, filter fence, or porous rock-fill check dam
    with little or no permanent pool.
  - `2` indicates a larger farm pond, greater than `1 ac`, with a permanent
    pool deeper than `1 m`.
- `NDIV`: number of particle-size subclass divisions. The source recommends
  `2`.
- `HMIN`: minimum stage (`m`)
- `AMIN`: area at minimum stage (`m^2`)
- `LMIN`: length at minimum stage (`m`)
- `NALPTS`: number of stage-area-length points used; ideally greater than `10`
- `HAL(I)`: stage at point `I` (`m`)
- `AREA(I)`: area at point `I` (`m^2`)
- `LENGTH(I)`: length at point `I` (`m`)

### Example Impoundment Input File

The original PDF included an image-based example. That example did not survive
cleanly in the converted Markdown and is not reproduced here.

### Impoundment Output Files

The impoundment output files provide summary information on impoundment
performance on daily, monthly, yearly, and full-simulation time scales. The
source material describes three output files:

- the user-specified output summary file,
- `hydraulc`,
- `sediment`.

## Supplemental WEPP Input Files

If these optional files are present, they supply extra inputs to the WEPP model
to further customize simulation behavior. The source material states that these
files should be placed in the same directory as the `.run` file.

### `partsize.dat`

This file allows a custom particle-size distribution for detached sediment to
be supplied to WEPP instead of the default five classes built into the model.
Up to 10 particle-size classes can be specified, and each OFE must also be
defined in the file. This file is mainly used for mining applications where the
default agricultural assumptions are not appropriate.

The source material notes that this model version should function properly for
single-OFE hillslopes, but had not been well tested for multiple-OFE
hillslopes.

Format summary:

- **Line 1**: number of particle-size classes for an OFE (`npart`)
- **Line 2**: particle-class information
  - `frac`: fraction of detached sediment in this size class at point of
    detachment
  - `dia`: diameter of this size class (`mm`)
  - `spg`: specific gravity of this size class (`g/cc`)
  - `frcly`: fraction of primary clay in this size fraction (`g/g`)
  - `frslt`: fraction of primary silt in this size fraction (`g/g`)
  - `frsnd`: fraction of primary sand in this size fraction (`g/g`)
  - `frorg`: fraction of organic matter in this size fraction (`g/g`)

Line 2 repeats for the number of size classes given on Line 1. Lines 1 and 2
then repeat for the number of OFEs in the simulation.

### `wepp_ui.txt`

The presence of this file activates an alternate water-balance computation that
uses an hourly time step. The default WEPP water balance uses a daily time
step. When using this option, the soil file format should be the `7778`
format. The file itself is empty.

### `beinpcalib.txt`

This file contains a list of biomass energy parameter (`BEINP`) adjustment
factors that modify the `BEINP` values in the management input file. It is
mainly intended to make yield and biomass calibration easier.

After a model run is completed, yield values can be analyzed and subsequent
runs can adjust the calibration factors in this file without creating a new
management file. The number and order of crops in the management file must
match the number and order of crops in `beinpcalib.txt`.

A value of `1.0` leaves the existing `BEINP` value unchanged:

`NEW_BEINP = BEINP * factor`

Format summary:

- crop name matching the crop name from the management file
- crop index matching the crop index from the management file
- adjustment factor to apply to `BEINP`

### `pmetpara.txt`

If this file exists, WEPP assumes the user wants to use the FAO
Penman-Monteith dual-coefficient method for evapotranspiration.

The source material points to the FAO Irrigation and Drainage Paper 56,
_Crop Evapotranspiration: Guidelines for Computing Crop Water Requirements_,
for representative `kcb` and `p` values:

<https://www.fao.org/4/X0490E/x0490e00.htm#Contents>

Format summary:

- **Line 1**: number of records (lines) in the file
- **Line 2**: Penman-Monteith parameters
  - crop name matching a crop in the management file
  - mid-season crop coefficient (`kcb`)
  - coefficient `p` for readily available root-zone soil water (`rawp`)
  - line integer, not used
  - logical name/comment string

### `frost.txt`

This file defines soil sublayers for improved freeze-thaw modeling. For more
detail, see Dun et al. (2010).

Format summary:

- **Line 1**
  - apply water redistribution in soil layers (`1 = yes`, `0 = no`)
  - number of freeze/thaw layers in the top two 10 cm soil layers
  - number of freeze/thaw layers within each remaining 20 cm soil layer
- **Line 2**
  - thermal conductivity adjustment factor for snow
  - thermal conductivity adjustment factor for residue
  - thermal conductivity adjustment factor for soil
  - lower conductivity limit for crop/fallow frozen soil
  - lower conductivity limit for pasture frozen soil
  - lower conductivity limit for forest frozen soil

If `frost.txt` is absent, the model uses default parameter values.

Citation:

Dun, S., Wu, J.Q., McCool, D., Frankenberger, J., and Flanagan, D. (2010).
Improving Frost-Simulation Subroutines of the Water Erosion Prediction Project
(WEPP) Model. _Transactions of the ASABE_, 53.
<https://doi.org/10.13031/2013.34896>

### `wepp-co2.txt`

This file reads CO2-specific parameters for each crop defined in the management
file. The source material describes this feature as optional, experimental, and
still in progress. It also notes that it does not correctly handle multiple
OFEs.

Format summary:

- **Line 1**: current atmospheric CO2 level for the simulation (`ppm`)
- **Line 2**
  - `vpth`: threshold vapor pressure deficit (`vpd`)
  - `vpda`: `vpd` above `vpth`
  - `vpdb`: fraction of maximum leaf conductance at a given `vpd`
  - `gsi`: maximum stomatal conductance (`m s^-1`)
  - `xptbe`: biomass energy ratio at elevated CO2 concentration
  - `xptco2`: elevated CO2 concentration corresponding to `xptbe`
  - `wavp`: parameter relating `vpd` to biomass energy ratio at `330 ppm`

Related citations preserved from the source material:

- Kimball, B.A. (1983). Carbon Dioxide and Agricultural Yield: An Assemblage
  and Analysis of 430 Prior Observations. _Agronomy Journal_, 75(5), 779-788.
  <https://doi.org/10.2134/agronj1983.00021962007500050014x>
- Korner, C., Scheel, J.A., and Bauer, H. (1979). Maximum leaf diffusive
  conductance in vascular plants. _Photosynthetica_, 13(1), 45-82.
- Stockle, C.O., and Kiniry, J.R. (1990). Variability in crop radiation-use
  efficiency associated with vapor-pressure deficit. _Field Crops Research_,
  25(3-4), 171-181.
  <https://doi.org/10.1016/0378-4290(90)90001-R>

### `tc.txt`

If this file is present in the same directory as the other WEPP input files,
another watershed output file named `tc_out.txt` is created. The source
material shows this output line shape:

`Element Chan Day Year Runoff Time of Storm Storm (m^3) Conc(hr) Dur(hr) Peak(hr)`

The input file `tc.txt` does not need to contain data. WEPP only checks for
its existence.

### `wepp_ch.txt`

The presence of `wepp_ch.txt` indicates that temporal channel erodibility
adjustments should be performed during a watershed simulation. The default WEPP
approach uses constant channel erodibility.

This file contains no data. Its presence alone triggers the behavior.

### `chan.inp`

The `chan.inp` file contains additional options for updated watershed routing
methods.

Format summary:

- **Line 1**
  - `ichout`: flag for channel-flow output type
    - `0` = no output
    - `1` = peak flow time and rate
    - `2` = daily average flow rate
    - `3` = time-step flow rate
  - `dtchr`: routing time step (`secs`)
- **Line 2**
  - `unit area baseflow coefficient` (`m^3/s/m^2`), typically `1e-6` or
    smaller
- **Line 3**
  - `nchnum`: number of channels to include in output
- **Line 4**
  - channel identifiers from the watershed structure file, listed on one line

## References

- Baumer, O.W. 1990. Prediction of soil hydraulic parameters. In: _WEPP Data
  Files for Indiana_. SCS National Soil Survey Laboratory, Lincoln, NE.
- Chow, V.T. 1959. _Open-Channel Hydraulics_. McGraw-Hill Publishing Company.
- Donahue, R.L., R.W. Miller, and J.C. Shickluna. 1977. _Soils: An
  Introduction to Soils and Plant Growth_. Prentice-Hall Inc., Englewood
  Cliffs, New Jersey.
- Federal Highway Administration. 1985. _Hydraulic Design of Highway
  Culverts_. Hydraulic Design Series No. 5. Report No. FHA-IP-85-15,
  Washington, D.C.
- Foster, G.R. and L.J. Lane (compilers). 1987. _User Requirements:
  USDA-Water Erosion Prediction Project (WEPP)_. NSERL Report No. 1,
  USDA-ARS National Soil Erosion Research Laboratory, West Lafayette, IN.
- Haan, C.T., B.J. Barfield, and J.C. Hayes. 1994. _Design Hydrology and
  Sedimentology for Small Catchments_. Academic Press, New York.
- Kiniry, J.R., V. Benson, and J.R. Williams. 1991. Potential heat units.
  Appendix VII. Crop Data. In: J.G. Arnold, J.R. Williams, R.H. Griggs, and
  N.B. Sammons (eds.), _SWRRBWQ - A Basin Scale Model for Assessing Management
  Impacts on Water Quality_ (draft manual), Temple, TX.
- Knisel, W.G. (editor). 1980. _CREAMS: A Field-Scale Model for Chemicals,
  Runoff, and Erosion from Agricultural Management Systems_. U.S. Department of
  Agriculture, Conservation Research Report No. 26.
- Lane, L.J., M.A. Nearing, J.J. Stone, and A.D. Nicks. 1989. WEPP hillslope
  profile erosion model user summary. Chapter S in L.J. Lane and M.A. Nearing
  (eds.), _USDA - Water Erosion Prediction Project: Hillslope Profile Model
  Documentation_. NSERL Report 2, USDA-ARS National Soil Erosion Research
  Laboratory, West Lafayette, Indiana.
- Lorenz, O.A. and D.N. Maynard. 1988. _Knott's Handbook for Vegetable
  Growers_, Third Edition. John Wiley and Sons, New York.
- Maryland Water Resources Administration. 1983. _Maryland Standards and
  Specifications for Soil Erosion and Sediment Control_. Annapolis, MD.
- Schwab, G.O., R.K. Frevert, T.W. Edminster, and K.K. Barnes. 1966. _Soil and
  Water Conservation Engineering_, Second Edition. John Wiley and Sons,
  New York, NY.
- Schwab, G.O., R.K. Frevert, T.W. Edminster, and K.K. Barnes. 1981. _Soil and
  Water Conservation Engineering_, Third Edition. John Wiley and Sons,
  New York, NY.
- Stott, D.E. and J.B. Rogers. 1990. _RESMAN: A residue management decision
  support program_. Public domain software. NSERL Publication No. 5.
  USDA Agricultural Research Service, National Soil Erosion Research
  Laboratory, West Lafayette, IN.
- Stott, D.E. and J.R. Barrett. 1993. RESMAN: Software for simulating changes
  in surface crop residue mass and cover. _Soil Science Society of America
  Journal_ (submitted August 1993).
- Stott, D.E. 1991. RESMAN: A tool for soil conservation education.
  _Journal of Soil and Water Conservation_, 46:332-333.
- Virginia Soil and Water Conservation Commission. 1980. _Virginia Erosion and
  Sediment Control Handbook_. Richmond, VA.
- Williams, J.R., A.D. Nicks, and J.G. Arnold. 1985. Simulator for water
  resources in rural basins. _ASCE Hydraulic Journal_, 3(6):970-986.
- Wight, J.R. 1987. _ERHYM-II: Model Description and User Guide for the Basic
  Version_. USDA, ARS, ARS 59.
- Wight, J.R. and J.W. Skiles (eds.). 1987. _SPUR: Simulation of Production
  Utilization of Rangeland. Documentation and User Guide_. USDA, ARS, ARS 63.
- Williams, J.R., C.A. Jones, J.R. Kiniry, and D.A. Spanel. 1989. The EPIC
  crop growth model. _Transactions of the ASAE_, 32(2):497-511.

## Appendix

### Estimated Values for Variables `SUMRTM` and `SUMSRM`

West Lafayette, Indiana continuous simulations on a silt loam soil.

| Cropping Management System | SUMRTM (kg/m^2) | SUMSRM (kg/m^2) |
| :--- | :--- | :--- |
| Continuous tilled fallow | 0.0 | 0.0 |
| Fall moldboard plow, corn | 0.03 | 0.18 |
| Spring chisel plow, corn | 0.03 | 0.65 |
| No-till corn with anhydrous application | 0.26 | 0.12 |
| Fall moldboard plow, soybeans | 0.03 | 0.13 |
| Spring chisel plow, soybeans | 0.03 | 0.02 |
| No-till soybeans | 0.03 | 0.0 |
| Continuous alfalfa | 0.0 | 0.0 |
| Continuous winter wheat | 0.10 | 0.40 |

Note: Users can obtain values for their location by using the warm-up feature
of the WEPP/Shell Interface and retrieving the `SUMRTM` and `SUMSRM` values
from the created initial condition files.

### Example Input Files

**Example Plant/Management Input File (`98.4`)**

```text
98.4
#
#
1 # number of OFE'S
1 # (total) years in simulation
#######################
# Plant Section
#
#######################
1
# Number of plant scenarios
Corn
High production level-125 bu/acre for Jefferson Iowa
J. M. Laflen, Feb 28, 1998
Cutting height 1 foot, non-fragile residue, 30 inch rows
1 #landuse
WeppWillSet
3.60000 3.00000 35.00196 10.00000 2.30000 55.00000 0.00000 0.30404 0.65000 0.05100
0.85000 0.98000 0.65000 0.99000 0.00000 1700.00000 0.50000 2.60099
2 # mfo <non fragile>
0.00650 0.00650 25.00000 0.25000 0.21900 1.51995 0.25000 0.00000 30 0.00000
0.00000 3.50000 0.00000
#######################
# Operation Section #
#######################
5 # Number of operation scenarios
FCSTACDP
`Field cultivator, secondary tillage, after duckfoot points
(from WEPP distribution database)
Maximum depth of 10 cm (4 inches)
1 #landuse
0.6000 0.3500 0
4 # pcode other
0.0250 0.3000 0.6000 0.3500 0.0150 1.0000 0.0500
TAND0002
`Tandem Disk'
From converted V92.2 file `ANSI1.MAN'
NOTE: MFO values are the min and max of original values.
1 #landuse
0.5000 0.5000 0
4 # pcode other
0.0500 0.2300 0.5000 0.5000 0.0260 1.0000 0.1000
PLDDO
`Planter, double disk openers'
(from WEPP distribution database)
Tillage depth of 2 inches
1 #landuse
0.2000 0.1000 6
1 # pcode - planter
0.0250 0.7500 0.2000 0.1000 0.0120 0.1500 0.0500
CULTMUSW
`Cultivator, row, multiple sweeps per row'
(from WEPP distribution database)
1 #landuse
0.4000 0.2000 0
4 # pcode other
0.0750 0.7500 0.4000 0.2000 0.0150 0.8500 0.0500
MOPL
`Plow, Moldboard', 8"
(from WEPP distribution database)
1 #landuse
0.9800 0.9500 0
4 # pcode other
0.0500 0.4000 0.9800 0.9500 0.0430 1.0000 0.1500
###############################
# Initial Conditions Section #
###############################
1
# Number of initial scenarios
Default
Default corn initial conditions set continuous corn spring/summer tillage only
90 percent cover, approximately 200 days since last tillage
500 mm of rain since last tillage in summer prior
1
#landuse
1.10000 0.00000 200 92 0.00000 0.90000
1 # iresd <Corn>
1 # mang annual
500.12601 0.02000 0.90000 0.02000 0.00000
1
# rtyp temporary
0.00000 0.00000 0.10000 0.20000 0.02540
0.50003 0.19997
############################
# Surface Effects Section #
############################
1
# Number of Surface Effects Scenarios
#
##
# Surface Effects Scenario 1 of 1
#
Year 1
From WEPP database
Your name, phone
1 # landuse cropland
5 # ntill number of operations
121 # mdate 5/1
1
# op FCSTACDP
0.102 # depth
2
# type
125 #mdate 5/5
2
# op TAND0002
0.102 # depth
2
# type
130 # mdate 5/10
3
# op PLDDO
0.051 # depth
2 # type
156 # mdate 6/5
4
# op CULTMUSW
0.076 # depth
2 # type
305
# mdate 11 / 1
5 # op --- MOPL
0.203 # depth
1 # type
#######################
# Contouring Section #
#######################
0 # Number of contour scenarios
#######################
# Drainage Section #
#######################
0 # Number of drainage scenarios
#######################
# Yearly Section
#
#######################
1 # looper; number of Yearly Scenarios
#
# Yearly scenario 1 of 1
#
Year 1
1
# landuse <cropland>
1
# plant growth scenario
1
# surface effect scenario
0
# contour scenario
0 # drainage scenario
1 # management <annual>
288 # harvest date --- 10 / 15 / 0
130 # planting date --- 5 / 10 / 0
0.7620 % row width
6
# residue man <none>
#######################
# Management Section #
#######################
Manage
description 1
description 2
description 3
1
# number of OFE's
1 # initial condition index
1
# rotation repeats
1
# years in rotation
##
#
# Rotation 1: year 1 to 1
#
1 # <plants/yr 1> OFE: 1>
1# year index
```

**Example Plant/Management Input File (`2017.1` format)**

```text
2017.1
#
#
##
#
1 # number of OFE'S
1 # (total) years in simulation
#######################
# Plant Section
#
#######################
1
# Number of plant scenarios
Corn
High production level-125 bu/acre for Jefferson Iowa
J. M. Laflen, Feb 28, 1998
Cutting height 1 foot, non-fragile residue, 30 inch rows
1
#landuse
WeppWillSet
3.60000 3.00000 35.00196 10.00000 2.30000 55.00000 0.00000 0.30404 0.65000 0.05100
0.85000 0.98000 0.65000 0.99000 0.00000 1700.00000 0.50000 2.60099
2 # mfo <non fragile>
0.00650 0.00650 25.00000 0.25000 0.21900 1.51995 0.25000 0.00000 30 0.00000
0.00000 3.50000 0.00000 0.00000
#######################
# Operation Section #
#######################
5 # Number of operation scenarios
FCSTACDP
`Field cultivator, secondary tillage, after duckfoot points
(from WEPP distribution database)
Maximum depth of 10 cm (4 inches)
1 #landuse
0.6000 0.3500 0
4 # pcode other
0.0250 0.3000 0.6000 0.3500 0.0150 1.0000 0.0500 0.0000 0.0000
TAND0002
`Tandem Disk'
From converted V92.2 file `ANSI1.MAN'
NOTE: MFO values are the min and max of original values.
1 #landuse
0.5000 0.5000 0
4 # pcode other
0.0500 0.2300 0.5000 0.5000 0.0260 1.0000 0.1000 0.0000 0.0000
PLDDO
`Planter, double disk openers'
(from WEPP distribution database)
Tillage depth of 2 inches
1 #landuse
0.2000 0.1000 6
1 # pcode planter
0.0250 0.7500 0.2000 0.1000 0.0120 0.1500 0.0500 0.0000 0.0000
CULTMUSW
`Cultivator, row, multiple sweeps per row'
(from WEPP distribution database)
1 #landuse
0.4000 0.2000 0
4 # pcode other
0.0750 0.7500 0.4000 0.2000 0.0150 0.8500 0.0500 0.0000 0.0000
MOPL
`Plow, Moldboard', 8"
(from WEPP distribution database)
1 #landuse
0.9800 0.9500 0
4 # pcode other
0.0500 0.4000 0.9800 0.9500 0.0430 1.0000 0.1500 0.0000 0.0000
###############################
# Initial Conditions Section #
###############################
1
# Number of initial scenarios
Default
Default corn initial conditions set continuous corn spring/summer tillage only
90 percent cover, approximately 200 days since last tillage
500 mm of rain since last tillage in summer prior
1
#landuse
1.10000 0.00000 200 92 0.00000 0.90000
1 # iresd <Corn>
1 # mang annual
500.12601 0.02000 0.90000 0.02000 0.00000
1 # rtyp - temporary
0.00000 0.00000 0.10000 0.20000 0.02540
0.50003 0.19997 0.00000 0.00000
############################
# Surface Effects Section #
############################
1
# Number of Surface Effects Scenarios
###
#
#
Surface Effects Scenario 1 of 1
#
Year 1
From WEPP database
Your name, phone
1 # landuse cropland
5 # ntill number of operations
121 # mdate -- 5/1
1
# op FCSTACDP
0.102 # depth
2
# type
125
#mdate 5/5
2
# op TAND0002
0.102 # depth
2
# type
130 # mdate 5/10
3 # op PLDDO
0.051 # depth
2 # type
156 # mdate 6/5
4
# op --- CULTMUSW
0.076 # depth
2
# type
305
# mdate 11 / 1
5 # op --- MOPL
0.203 # depth
1 # type
#######################
# Contouring Section #
#######################
0
# Number of contour scenarios
#######################
# Drainage Section #
#######################
0 # Number of drainage scenarios
#######################
# Yearly Section
#
#######################
1
# looper; number of Yearly Scenarios
#
# Yearly scenario 1 of 1
#
Year 1
1
# landuse <cropland>
1
# plant growth scenario
1
# surface effect scenario
0
% contour scenario
0
# drainage scenario
1 # management <annual>
288 # harvest date --- 10 / 15 / 0
130 # planting date --- 5 / 10 / 0
0.7620 % row width
6
# residue man <none>
#######################
# Management Section #
#######################
Manage
description 1
description 2
description 3
1
# number of OFE's
1 # initial condition index
1 # rotation repeats
1
# years in rotation
#
# Rotation 1: year 1 to 1
#
1 # <plants/yr 1> OFE: 1>
1# year index
```
