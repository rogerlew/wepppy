# Getting Started with WEPPcloud

This guide walks you through creating your first WEPPcloud project and introduces the key features you will use along the way.

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

When you use OAuth, you authenticate directly with the provider (Google or GitHub). WEPPcloud receives only your name and email address to create or link your account. Your password is never shared with WEPPcloud. You can connect multiple OAuth providers to the same WEPPcloud account and disconnect them at any time from your profile page.

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

## Creating a Project

To start a new project, go to the WEPPcloud landing page and select an interface (such as **WEPPcloud-(Un)Disturbed-WBT** for U.S. watersheds). Choose your unit system (SI or English) and click **Launch**. If you are not signed in, you will complete a brief verification before proceeding.

WEPPcloud creates a new project workspace and opens the run page — the main screen where all of your work happens.

<!-- ![Launching a new project](static/getting-started/launch-interface.png) -->

---

## Your Run ID

Every project is assigned a **run ID** — a memorable, hyphenated phrase like `walk-in-obsessive-compulsive` or `bright-golden-retriever`. Run IDs are generated automatically and serve as the unique identifier for your project. You will see your run ID in the page header and in the URL.

Run IDs make it easy to reference a project in conversation, in reports, or when sharing a link with a colleague. You do not choose your run ID, but you can set a descriptive **project name** and **scenario name** (described below) to give your work a human-friendly label.

---

## How Projects Work

A WEPPcloud project is **directory-based**. When you create a project, WEPPcloud sets up a folder on the server that stores everything related to your run: elevation data, soils, land cover, climate files, model inputs, simulation outputs, and any files you upload.

As you work through each section of the run page — delineating a watershed, building landuse, configuring soils, selecting climate data, and running the WEPP model — you are **acquiring, processing, and saving resources** into your project directory. Each step builds on the previous one, gradually assembling a complete watershed model.

You can browse the contents of your project directory at any time from the **More → Browse** menu (described below).

<!-- ![Run page showing controller sections in the sidebar](static/getting-started/run-page-overview.png) -->

---

## The Run Page Walkthrough

The run page is organized as a single scrollable page with a **sidebar navigation** on the left and **controller sections** stacked vertically on the right.

### Sidebar Navigation

The sidebar lists every step in the modeling workflow. Click any item to jump to that section. The sidebar items are:

1. **Map & Analysis** — the interactive map where you view your watershed
2. **Soil Burn Severity** — upload a burn severity map (for fire-related projects)
3. **Channel Delineation** — define the area of interest and build the stream network
4. **Outlet** — set the watershed outlet point
5. **Subcatchments Delineation** — divide the watershed into subcatchments and hillslopes
6. **Landuse** — assign land cover types to each hillslope
7. **Soils** — assign soil properties to each hillslope
8. **Climate** — select a climate data source and time period
9. **WEPP** — run the erosion model

Additional sections appear in the sidebar when optional modules are enabled (see **Modules** below).

### Working Through the Controllers

You work through the sections roughly from top to bottom. Each section has a **Build** or **Run** button that processes that step. When a step completes, WEPPcloud saves the results to your project directory and you can move on to the next section.

A typical workflow looks like this:

1. **Zoom the map** to your area of interest.
2. **Build Channels** to acquire elevation data and delineate the stream network.
3. **Set the Outlet** by clicking a point on the map or entering coordinates.
4. **Build Subcatchments** to divide the watershed into modeling units.
5. **Build Landuse** to classify land cover on each hillslope.
6. **Build Soils** to assign soil properties.
7. **Build Climate** to select and prepare weather data.
8. **Run WEPP (hillslopes + watershed)** to simulate erosion on each hillslope then watershed.
9. **Run WEPP (watershed)** to route water and sediment just through the channel network (useful for calibration purposes).

After the model runs, results appear on the interactive map and are available for export.

<!-- ![Sidebar navigation with controller sections](static/getting-started/sidebar-navigation.png) -->

---

## Setting Project Name and Scenario

In the header bar at the top of the page, you will see two editable text fields next to your run ID:

- **Project Name** — a descriptive title for your project (e.g., "Cedar Creek Post-Fire Assessment")
- **Scenario** — a label for the specific scenario you are modeling (e.g., "High Severity Burn" or "Mulch Treatment")

Click either field, type your label, and it saves automatically. These labels help you organize and identify your work, especially when you have multiple projects or are comparing scenarios.

<!-- ![Header showing project name and scenario fields](static/getting-started/project-name-scenario.png) -->

---

## Project README

Every project has a **README** — a place to save notes, observations, and context about your run. Click the **README** button in the header to open the editor.

The README editor has a split-pane layout: you write in the left panel using Markdown formatting, and a live preview appears on the right. Your notes are saved to the project directory and can be viewed by anyone with access to the project. Use the README to document your assumptions, record field observations, or leave notes for collaborators.

<!-- ![README editor with live preview](static/getting-started/readme-editor.png) -->

---

## Fork (Duplicate a Project)

The **Fork** button in the header creates a complete copy of your project under a new run ID. Forking is useful when you want to:

- **Try an alternative scenario** without modifying your original work
- **Create a baseline copy** before making changes
- **Share a starting point** with a colleague

When forking, you also have the option to **Undisturbify** — this creates the copy, removes fire-related disturbance data (burn severity maps and fire-modified soils/landuse), resets the project to undisturbed baseline conditions, and reruns WEPP. This lets you quickly set up a "before fire" comparison scenario from an existing post-fire project.

<!-- ![Fork console with undisturbify option](static/getting-started/fork-console.png) -->

---

