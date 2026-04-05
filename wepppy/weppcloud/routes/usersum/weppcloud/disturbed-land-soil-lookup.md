# Disturbed Land Soil Lookup Table (PowerUser Panel → Modify Disturbed Parameters)

The disturbed land soil table in WEPPcloud contains parameters that define soil properties for various land use categories and soil textures. These parameters are essential for modeling erosion and hydrology in disturbed lands using the WEPP (Water Erosion Prediction Project) model. The table includes data for combinations of land use (e.g., agriculture crops, forest, bare) and soil texture (clay loam, loam, sand loam, silt loam).

Each project has its own disturbed land-soil-lookup table that can be modified through the PowerUser Panel.

This page is the parameter reference. For the recommended calibration order, what to calibrate first, and how to think about undisturbed versus post-fire tuning, see [WEPPcloud Calibration Guidance](./weppcloud-calibration-guidance.md).

### Table of Parameters

| Parameter     | Description                                                              | Units        |
|---------------|--------------------------------------------------------------------------|--------------|
| luse          | Land use category (disturbed class from the land use map)                | -            |
| stext         | Soil texture (clay loam, loam, sand loam, silt loam)                     | -            |
| ki            | Interrill erodibility                                                    | kg·s/m⁴      |
| kr            | Rill erodibility                                                         | s/m          |
| shcrit        | Critical shear stress (τc)                                               | N/m² or Pa   |
| avke          | Effective hydraulic conductivity                                         | mm/h         |
| ksflag        | Flag to use internal hydraulic conductivity adjustments (0: no, 1: yes)  | {0,1}        |
| ksatadj       | Adjustment factor for saturated hydraulic conductivity                   | -            |
| ksatfac       | ignore - will be removed                                                 | -            |
| ksatrec       | ignore - will be removed                                                 | -            |
| pmet_kcb      | Basal crop coefficient (Kcb)                                             | -            |
| pmet_rawp     | Parameter for readily available water                                    | -            |
| rdmax         | Maximum root depth                                                       | m            |
| xmxlai        | Maximum leaf area index                                                  | frac         |
| keffflag      | Flag for lower limit of effective conductivity (lkeff; 0: no, 1: yes)    | {0,1}        |
| lkeff         | Lower limit of effective conductivity (-9999 indicates no adjustment)    | mm/h         |

## Additional Notes and Other Parameters of Interest

### Effective Hydraulic Conductivity (avke)

Determined from field data. Do not change unless you have a good reason.

- **Units**: mm/h
- **Guidelines**:
  - Treat this as a field-based parameter, not a general-purpose calibration knob.
  - In some west-of-Cascades settings, the disturbed-versus-undisturbed difference in this parameter may matter less than it does in drier inland settings.

### Interrill Erodibility (ki)

Interrill areas are the sheet flow zones between small channels (rills) on a hillslope. Interrill erodibility measures the soil's susceptibility to detachment by raindrop impact and shallow sheet flow. It is influenced by:

- Soil texture
- Surface cover (e.g., vegetation, mulch)
- Soil structure and cohesion

**Units**: kg·s/m⁴  
**Note**: Do not change.

### Rill Erodibility (kr)

Rills are small channels formed by concentrated flow on hillslopes. Rill erodibility is the soil’s susceptibility to detachment by concentrated flow (not raindrop impact). Rill erosion is generally more intense on steeper and/or longer slopes and can cause greater sediment transport than interrill erosion.

**Units**: s/m  
**Note**: Do not change in most projects.

Regional caution:

- Emerging West Cascades guidance suggests that lower `kr` values may fit some settings better.
- Treat that as expert-guided regional adjustment, not as a general default.

### Critical Shear Stress (τc)

This is the minimum hydraulic shear stress required to initiate detachment of soil particles in rills. Below this threshold, the flow is not energetic enough to detach soil. It acts as a resistance parameter in rill erosion models.

**Units**: N/m² or Pa  
**Note**: Do not change.

### Basal Crop Coefficient (pmet_kcb)

The Kcb parameter for the FAO Penman-Monteith equation approximates net evapotranspiration from meteorological data as a replacement for direct measurement of evapotranspiration.

