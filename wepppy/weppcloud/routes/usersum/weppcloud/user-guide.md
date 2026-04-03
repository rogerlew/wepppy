# WEPPcloud User Guide

## Introduction

### What is WEPPcloud?

WEPPcloud is a free, online platform that predicts how water and soil move through a watershed — how much soil erodes, where sediment goes, and how runoff responds to fires, land management, and climate. It runs entirely in a web browser with no software to install.

**From a point on a map to physics-based predictions in minutes.** You zoom to a location, draw a watershed boundary, and WEPPcloud does the rest: it acquires elevation data, delineates the channel network and hillslopes, pulls soils and land cover from federal databases, retrieves climate records, and runs the USDA's peer-reviewed WEPP erosion model — a process that traditionally required weeks of GIS preparation and manual model setup.

**Compare management options with evidence.** WEPPcloud's scenario engine lets you model alternative treatments — mulching, thinning, prescribed fire, revegetation — and compare their effects side by side against a control. The results show exactly where and by how much each treatment reduces erosion, giving you defensible evidence for management recommendations and BAER reports.

**The best available data, selected automatically.** WEPPcloud integrates soils from SSURGO and STATSGO, land cover from NLCD and the Rangeland Analysis Platform, and climate from five independent sources including historical station records, gridded observations (Daymet, GridMET, PRISM), and stochastic weather generation for extreme-event analysis. You choose your watershed; WEPPcloud finds the right data.

**More than erosion.** Beyond standard WEPP hydrology, the platform includes modules for post-fire ash transport and water quality, debris flow hazard, road and stream-crossing erosion, rangeland condition assessment, phosphorus loading, and cost-effective treatment optimization — each available as a modeling option within the same project.

**Interactive maps and exportable results.** Outputs are displayed on interactive 3D maps where you can visualize erosion, runoff, soils, and land cover by subcatchment, filter by year, and compare scenarios spatially. Results are also exportable as GIS datasets (Shapefile, GeoJSON, GeoParquet), HEC-DSS files for integration with Army Corps and FEMA workflows, and tabular summaries.

### Use Cases

- **Academic research.** WEPPcloud is documented in peer-reviewed literature, including the two-part 2022 *Journal of Hydrology* WEPPcloud papers.
- **Post-fire response modeling (BAER teams).** WEPPcloud supports post-fire workflows (including burn-severity-driven scenarios), and the broader WEPP model suite is used by BAER teams for rapid post-fire erosion and runoff risk assessment.
- **Pre-fire land-use management.** WEPPcloud is used to compare management scenarios such as thinning and prescribed fire before wildfire, then evaluate post-fire outcomes.
- **Utility watershed management.** WEPPcloud includes municipal watershed interfaces (for example, Seattle and Portland municipal watershed resources) used to evaluate watershed conditions, fire scenarios, and treatment alternatives.
- **Agriculture.** The WEPPcloud framework is applicable to cropland conditions (alongside forest and rangeland), supporting runoff and erosion analysis for agricultural land-management planning.

### Who develops WEPPcloud?

WEPPcloud was developed primarily for forestry applications as a joint effort between the University of Idaho and the USDA Forest Service Rocky Mountain Research Station. Additional contributions come from USDA Agricultural Research Service (ARS), Swansea University, and Michigan Technological University. The European interface was funded in part by the European Union's Horizon 2020 research and innovation program (grant agreement No. 10100389).

### How much does it cost?

WEPPcloud is free to use. There are no subscription fees, usage limits, or premium tiers. The platform is publicly funded through federal research grants and university support.

---

## User Accounts

You can use WEPPcloud with or without an account, but creating one is recommended.

### Anonymous Access

You can start a project without logging in. Anonymous runs require completing a CAPTCHA before launching an interface. Anonymous runs are not tied to a user profile, which means you cannot manage them from a central dashboard or generate API tokens for programmatic access.

### Benefits of Having an Account

- **Private projects by default** — anonymous projects are publicly visible to anyone with the link, while projects owned by a registered account are private. You can share individual projects with a group or make them public when you choose to.
- Bypass CAPTCHAs when launching interfaces
- View and manage all your runs from a central dashboard
- Generate API tokens for programmatic access (Python, R)
- Access role-based features when granted by administrators

### Creating an Account

You can register for a WEPPcloud account using an email address and password. Registration requires your first and last name and email confirmation.

### OAuth Sign-In (Recommended)

The easiest way to use WEPPcloud is to sign in through an existing account with one of the supported providers:

- **Google** — sign in with your Google account
- **GitHub** — sign in with your GitHub account
- **ORCID** — sign in with your ORCID researcher identifier

When you use OAuth, you authenticate directly with the provider (Google, GitHub, or ORCID). WEPPcloud receives only your name and email address to create or link your account. Your password is never shared with WEPPcloud. You can connect multiple OAuth providers to the same WEPPcloud account and disconnect them at any time from your profile page.

---

## Interfaces

### What is an Interface?

An interface is a preconfigured bundle of data sources, models, and settings that defines how a WEPPcloud project is set up and run. Each interface targets a specific geographic region and use case, determining which soils databases, land cover datasets, climate sources, and model options are available. When you start a new project, you choose an interface, and WEPPcloud configures everything accordingly.

All interfaces let you choose between **SI** (metric) and **English** (imperial) units when launching a project.

### Active Interfaces

#### WEPPcloud-(Un)Disturbed (United States)