## Archive (Snapshot and Download)

The **Archive** button in the header opens the archive dashboard, where you can:

- **Create a snapshot** — save a point-in-time ZIP of your entire project. You can add a short comment (up to 40 characters) to label the snapshot.
- **Download** — download any snapshot as a ZIP file to your computer.
- **Restore** — roll your project back to a previous snapshot, replacing the current state with the archived version.
- **Delete** — remove snapshots you no longer need.

Archives are stored inside your project directory. Use them to preserve milestones before making major changes, or to create a portable copy of your work.

<!-- ![Archive dashboard showing snapshots](static/getting-started/archive-dashboard.png) -->

---

## Theme Selector

WEPPcloud includes a **theme selector** in the header bar that lets you change the visual appearance of the interface. Choose from over a dozen light and dark themes, including:

- **Default (Light)** — the standard light appearance and part of the AA-checked theme set
- **Light High Contrast** — optimized for accessibility and part of the AA-checked theme set
- **OneDark** — a popular dark theme inspired by Atom
- **Ayu Dark / Ayu Mirage** — modern dark themes with flat styling (`Ayu Mirage` is AA-checked)
- **Cursor Dark** — dark themes with multiple contrast levels (`Cursor Dark (Midnight)` is AA-checked)

Your theme choice is saved in your browser and applies across all your WEPPcloud sessions. Themes marked **AA checked** are part of the validated accessibility set. Themes marked **Sensory preference** remain available for users who prefer lower-stimulation palettes, but they are not part of the AA conformance set.

<!-- ![Theme selector dropdown](static/getting-started/theme-selector.png) -->

---

## Modules (Mods)

WEPPcloud has an extensible **module system** that adds specialized modeling capabilities, data sources, and analysis tools to your project. Modules are activated from the **Mods** dropdown in the header bar.

### What Modules Do

Each module extends what your project can do. When you enable a module, a new section appears in the sidebar navigation, and additional data and modeling options become available. Modules may add new map layers, new export formats, or entirely new models that run alongside WEPP.

### Available Modules

| Module | What It Adds |
|--------|-------------|
| **Ash Transport** | Post-fire ash and contaminant transport modeling for water quality assessment |
| **Debris Flow** | Debris-flow hazard estimation using USGS risk equations and precipitation data |
| **Treatments** | Management treatment tracking for scenarios like mulching, seeding, and thinning |
| **Omni Scenarios** | Side-by-side comparison of multiple treatment scenarios against a control |
| **RUSLE** | RUSLE erosion factor integration for alternative erosion estimates |
| **Roads** | Road and stream-crossing erosion analysis |
| **Observed Data** | Import and compare field-measured data against model predictions |
| **RAP Time Series** | Rangeland Analysis Platform vegetation cover time series |
| **OpenET Time Series** | Satellite-derived evapotranspiration data from OpenET |
| **Features Export** | Export results to GIS formats (Shapefile, GeoJSON, GeoParquet) |
| **Path CE** | Cost-effectiveness optimization for post-fire mulch treatments |

Module availability depends on your run configuration, backend, and user role. For the current canonical list of mods, dependencies, and outputs, see [Mods Overview](mods-overview.md).

### Enabling a Module

Click the **Mods** dropdown in the header and toggle a module on. A new section appears in the sidebar. Some modules have dependencies (for example, Ash Transport requires burn severity data), and WEPPcloud will guide you if prerequisites are needed.

<!-- ![Mods dropdown showing available modules](static/getting-started/mods-dropdown.png) -->

---

## The "More" Menu

The **More** dropdown in the header provides access to project settings, utilities, and navigation. Here is what you will find:

### Browse

Opens a **file browser** where you can explore everything in your project directory — input files, model outputs, logs, rasters, and data tables. You can view text files with syntax highlighting, preview data tables, and download individual files. This is useful for inspecting raw model inputs and outputs.

### Change Units

Opens the **unit settings** panel where you can switch between SI (metric) and English (imperial) units, or customize units for individual measurement categories.

### Manage Team

Invite collaborators to your project by email address. Shared team members can view and work on the same project.

### Readonly Toggle

Lock your project to prevent accidental modifications. When Readonly is enabled, all Build and Run buttons are disabled.

### Public Toggle

Control whether your project is visible to anyone with the link. By default, projects owned by registered accounts are private. Toggle Public to share your project openly.

### Open Links in New Tabs

A convenience toggle that controls whether navigation links open in the current tab or a new tab.

### PowerUser Panel

An advanced panel that provides direct access to all project resources, detailed parameters, and diagnostic tools. Most users will not need this, but it is available for researchers who want to inspect or fine-tune model inputs at a granular level.

For administrators, the Actions column also includes **Mint Run Token**, which issues a 24-hour run-scoped JWT for operational workflows such as credentialed syncing and API debugging. Treat minted tokens as secrets and rotate them after use.

### Profile and Runs

Quick links to your **user profile** (account settings, API tokens) and your **runs dashboard** (a list of all your projects).

<!-- ![More menu dropdown](static/getting-started/more-menu.png) -->

---

## Tips for New Users

- **Save your work as you go.** Each Build step saves its results automatically, but consider creating an **Archive** snapshot before running the WEPP model or making significant changes.
- **Use the README** to document your assumptions and decisions — your future self will thank you.
- **Fork before experimenting.** If you want to try a different scenario, fork your project first so you can always return to the original.
- **Browse your project files** to understand what WEPPcloud is producing at each step. The file browser is a great learning tool.
- **Start simple.** Run a basic undisturbed project before adding modules like Ash Transport or Omni Scenarios.
