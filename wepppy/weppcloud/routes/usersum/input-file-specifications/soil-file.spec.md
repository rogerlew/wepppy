# Soil Input File

Information on soil properties to a maximum depth of 1.8 meters are input to the WEPP model through the soil input file. The user may input information on up to 8 different soil layers. WEPP internally creates a new set of soil layers based on the original set parameter values. If the entire 1.8 meters is parameterized, the new soil layers represent depths of 0-100 mm, 100-200 mm, 200-400 mm, 400-600 mm, 600-800 mm, 800-1000 mm, 1000-1200 mm, 1200-1400 mm, 1400-1600 mm, 1600-1800 mm.

As with the slope file, soil parameters must be input for each and every Overland Flow Element (OFE) on the hillslope profile and for each channel in a watershed, even if the soil on all OFEs is the same.

Accurate estimation of soil physical and hydrological parameters is essential when operating the WEPP erosion prediction model. Table 3 lists the input parameters in the soil input file, and the discussion following the table is meant to assist the users in determining input parameter values. There are several versions of the soil file that can be used as input for WEPP. The differences in format are specified by the version number in line 1 which indicates how the remainder of the file is interpreted by WEPP.

## Soil input file description

- Line 1:

  version control number - real (datver)
  - 97.5 – Base set of soil properties
  - 2006.2 – Adds a separate restricting layer below profile
  - 7777 – Adds additional layer parameters
  - 7778 – Adds additional layer parameters and anisotropy ratio
  - 9002 - Adds `ksat` adjustment based on soil saturation
  - 9003 - Adds `lkeff` parameter
  - 9005 - Adds revegetation texture enum and understory conductivity controls


- Line 2:

  a) User comment line - character*80, (solcom)

- Line 3:

  a) number of overland flow elements(OFE’s) or channels integer (ntemp)

  b) flag to use internal hydraulic conductivity adjustments - integer (ksflag)
    - 0 - do not use adjustments (conductivity will be held constant)
    - 1 - use internal adjustments

**Lines 4 & 5 are repeated for the number of OFE's or channels on Line 3a.**

- Line 4:

  a) soil name for current OFE or channel - character (slid)

  b) soil texture for current OFE or channel - character (texid)

  c) number of soil layers for current OFE or channel - integer (nsl)

  d) albedo of the bare dry surface soil on the current OFE or channel - real (salb)

  e) initial saturation level of the soil profile porosity (m/m) - real (sat)

  f) baseline interrill erodibility parameter (kg*s/m4) - real (ki)

  g) baseline rill erodibility parameter (s/m) - real (kr)

  h) baseline critical shear parameter (N/m2) - real (shcrit)

  i) effective hydraulic conductivity of surface soil (mm/h) - real (avke)

- Line 5: _Version 97.5 and 2006.2 (repeated for the number of soil layers indicated on
Line 4c.)_

  a) depth from soil surface to bottom of soil layer (mm) - real (solthk)

  b) percentage of sand in the layer (%) - real (sand)

  c) percentage of clay in the layer (%) - real (clay)

  d) percentage of organic matter (volume) in the layer (%) - real (orgmat)

  e) cation exchange capacity in the layer (meq/100 g of soil) - real (cec)

  f) percentage of rock fragments by volume in the layer (%) - real (rfg)

- Line 5: Version 7777 _(repeated for the number of soil layers indicated on Line 4c.)_

  a) depth from soil surface to bottom of soil layer (mm) - real (solthk)

  b) Bulk density for layer (gm/cc)

  c) Hydraulic conductivity for layer (mm/h)

  d) Field capacity for layer (mm/mm)

  e) Wilting point for layer (mm/mm)

  f) percentage of sand in the layer (%) - real (sand)

  g) percentage of clay in the layer (%) - real (clay)

  h) percentage of organic matter (volume) in the layer (%) - real (orgmat)

  i) cation exchange capacity in the layer (meq/100 g of soil) - real (cec)

  j) percentage of rock fragments by volume in the layer (%) - real (rfg)

Line 5: _Version 7778 _(repeated for the number of soil layers indicated on Line 4c.)_

  a) depth from soil surface to bottom of soil layer (mm) - real (solthk)

  b) Bulk density for layer (gm/cc)

  c) Hydraulic conductivity for layer (mm/h)

  d) Anisotropy ratio for layer (mm/h / \[mm/h\])

  e) Field capacity for layer (mm/mm)

  f) Wilting point for layer (mm/mm)

  g) percentage of sand in the layer (%) - real (sand)

  h) percentage of clay in the layer (%) - real (clay)

  i) percentage of organic matter (volume) in the layer (%) - real (orgmat)

  j) cation exchange capacity in the layer (meq/100 g of soil) - real (cec)