The primary interface for the continental United States, with experimental support for Hawaii and Alaska. It uses SSURGO-derived soils and NLCD land cover to parameterize runs. Users can optionally upload a burn severity map to predict post-fire erosion, or skip it to analyze unburned conditions. Fire and treatment scenarios procedurally generate soils and management files from the disturbed database using soil texture and land use class. This interface also integrates the Wildfire Ash Transport And Risk estimation tool (WATAR) for post-fire water quality assessment.

**Available configurations:** CONUS, Hawaii (experimental), Alaska (experimental)

#### WEPPcloud-(Un)Disturbed-WBT

The successor to the original TOPAZ-based delineation workflow. It uses WEPPcloud-WBT (a WhiteboxTools fork) for watershed preprocessing and hillslope delineation. In addition to improved performance, the WBT backend produces GeoTIFF raster products and supports advanced workflows such as Omni scenario contrasts and stream-order pruning.

**Available configurations:** CONUS

#### WEPPcloud-Revegetation

Supports burn severity uploads and leverages historical vegetative cover data from the Rangeland Analysis Platform (RAP) to model post-fire hydrology and erosion. Users can simulate stochastic wildfires, recovery trajectories, and cover transformations across perennial, annual, shrub, and tree components following a fire event.

**Available configurations:** CONUS, Multiple OFE (CONUS), 10m Multiple OFE (CONUS), Alaska (experimental)

#### WEPPcloud-EU (Europe)

Designed for European watersheds. Uses ESDAC land use classifications, EU-SoilHydroGrids for soil properties, and E-OBS climate data to match U.S. climate stations by monthly precipitation and temperature patterns. The PeP (Post-fire Erosion and Prevention) extension adds post-fire erosion modeling and WATAR ash transport for European landscapes.

#### WEPPcloud-AU (Australia)

Experimental interface for Australian watersheds. Assigns land management from the Land Use of Australia 2010-11 dataset and constructs soils from ASRIS data. Climate stations are selected using AGDC monthly precipitation and temperature patterns.

#### WEPPcloud-RHEM

Runs the Rangeland Hydrology and Erosion Model (RHEM) across the United States. Where available, foliar and ground covers are estimated from NLCD Shrubland 2016 data, and SSURGO/STATSGO identifies soil textures.

### Site-Specific Resources

Some interfaces are configured for specific geographic areas with region-specific datasets:

- **Lake Tahoe** — incorporates region-specific soil, phosphorus, and estimated soil burn severity datasets
- **Hazard SEES FireEarth** — data portals for the Hazard SEES FireEarth Project, including Seattle and Portland municipal watersheds

### Legacy Interfaces

The original **WEPPcloud** and **WEPPcloud-PEP** interfaces are still available but have been deprecated. For new projects, use the (Un)Disturbed interface instead. The legacy WEPPcloud-PEP interface is limited to four general soils based on texture, whereas (Un)Disturbed incorporates spatial soil variability from SSURGO/STATSGO databases.

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

**Usage data.** WEPPcloud records basic access information such as login timestamps and run access counts for operational monitoring. This data is used to maintain service reliability and track platform usage metrics displayed on the landing page.

**What WEPPcloud does not do:**
- Sell or share your personal information with third parties
- Use your data for advertising
- Require more personal information than what is needed to operate your account

**Data retention.** Account and run data are retained until you delete your account or projects. If you have questions about your data, contact rogerlew@uidaho.edu.

---

## Legal Disclaimer

WEPPcloud provides simulation outputs based on the WEPP model and associated datasets. These outputs are estimates derived from mathematical models, publicly available geospatial data, and climate records. Like all models, they are simplifications of complex natural systems and are subject to uncertainty. WEPPcloud simulation outputs are not a substitute for professional judgment or site-specific field assessment.

**All models are approximations.** Simulation results should be interpreted by qualified professionals in the context of local site conditions, field observations, and professional judgment. WEPPcloud outputs are intended to support — not replace — expert analysis and decision-making.

**No warranty.** THIS SOFTWARE AND ITS OUTPUTS ARE PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. The developers and contributing institutions make no warranty regarding the accuracy, completeness, or suitability of simulation results for any particular use.

**Limitation of liability.** IN NO EVENT SHALL THE UNIVERSITY OF IDAHO, USDA FOREST SERVICE, OR ANY CONTRIBUTING INSTITUTION, DEVELOPER, OR CONTRIBUTOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, LOSS OF DATA, PROPERTY DAMAGE, ENVIRONMENTAL HARM, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES, OR FINANCIAL LOSS) ARISING FROM THE USE OF OR RELIANCE ON WEPPCLOUD OR ITS OUTPUTS, HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE), EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

**Assumption of risk.** By using WEPPcloud, you acknowledge that simulation outputs are approximations subject to uncertainty and agree that you bear sole responsibility for any decisions, actions, or consequences arising from their use. You agree to independently verify any WEPPcloud outputs before relying on them for management decisions, regulatory compliance, or any purpose where errors could result in harm.

**Data sources.** WEPPcloud relies on publicly available datasets (SSURGO, NLCD, ESDAC, ASRIS, CLIGEN, RAP, E-OBS, and others) that are maintained by their respective agencies. Data quality, resolution, and currency vary by source and region. WEPPcloud does not independently verify the accuracy of these upstream datasets.

**Funding acknowledgments.** WEPPcloud development has been supported by the University of Idaho, USDA Forest Service Rocky Mountain Research Station, USDA Agricultural Research Service, Swansea University, Michigan Technological University, and the European Union's Horizon 2020 research and innovation program (grant agreement No. 10100389).
