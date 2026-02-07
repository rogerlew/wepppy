# WEPP-WQ Integration Feasibility (wepp-forest)

## Purpose
Assess what is required to integrate WEPP-WQ (/workdir/WEPP-WQ) into the wepp-forest codebase, using the McGehee 2023 model development reference in `docs/McGehee_2023_WEPP-WQ_Model_Development_Reference.md` as the authoritative description of WEPP-WQ scope and inputs.

## Current Baseline (wepp-forest)
- **Codebase**: Fixed-source Fortran (`.for`) with extensive COMMON blocks; build uses `ifx` and assumes `.for` sources.
- **Version**: `ver = 2020.5` in `src/inidat.for` (WEPP-WQ reference is based on WEPP 2012.8).
- **Existing water-quality hooks**: Limited phosphorus handling via `phosphorus.txt` and channel flow variables (e.g., `src/main.for`, `src/wshcqi.for`).

## WEPP-WQ Scope to Integrate (from McGehee 2023)
- Adds **daily nonpoint source (NPS) chemical simulation** for nutrients and pesticides across **multiple OFEs**.
- Introduces **new chemical processes** (mineralization, volatilization, pesticide dynamics, deposition) and **physical transport** pathways (runoff, sediment, vertical/lateral flow, tile drains).
- Requires **SWAT 2012 databases** and new **WEPP-WQ input files** (atmospheric input, soil chemical input, chemical management input, control file).
- Refactors chemical code into **modern Fortran (free-source)** with a **global parameter module** and a consolidated output file.

## Integration Requirements

### 1) Source Code Integration
- **Add WEPP-WQ sources**: The following WEPP-WQ files are not in wepp-forest and would need to be integrated (or ported):
  - `WEPP-WQ/SRC/*.f90` (e.g., `chemical.f90`, `parameterModule.f90`, `initializeChemicalSimulation.f90`, `read*InputFile.f90`, `writeChemicalOutput.f90`).
- **Connect WEPP state to WEPP-WQ module variables**:
  - WEPP-WQ expects arrays for **OFE-level hydrology**, **soil layers**, **crop/residue**, **sediment**, and **management**.
  - wepp-forest holds these in COMMON blocks; a mapping layer is required to populate WEPP-WQ module variables each day and OFE.
- **Call sites**:
  - WEPP-WQ’s `chemical` routine is designed to execute **once per day per OFE**. This requires insertion in wepp-forest’s daily simulation loop(s).
- **Initialization and teardown**:
  - WEPP-WQ has explicit initialization/zeroing routines (`initializeChemicalSimulation`, `initializeSoilChemistry`, `zeroChemicalVariables`, etc.) that must be wired into wepp-forest’s init and yearly/day reset phases.
- **Conflict resolution with existing WQ logic**:
  - wepp-forest already reads `phosphorus.txt` and tracks baseflow-related P in channel routing.
  - Decide whether to **replace**, **merge**, or **deprecate** existing P routines to avoid double-counting or inconsistent pathways.

### 2) Build System and Fortran Compatibility
- **Free-source Fortran support**:
  - WEPP-WQ uses **free-format F90** and a **MODULE** (`parameterModule.f90`).
  - Update `src/makefile` to compile `.f90` sources, add module include paths, and ensure correct compilation order.
- **Mixed-language considerations**:
  - If wepp-forest stays in fixed-format `.for`, you must either:
    1. **Enable mixed F77/F90 compilation**, or
    2. **Backport WEPP-WQ to fixed-source Fortran** (high effort; likely error-prone).

### 3) Input Files and Databases
- **New WEPP-WQ inputs** (per McGehee 2023):
  - Atmospheric input file
  - Soil chemical input file
  - Chemical management input file
  - Control file specifying OFEs and file references
- **SWAT 2012 reference data**:
  - Fertilizer database
  - Pesticide database
  - Crop database
  - Crop reference table (WEPP ↔ SWAT crop names)
- **Integration tasks**:
  - Define expected file locations (relative paths vs absolute).
  - Add parsing and validation at model start.
  - Update run configuration or CLI to pass these file paths.

### 4) Outputs and Reporting
- WEPP-WQ consolidates chemical outputs into a **single, comprehensive file**.
- Decide how this output integrates with existing WEPP output conventions:
  - New output file format?
  - Extend existing output files?
  - Optionally add a feature flag to enable WQ outputs.

### 5) SWAT+ DOC Integration (Optional)
- **SWAT+ DOC status**: In current SWAT+ sources, DOC/DIC parameters and output fields exist, but the only implemented dissolved C transport is **total dissolved C** computed in `nut_orgnc2`. DOC/DIC are not split unless additional logic is added.
- **Post-run feasibility**: A hillslope-scale DOC estimator can be run after WEPP using pass files or daily water balance outputs, but it is **approximate** because WEPP does not track microbial biomass C pools.
- **Minimum inputs**: Surface runoff, subsurface/lateral flow (`sbrunf`), percolation (`sep`), tile drainage, sediment yield, soil organic matter (from inputs), and residue mass (plant output).
- **Higher-fidelity option**: Add explicit carbon pool outputs (or a lightweight C pool tracker) to provide microbial/active/stable C state and support a DOC/DIC split.
- **Recommendation**: Treat DOC as an optional, calibrated post-processor with documented assumptions and a separate validation dataset.

### 6) Version Reconciliation
- WEPP-WQ development is based on **WEPP 2012.8**; wepp-forest is **2020.5**.
- Required work:
  - Identify code drift between 2012.8 and 2020.5 for routines WEPP-WQ touches.
  - Resolve any updated variable names, data structures, or behavior changes in wepp-forest.

### 7) Testing and Validation
- Establish **regression baselines** using WEPP-WQ `DATA/` validation sets (where permissible).
- Validate:
  - Base hydrology/erosion outputs remain unchanged when WQ is disabled.
  - WEPP-WQ outputs match the reference behavior for equivalent inputs.
- Add a **minimal automated test harness** for chemical output sanity (e.g., non-negative pools, mass balance checks).

### 8) Licensing and Distribution
- WEPP-WQ explicitly includes only **nonproprietary source**; it depends on the **proprietary WEPP core**.
- Confirm:
  - Any redistribution of SWAT database files and WEPP-WQ code complies with their licenses.
  - The integrated wepp-forest distribution aligns with WEPP-WQ’s constraints.

## Feasibility Snapshot
- **Technically feasible**, but **non-trivial** due to:
  - Fortran 77 ↔ Fortran 90 integration and module plumbing.
  - Large data/variable mapping effort from WEPP internals to WEPP-WQ module expectations.
  - Version drift between WEPP 2012.8 and wepp-forest 2020.5.
- **Primary effort drivers**: code integration and validation, not just file copying.

## Recommended Next Steps
1. **Inventory integration points**:
   - Identify where to hook the daily OFE loop and initialization in wepp-forest.
2. **Create a mapping spec**:
   - Map WEPP-WQ module variables to existing COMMON block variables.
3. **Prototype build**:
   - Add a minimal F90 build target with `parameterModule.f90` and a stub call.
4. **Input/output scaffolding**:
   - Add parsing for the WEPP-WQ control file and write a minimal output file.
5. **Iterate with test cases**:
   - Use one known WEPP-WQ case to validate against reference outputs.

## Reference
- `docs/McGehee_2023_WEPP-WQ_Model_Development_Reference.md`
- `/workdir/WEPP-WQ/README.md`
- `/workdir/WEPP-WQ/SRC/`
