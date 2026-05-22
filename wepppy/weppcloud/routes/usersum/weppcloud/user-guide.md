# WEPPcloud User Guide

## Introduction

### What is WEPPcloud?

WEPPcloud is an open-source, online platform that predicts how water and soil move through a watershed — how much soil erodes, where sediment goes, and how runoff responds to fires, land management, and climate. It runs entirely in a web browser with no software to install.

**From an extent on a map to model-based estimates in minutes.** You zoom to a location, draw a watershed boundary, and WEPPcloud does the rest: it acquires elevation data, delineates the channel network and hillslopes, pulls soils and land cover from federal databases, retrieves climate records, and runs the USDA's peer-reviewed WEPP erosion model — a process that traditionally required weeks of GIS preparation and manual model setup.

**Compare management options with evidence.** WEPPcloud's scenario engine lets you model alternative treatments — mulching, thinning, prescribed fire, revegetation — and compare their effects side by side against a control. The results estimate where and by how much each treatment reduces erosion, supporting defensible comparisons for management recommendations and BAER reporting.

**Uses available public datasets, selected automatically.** WEPPcloud integrates soils from SSURGO and STATSGO, land cover from NLCD and the Rangeland Analysis Platform, and climate from five independent sources including historical station records, gridded observations (Daymet, GridMET, PRISM), and stochastic weather generation for extreme-event analysis. You choose your watershed; WEPPcloud assembles relevant available data for your run.

**More than erosion.** Beyond standard WEPP hydrology, the platform includes modules for post-fire ash transport and water quality, debris flow hazard, road and stream-crossing erosion, rangeland condition assessment, phosphorus loading, and cost-effective treatment optimization — each available as a modeling option within the same project.

**Interactive maps and exportable results.** Outputs are displayed on interactive 3D maps where you can visualize erosion, runoff, soils, and land cover by subcatchment, filter by year, and compare scenarios spatially. Results are also exportable as GIS datasets (Shapefile, GeoJSON, GeoParquet), HEC-DSS files for integration with Army Corps and FEMA workflows, and tabular summaries.

### Use Cases

- **Academic research.** WEPPcloud is documented in peer-reviewed literature, including the two-part 2022 *Journal of Hydrology* WEPPcloud papers.
- **Post-fire response modeling (BAER teams).** WEPPcloud supports post-fire workflows (including burn-severity-driven scenarios), and the broader WEPP model suite is used by BAER teams for rapid post-fire erosion and runoff risk assessment.
- **Pre-fire land-use management.** WEPPcloud is used to compare management scenarios such as thinning and prescribed fire before wildfire, then evaluate post-fire outcomes.
- **Utility watershed management.** WEPPcloud includes municipal watershed interfaces (for example, Seattle and Portland municipal watershed resources) used to evaluate watershed conditions, fire scenarios, and treatment alternatives.
- **Agriculture.** The WEPPcloud framework is applicable to cropland conditions (alongside forest and rangeland), supporting runoff and erosion analysis for agricultural land-management planning.

### Models Available on WEPPcloud

WEPPcloud supports a mix of core models, optional modules, interface-specific workflows, and API-backed integrations:

- **[WEPP](models/wepp/ENDUSER.md)** — the core hydrology and erosion model used to simulate runoff, hillslope erosion, channel processes, and sediment delivery.
- **[Ash Transport (WATAR)](models/ash-transport/ENDUSER.md)** — post-fire ash and contaminant transport modeling for watershed-scale ash and water-quality assessment after wildfire.
- **[Debris Flow](models/debris-flow/ENDUSER.md)** — post-fire debris-flow probability and volume estimation using watershed properties, burn severity, soils, slope, and precipitation inputs.
- **[Gridded RUSLE](models/gridded-rusle/ENDUSER.md)** — gridded RUSLE factor and annual detachment mapping for spatial erosion-potential analysis.
- **[Culvert Modeling (API)](models/culvert-modeling/ENDUSER.md)** — an API-backed culvert and hydroenforcement workflow used to condition terrain and drainage paths around engineered crossings.
- **[Roads](models/roads/ENDUSER.md)** — road and stream-crossing erosion analysis integrated with the watershed workflow.
- **[Revegetation](models/revegetation/ENDUSER.md)** — a WEPPcloud interface and scenario workflow for modeling post-fire vegetation recovery and cover-transform effects before running WEPP.
- **[RHEM](models/rhem/ENDUSER.md)** — the Rangeland Hydrology and Erosion Model interface for rangeland runoff and erosion analysis.
- **[Agricultural Fields (AgFields API)](models/agricultural-fields/ENDUSER.md)** — an API-backed workflow for modeling mapped crop fields and generating field- or sub-field-scale WEPP results.
- **[WEPP-SWAT+](models/wepp-swat/ENDUSER.md)** — a combined workflow that extends WEPP results with optional SWAT+ channel-routing steps.
- **[WEPP DSS Export for HEC-RAS](models/hec-dss-export/ENDUSER.md)** — export of WEPP channel and outlet time series to HEC-DSS for downstream HEC workflows such as HEC-RAS.

### Who develops WEPPcloud?

