# WEPP Soil Input Files

### Data Versions

#### < 100 (e.g. 97.3)
Basic Soils

Each horizon specifies: solthk, sand, clay, orgmat, cec, rfg

#### 2006
Incorporated Restrictive Layer Parameters

#### 7777
Each horizon specifies: solthk, bd, ksat, fc, wp, sand, clay, orgmat, cec, rfg

#### 7778
Each horizon specifies: solthk, bd, ksat, anisotropy, fc, wp, sand, clay, orgmat, cec, rfg

#### 9001

Each OFE specifies: ksatadj, luse, stext, ksatfac, ksatrec (for modeling keff)

Calculate effective K from exponential function based on user defined ksat fac (ksatfac) and recovery (ksatrec) 

#### 9002
Each OFE specifies: ksatadj, luse, stext, ksatfac, ksatrec (for modeling keff)

Effective K calculated from Saxton and Rawls (2006)

#### 9003

Each OFE specifies: ksatadj, luse, burn_code, stext, texid_enum, uksat, lkeff (for revegetation)

Effective K calculated from Saxton and Rawls (2006) and restrict lower limit of keff for burn severities.


### Parameter descriptions

#### Soil
 - datver: dataversion (e.g. 2006, 7777, 7778, 9001, 9002, 9003)
 - solcom: User comment line - character*80 
 - ntemp: number of overland flow elements(OFE’s) or channels integer
 - ksflag: flag to use internal hydraulic conductivity adjustments
   - 0: do not use adjustments (conductivity will be held constant)
   - 1: use internal adjustments

#### OFE
 - slid: soil name for current OFE or channel
 - texid: soil texture for current OFE or channel
 - nsl: number of soil layers for current OFE or channel
 - salb: albedo of the bare dry surface soil on the current OFE or channel
 - sat: initial saturation level of the soil profile porosity (m/m)
 - ki: baseline interrill erodibility parameter (kg*s/m^4)
 - kr: baseline rill erodibility parameter (s/m)
 - shcrit: baseline critical shear parameter (N/m2) 
 - avke: effective hydraulic conductivity of surface soil (mm/h) _> 94.1 and < 2006.2_
 - luse: disturbed class (forest, shrub, grass, ...)
 - stext: simple soil texture (clay, clay loam, silt, sand)
 - ksatadj: flag to specify using soil saturation (`keff`) adjustment for forests
   - 0: do not adjust
   - 1: do internal adjustment
 - ksatfac: specifies lower bound for `keff` adjustment _9001_
 - ksatrec: exponential recovery parameter for `keff` adjustment _9001_

#### Horizon
 - solthk: horizon depth (mm)
 - bd: bulk density
 - ksat: hydraulic conductivity _< 94.1 or ≥ 7777_
 - anisotropy: _≥ 7778_
 - fc: field capacity _≥ 7778_
 - wp: wilting point _≥ 7778_
 - sand: percentage of sand content (%)
 - clay: percentage of  clay content (%)
 - orgmat: percentage of organic matter (%)
 - cec: cation exchange capacity in the layer (meq/100 g of soil)
 - rfg: percentage of rock fragments by volume in the layer (%)


#### Restrictive Layer
 - slflag: flag to specify restrictive layer
   - 0: no restrictive layer
   - 1: restritive layer present
 - ui_bdrkth: bed rock depth (mm)
 - kslast: hydraulic conductivity of restrictive layer