**Units**: None  
**Guidelines**:
- For forests, use default: 0.95 (well-watered conditions).
- For undisturbed calibration, values near `1.2` can increase ET and reduce annual water yield, while values near `0.65` can reduce ET and increase annual water yield.
- No need to modify for disturbed conditions, as the reduction in ET is accounted for by a reduction in LAI within the model.

For more information, see: [Crop evapotranspiration - Guidelines for computing crop water requirements - FAO Irrigation and drainage paper 56, Chapter 7 - ETc - Dual crop coefficient (Kc = Kcb + Ke)](https://www.fao.org/4/x0490e/x0490e0c.htm#chapter%207%20%20%20etc%20%20%20dual%20crop%20coefficient%20(kc%20=%20kcb%20+%20ke))

### Rain-Snow Temperature Threshold

Found under WEPP Advanced Options - Snow.

**Units**: °C  
**Range**: -3 to 1  
**Guidelines**:
- Use `0` for `CLIGEN`.
- Use `0` for `Daymet`.
- Use `-2` for `GridMET`.

### Underlying Bedrock Conductivity (ksat for restrictive layer - kslast)

Found under WEPP Advanced Options - Bedrock

**Units**: mm/h  
**Default**: Based on SSURGO values (ksat of the last horizon / 100, or other rules).  
**Range**: 0.001–0.1  
**Guidelines**:
- `0.001` strongly restricts deep seepage and tends to keep more water in lateral flow and runoff pathways.
- `0.1` allows more drainage to the baseflow reservoir and can reduce quick runoff response.
- Use this as a structural watershed-hydrology parameter, not as a first-response substitute for poor climate or watershed setup.

### Baseflow Coefficient

Found under WEPP Advanced Options - Baseflow Processing.

**Units**: per day  
**Range**: 0.01–0.10  
**Guidelines**:
- `0.01` gives a longer recession, on the order of about `100` days.
- `0.04` gives a shorter recession, on the order of about `25` days.
- The historical WEPPcloud limit of `0.04` came from earlier disturbed-land guidance, not a hard WEPP model limit.
- Some small watersheds, especially in the `40-100 ha` range, may require higher coefficients such as `0.05-0.07` per day to match observed recession behavior.
- When observed streamflow data are available, estimate this from the slope of the recession limb rather than tuning by trial and error alone.
- Start with the project default and only increase the coefficient when the simulated baseflow recession is too slow relative to observations or other defensible calibration targets.

### Channel Critical Shear Stress (τc)

Found under WEPP Advanced Options - Channel Parameters

**Units**: N/m² or Pa
**Range**: 0.05 (fine silt) and 170 coarse cobble
**Guidelines**:
- This is the minimum shear stress required to initiate the movement of sediment particles on the bed of a channel (such as a river, stream, or canal). 
- In simple terms, it's the threshold force per unit area that water flow must exert on the channel bed to start erosion or sediment transport.
- For practical calibration, channel critical shear is often started from the channel bed `D50` particle size in mm.
- Higher values generally mean less channel erosion; lower values generally mean more channel erosion.
- Example regional guidance:
  - `70-170` for coarse-bed West Cascades style channels.
  - about `20-50` for more erosion-prone Inland Pacific Northwest settings.
  - about `35-40` for North Idaho examples such as Mika Creek.
  - about `70` near Eugene, Oregon.
  - about `83` for some Oregon/Washington municipal watershed settings.

### ksatadj

Specifies hydrophobicity adjustment

**Units**: None
**Guidelines**:
- Currently, we set the hydrophobicity for high severity burn only. But it could be changed as desired. Note that in the model the hydrophobicity is by burn severity applied to all four soil textures of high severity.
- The `ksatadj` value of "1" specifies hydrophobic soils. Users can then change the lower limit of hydraulic conductivity (`lkeff` parameter value), which would restrict infiltration and allow more surface runoff.

## Related Docs

- [WEPPcloud Calibration Guidance](./weppcloud-calibration-guidance.md)
- [WEPP Advanced Options](./wepp-advanced-options.md)
- [Observed Model Fitting](./observed-model-fitting.md)