WEPPcloud was developed primarily for forestry applications as a joint effort between the University of Idaho and the USDA Forest Service Rocky Mountain Research Station. Additional contributions come from USDA Agricultural Research Service (ARS), Swansea University, and Michigan Technological University. The European interface was funded in part by the European Union's Horizon 2020 research and innovation program (grant agreement No. 10100389).

### Open Source and User Access

WEPPcloud is open-source and built around transparency. Users have full access to their runs, can browse project files, and can download their work at any time. The platform is free to use, with no subscription fees, usage limits, or premium tiers, and it is publicly funded through federal research grants and university support.

---

## Help and Feedback

If you need help using WEPPcloud, have questions about model setup, or want to report a problem, contact the development and research team:

| Name | Role | Affiliation | Email | Expertise |
|------|------|-------------|-------|-----------|
| Roger Lew | WEPPcloud DevOps Architect, Associate Research Professor | University of Idaho | rogerlew@uidaho.edu | WEPPcloud, WEPP inputs and outputs, data pipelines, analytics |
| Mariana Dobre | Assistant Professor | University of Idaho | mdobre@uidaho.edu | Hydrology, soil science, calibration, forests |
| Anurag Srivastava | Research Scientist | University of Idaho | srivanu@uidaho.edu | WEPP model, hydrology, soil erosion, climate datasets |
| Pete Robichaud | Research Engineer | USDA Forest Service, Rocky Mountain Research Station | peter.robichaud@usda.gov | Forest response, WEPP, post-fire erosion, ash transport |

For software bugs and feature requests, submit an issue on the WEPPcloud GitHub repository.

---

## Privacy Statement

WEPPcloud collects only the information necessary to operate the platform and support your work.

**Account data.** When you register or sign in via OAuth, WEPPcloud stores your name and email address. If you use OAuth (Google, GitHub, or ORCID), WEPPcloud receives only the profile information needed to identify your account. Your OAuth provider password is never transmitted to or stored by WEPPcloud.

**Run data.** Watershed delineations, model inputs, simulation outputs, and uploaded files (such as burn severity maps) are stored on WEPPcloud servers for as long as the project exists. Run data includes geographic coordinates of your watershed area.

**Project TTL (Time To Live).** WEPPcloud uses a project TTL (Time To Live), which is an inactivity timer for project data. By default, each project has a rolling 90-day TTL. If a project is not accessed before the timer expires, it is queued for deletion.

**How TTL resets.** When a project is accessed, WEPPcloud refreshes the project's last-access timestamp and extends the expiration window by another 90 days.

**Disabling TTL deletion.** Logged-in users with `PowerUser`, `Admin`, or `Root` permissions can disable TTL deletion for a project from the run header: **More -> Disable TTL Deletion**. If TTL deletion is turned back on, the project starts a fresh 90-day TTL window.

**Usage data.** WEPPcloud records basic access information such as login timestamps and run access counts for operational monitoring. This data is used to maintain service reliability and track platform usage metrics displayed on the landing page.

**What WEPPcloud does not do:**
- Sell or share your personal information with third parties
- Use your data for advertising
- Require more personal information than what is needed to operate your account

**Data retention.** Account data are retained until you delete your account. Run data are retained while projects remain active, unless you delete them manually; inactive projects may be deleted under the project TTL policy above. If you have questions about your data, contact rogerlew@uidaho.edu.

---

## Legal Disclaimer

WEPPcloud provides simulation outputs based on the WEPP model and associated datasets. These outputs are estimates derived from mathematical models, publicly available geospatial data, and climate records. Like all models, they are simplifications of complex natural systems and are subject to uncertainty. WEPPcloud simulation outputs are not a substitute for professional judgment or site-specific field assessment.

**All models are approximations.** Simulation results should be interpreted by qualified professionals in the context of local site conditions, field observations, and professional judgment. WEPPcloud outputs are intended to support — not replace — expert analysis and decision-making.

**No warranty.** This software and its outputs are provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. The developers and contributing institutions make no warranty regarding the accuracy, completeness, or suitability of simulation results for any particular use.

**Limitation of liability.** In no event shall the University of Idaho, USDA Forest Service, or any contributing institution, developer, or contributor be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, loss of data, property damage, environmental harm, procurement of substitute goods or services, or financial loss) arising from the use of or reliance on WEPPcloud or its outputs, however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise), even if advised of the possibility of such damage.

**Assumption of risk.** By using WEPPcloud, you acknowledge that simulation outputs are approximations subject to uncertainty and agree that you bear sole responsibility for any decisions, actions, or consequences arising from their use. You agree to independently verify any WEPPcloud outputs before relying on them for management decisions, regulatory compliance, or any purpose where errors could result in harm.

**Data sources.** WEPPcloud relies on publicly available datasets (SSURGO, NLCD, ESDAC, ASRIS, CLIGEN, RAP, E-OBS, and others) that are maintained by their respective agencies. Data quality, resolution, and currency vary by source and region. WEPPcloud does not independently verify the accuracy of these upstream datasets.

**Funding acknowledgments.** WEPPcloud development has been supported by the University of Idaho, USDA Forest Service Rocky Mountain Research Station, USDA Agricultural Research Service, Swansea University, Michigan Technological University, and the European Union's Horizon 2020 research and innovation program (grant agreement No. 10100389).
