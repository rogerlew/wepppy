## **Soil Input File**

Information on soil properties to a maximum depth of 1.8 meters are input to the WEPP model through the soil input file1. The user may input information on up to 8 different soil layers2. WEPP internally creates a new set of soil layers based on the original set parameter values3. If the entire 1.8 meters is parameterized, the new soil layers represent depths of 0-100 mm, 100-200 mm, 200-400 mm, 400-600 mm, 600-800 mm, 800-1000 mm, 1000-1200 mm, 1200-1400 mm, 1400-1600 mm, 1600-1800 mm4.

As with the slope file, soil parameters must be input for each and every Overland Flow Element (OFE) on the hillslope profile and for each channel in a watershed, even if the soil on all OFEs is the same5.

Accurate estimation of soil physical and hydrological parameters is essential when operating the WEPP erosion prediction model6. Table 3 lists the input parameters in the soil input file, and the discussion following the table is meant to assist the users in determining input parameter values7. There are several versions of the soil file that can be used as input for WEPP8. The differences in format are specified by the version number in line 1 which indicates how the remainder of the file is interpreted by WEPP9.

Table 3\. Soil input file description. 10

| Line | Description |
| :---- | :---- |
| **Line 1:** | **version control number \- real (datver)** 97.5 \- Base set of soil properties 2006.2 \- Adds a separate restricting layer below profile 7777 \- Adds additional layer parameters 7778 \- Adds additional layer parameters and anisotropy ratio |
| **Line 2:** | a) **User comment line** \- character\*80, (solcom) |
| **Line 3:** | a) **number of overland flow elements (OFE's) or channels** integer (ntemp) b) **flag to use internal hydraulic conductivity adjustments** \- integer (ksflag)      0 \- do not use adjustments (conductivity will be held constant)      1 \- use internal adjustments |
|  | *Lines 4 & 5 are repeated for the number of OFE's or channels on Line 3a.* |
| **Line 4:** | a) **soil name for current OFE or channel** \- character (slid) b) **soil texture for current OFE or channel** \- character (texid) c) **number of soil layers for current OFE or channel** \- integer (nsl) d) **albedo of the bare dry surface soil on the current OFE or channel** \- real (salb) e) **initial saturation level of the soil profile porosity** (m/m) \- real (sat) f) **baseline interrill erodibility parameter** (kg∗s/m4) \- real (ki) g) **baseline rill erodibility parameter** (s/m) \- real (kr) h) **baseline critical shear parameter** (N/m2) \- real (shcrit) i) **effective hydraulic conductivity of surface soil** (mm/h) \- real (avke) |
| **Line 5:** | **Version 97.5 and 2006.2** *(repeated for the number of soil layers indicated on Line 4c.)* a) **depth from soil surface to bottom of soil layer** (mm) \- real (solthk) b) **percentage of sand in the layer** (%) \- real (sand) c) **percentage of clay in the layer** (%) \- real (clay) d) **percentage of organic matter (volume) in the layer** (%) \- real (orgmat) e) **cation exchange capacity in the layer** (meq/100 g of soil) \- real (cec) f) **percentage of rock fragments by volume in the layer** (%) \- real (rfg) |
| **Line 5:** | **Version 7777** *(repeated for the number of soil layers indicated on Line 4c.)* a) **depth from soil surface to bottom of soil layer** (mm) \- real (solthk) b) **Bulk density for layer** (gm/cc) c) **Hydraulic conductivity for layer** (mm/h) d) **Field capacity for layer** (mm/mm) e) **Wilting point for layer** (mm/mm) f) **percentage of sand in the layer** (%) \- real (sand) g) **percentage of clay in the layer** (%) \- real (clay) h) **percentage of organic matter (volume) in the layer** (%) \- real (orgmat) i) **cation exchange capacity in the layer** (meq/100 g of soil) \- real (cec) j) **percentage of rock fragments by volume in the layer** (%) \- real (rfg) |
| **Line 5:** | **Version 7778** *(repeated for the number of soil layers indicated on Line 4c.)* a) **depth from soil surface to bottom of soil layer** (mm) \- real (solthk) b) **Bulk density for layer** (gm/cc) c) **Hydraulic conductivity for layer** (mm/h) d) **Anisotropy ratio for layer** (mm/h/\[mm/h\]) e) **Field capacity for layer** (mm/mm) f) **Wilting point for layer** (mm/mm) g) **percentage of sand in the layer** (%) \- real (sand) h) **percentage of clay in the layer** (%) \- real (clay) i) **percentage of organic matter (volume) in the layer** (%) \- real (orgmat) j) **cation exchange capacity in the layer** ((meq/100 g of soil) \- real (cec) k) **percentage of rock fragments by volume in the layer** (%) \- real (rfg) |
| **Line 6:** | *Applies to versions 2006.2, 7777 and 7778 format soil files* a) **Indicates if a restricting layer is present** (0=no restricting layer, 1= restricting layer present) b) **Thickness of restricting layer** (mm) c) **Hydraulic conductivity of restricting layer** (mm/h) |

---

### **Soil Input Parameter Estimation Procedures**

The key parameter for WEPP in terms of infiltration is the Green and Ampt effective conductivity parameter (  
Ke​)11. This parameter is related to the saturated conductivity of the soil, but it is important to note that it is not the same as or equal in value to the saturated conductivity of the soil12. The second soil-related parameter in the Green and Ampt model is the wetting front matric potential term13. That term is calculated internal to WEPP as a function of soil type, soil moisture content, and soil bulk density: it is not an input variable14.

The effective conductivity (avke) value for the soil may be input on Line 4i of the soil input file, immediately after the inputs for soil erodibility15. If the user does not know the effective conductivity of the soil, he/she may insert a zero (0.0) and the WEPP model will calculate a value based on the equations presented here for the time-variable case (see Equation 1 below)16.

The model will run in 2 modes by either: A) using a "baseline" effective conductivity (  
Kb​) which the model automatically adjusts within the continuous simulation calculations as a function of soil management and plant characteristics, or B) using a constant input value of Ke​17. The second number in line 3 of the soil file contains a flag (0 or 1) which the model uses to distinguish between these two modes18. A value of 1 indicates that the model is expecting the user to input a

Kb​ value which is a function of soil only, and which will be internally adjusted to account for management practices19. A value of 0 indicates the model is expecting the user to input a value of

Ke​ which will not be internally adjusted and must therefore be representative of both the soil and the management practice being modeled20. It is essential that the flag (0 or 1\) in line 3 of the soil file be set consistently with the input value of effective conductivity for the upper soil layer21.

#### **"Baseline" Effective Conductivity Estimation Procedures for Croplands**

Values for "baseline" effective conductivity (  
Kb​) may be estimated using the following equations22:

For soils with ≤40% clay content:

Kb​=−0.265+0.0086×SAND1.8+11.46×CEC−0.75\[1\]  
23232323

For soils with \>40% clay content:

Kb​=0.0066exp(2.44/CLAY)\[2\]  
24242424

where SAND and CLAY are the percent of sand and clay, and CEC  
(meq/100g) is the cation exchange capacity of the soil25. In order for \[1\] to work properly, the input value for cation exchange capacity should always be greater than

1 meq/100g26. These equations were derived based on model optimization runs to measured and curve number (fallow condition) runoff amounts27. Forty three soil files were used to develop the relationships (Table 4\)28.  