Line 5: _Version 9002 (disturbed land soils; repeated for each OFE before the layer data)_

  a) saturated hydraulic conductivity adjustment flag - integer (ksatadj)
     - 0 – do not apply hydrophobicity or burn adjustments
     - 1 – apply the internal adjustment logic
  b) disturbed land-use classification - character (luse)
  c) simplified soil texture class (clay loam, loam, sand loam, silt loam) - character (stext)
  d) lower bound on effective hydraulic conductivity (mm/h) - real (ksatfac)
  e) exponential recovery coefficient for hydraulic conductivity (1/day) - real (ksatrec)

Line 5: _Version 9002 layer data (repeated for the number of soil layers indicated on Line 4c.)_

  a) depth from soil surface to bottom of soil layer (mm) - real (solthk)

  b) Bulk density for layer (g/cm³) - real (bd)

  c) Hydraulic conductivity for layer (mm/h) - real (ksat)

  d) Anisotropy ratio for layer (horizontal ksat / vertical ksat) - real (anisotropy)

  e) Field capacity for layer (m³/m³) - real (fc)

  f) Wilting point for layer (m³/m³) - real (wp)

  g) percentage of sand in the layer (%) - real (sand)

  h) percentage of clay in the layer (%) - real (clay)

  i) percentage of organic matter (volume) in the layer (%) - real (orgmat)

  j) cation exchange capacity in the layer (meq/100 g of soil) - real (cec)

  k) percentage of rock fragments by volume in the layer (%) - real (rfg)

  l) residual volumetric water content (m³/m³) derived from Rosetta - real (theta_r)

  m) saturated volumetric water content (m³/m³) derived from Rosetta - real (theta_s)

  n) van Genuchten alpha parameter (1/cm) - real (alpha)

  o) van Genuchten pore-size distribution exponent (dimensionless) - real (npar)

  p) saturated hydraulic conductivity predicted by Rosetta (cm/day) - real (ks)

  q) wilting point water content predicted by Rosetta (m³/m³) - real (wp)

  r) field capacity water content predicted by Rosetta (m³/m³) - real (fc)

  _Note: The Rosetta-derived `wp` and `fc` values are appended even though measured `wp` and `fc` appear earlier in the record. WEPP loads both sets so that hydraulic property recalculations can use the pedotransfer estimates when required._

Line 5: _Version 9003 (disturbed land soils with burn severity; repeated for each OFE before the layer data)_

  a) saturated hydraulic conductivity adjustment flag - integer (ksatadj)

  b) disturbed land-use classification (e.g., "forest high sev") - character (luse)

  c) burn severity code - integer (burn_code)
     - 100 agriculture, 200 shrub, 300 forest, 306 young forest, 400 grass
     - add 1 for low, 2 for moderate, 3 for high burn severity

  d) simplified soil texture class - character (stext)

  e) lower limit on effective hydraulic conductivity (mm/h; -9999 disables the cap) - real (lkeff)

Line 5: _Version 9003 layer data (repeated for the number of soil layers indicated on Line 4c.)_

  Identical to Version 9002 layer data, including the appended van Genuchten parameters (`theta_r` through the Rosetta-derived `fc`).

Line 5: _Version 9005 (revegetation soils; repeated for each OFE before the layer data)_

  a) saturated hydraulic conductivity adjustment flag - integer (ksatadj)

  b) disturbed land-use classification - character (luse)

  c) burn severity code - integer (burn_code)

  d) simplified soil texture class - character (stext)

  e) simplified texture enumeration (clay loam=1, loam=2, sand loam=3, silt loam=4) - integer (texid_enum)

  f) understory saturated hydraulic conductivity used for revegetation (mm/h) - real (uksat)

  g) lower limit on effective hydraulic conductivity (mm/h; -9999 disables the cap) - real (lkeff)

Line 5: _Version 9005 layer data (repeated for the number of soil layers indicated on Line 4c.)_

  Identical to Version 9002 layer data, including the appended van Genuchten parameters (`theta_r` through the Rosetta-derived `fc`).

  _Additional guidance on disturbed land parameters such as `ksatadj`, `lkeff`, and `uksat` is available in `wepppy/weppcloud/routes/usersum/weppcloud/disturbed-land-soil-lookup.md`._

Line 6: Applies to versions 2006.2, 7777, 7778, 9002, 9003, 9005 format soil files

  a) Indicates if a restricting layer is present (0=no restricting layer, 1=restricting
layer present) (slflag)

  b) Thickness of restricting layer (mm) (ui_bdrkth)

  c) Hydraulic conductivity of restricting layer (mm/h) (kslast)
