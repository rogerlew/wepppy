## Omni is functionality for running scenarios inside of a parent weppcloud project


### Omni scenarios

- **Uniform High Severity**: Forest, shrubs, and grasses burned at high soil burn severity
- **Uniform Moderate Severity**: Forest, shrubs, and grasses burned at moderate soil burn severity
- **Uniform Low Severity**: Forest, shrubs, and grasses burned at low soil burn severity
- **Soil Burn Severity Map**: Forest, shrubs, and grasses burned at from soil burn severity (not implement, but easy to implement)
- **Thinning**: Forests use thinned management (pre-fire)
- **Mulching**: Mulching post fire (not implemented)
- **Seeding**: WIP (not implemented)

Scenarios are created within the `omni/scenarios` folder. Each scenario has it's own folder and is a weppcloud project.
It symlinks (equivalent of Windows shortcuts) to the parent project for shared inputs
The `wepp/output` folder contains all the hillslope and watershed files of a normal weppcloud project 


### Workflow

#### 1. Create Undisturbed weppcloud project

#### 2. Define omni scenarios

```python
omni = Omni.getInstance()
omni.scenarios = ['uniform_high', 'uniform_moderate', 'uniform_low', 'thinning']
```

#### 3. Run omni scenarios

```python
omni = Omni.getInstance()
omni.run_omni_scenarios()
```

##### Scenario dependency tracking

Omni persists lightweight bookkeeping alongside the scenarios in `omni.nodb` so repeated runs can skip work when upstream data is unchanged:

- `scenario_dependency_tree`: maps each scenario name to the dependency it was built from.  For every build Omni records the SHA1 hash of the dependency `loss_pw0.txt`, the normalized dependency target (e.g., `undisturbed`, `uniform_high`, etc.), the serialized scenario signature, and a timestamp of the last run.  When `run_omni_scenarios()` is called again the current hash/signature are compared with the stored entry and the build is skipped if both still match.
- `scenario_run_state`: contains the most recent status records returned by `run_omni_scenarios()`.  Each entry captures the scenario name, whether it was executed or skipped, the dependency target and file path used for hashing, the dependency hash, and the timestamp the decision was made.  This provides a quick audit trail visible to downstream tools or debugging workflows.

Dependency resolution is scenario aware: mulching scenarios hash the chosen base scenario’s `loss_pw0.txt`, while all other scenarios hash the parent project (undisturbed or SBS map).  Any change to that file’s contents or to the scenario definition (signature) forces a rebuild.


### Developer notes: cloning internals and gotchas

Omni builds every scenario workspace by cloning the parent project with `_omni_clone()` and, when necessary, overlaying a sibling scenario via `_omni_clone_sibling()`.  A few details matter if you are extending these helpers:

- **Workspace creation.** `_omni_clone()` creates `<parent>/_pups/omni/scenarios/<scenario>` and symlinks shared inputs (`climate/`, `dem/`, `watershed/`, their `.nodb` counterparts, etc.).  Per-scenario state (`disturbed/`, `landuse/`, `soils/`) is copied so each scenario can mutate it without touching the parent.
- **Writable copies.** Some production runs stamp a `READONLY` file into the project root; the clone explicitly removes it so downstream code can dump `.nodb` files.  Forgetting that step leaves the child project read-only and all subsequent `with locked()` calls explode.
- **Relinking `.nodb` metadata.** When `.nodb` files are copied, `_omni_clone()` rewrites their JSON payloads to update the `wd` and `_parent_wd` attributes.  Without that rewrite the nodb singletons continue to point at the parent run directory and every subsequent path lookup goes rogue.
- **Clearing caches and locks.** Both `_omni_clone()` and `_omni_clone_sibling()` call `_clear_nodb_cache_and_locks(runid, pup_relpath)` after swapping files.  This flushes the Redis-backed nodb cache and per-run locks so new workers do not load stale payloads or hang on inherited locks.
- **Sibling overlays.** `_omni_clone_sibling()` is used for scenarios that depend on another scenario’s disturbed/landuse/soils state (e.g., mulching built on `uniform_low`).  It replaces the cloned directories with copies from the sibling, dumps fresh `.nodb` files, and again clears caches before returning.

When creating your own clone routine, keep those steps in mind: ensure the workspace is writable, update the embedded `wd`, and always clear caches before handing the tree to the next stage of the pipeline.


### Running scenarios concurrently – lessons learned

Omni can run scenarios inside a single process (`run_omni_scenarios`) or scatter them across RQ workers (`run_omni_scenarios_rq`).  The latter provides throughput, but introduces a few pain points:

- **Stale singleton state.** Every worker loads its own `Omni` singleton at queue time.  If you mutate `_scenario_dependency_tree` or `_scenario_run_state`, reload the latest `omni.nodb` inside the lock before writing back, otherwise the last writer clobbers previous updates.
- **Process pools and Rosetta.** Soil preparation is CPU heavy.  We wrap it in a `ProcessPoolExecutor` with retry logic: try spawn first, retry with fork if the pool crashes, then fall back to sequential execution.  This avoids deadlocks when the spawn bootstrap explodes and keeps large projects from failing silently.
- **Lock contention.** Scenario jobs call `_locked_with_retry()`, which retries for 30 seconds before giving up.  Long-running tasks (soil prep, watershed runs) can exhaust that window.  If you add new critical sections make sure they release quickly or bump the timeout.
- **Resource cleanup.** Always clear nodb caches and locks when cloning or replacing scenario directories; otherwise a rescheduled job can pick up stale `.nodb` payloads that still point to deleted files and the run will fail mid-stream.
- **Logging fan-out.** Each pup writes its own `wepp.log`, `landuse.log`, etc.  If you spin up many workers at once, watch disk quotas and rotate logs if necessary.  The logging system falls back to console on errors, so a full disk manifests as missing run output and no dependency updates.

Running concurrently pays off with large watersheds, but the bookkeeping is fragile.  Treat nodb state as shared memory: reload before writing, clear caches when swapping files, and prefer idempotent tasks so a retry won’t corrupt downstream state.


#### 4. Objective parameter analysis to idenfity contrast hillslopes

Omni uses the gpkg exports to find hillslopes with high sediment, runoff, lateral flow, ...

Applies filter to limit selection of hillslopes


#### 5. Run Contrast Scenarios

Omni uses the gpkg exports to find hillslopes with high sediment, runoff, lateral flow, ...

Applies filter to limit selection of hillslopes

Contrast execution follows the same hashing approach:

- `contrast_dependency_tree` stores a signature for each contrast payload along with hashes of the control and contrast scenarios’ `loss_pw0.txt` files.  When `run_omni_contrasts()` is invoked, contrasts where the signature and dependency hashes still match are skipped automatically.
- Any contrast whose dependencies differ (e.g., the control scenario was re-run) is rebuilt and the tree updated with the new hash and timestamp.


## Project routing for Omni “pup” workspaces

Omni scenarios live under the parent project’s `_pups` directory and reuse the same routes that serve the base project. For a request like `/weppcloud/runs/considerable-imperative/disturbed9002/?pup=omni/scenarios/undisturbed`, the routing stack executes in this order:

- **Preprocessor hook.** Every `/runs/<runid>/<config>` blueprint is registered with `register_run_context_preprocessor`, which calls `load_run_context(runid, config)` before the view executes.
- **Parent lookup.** `load_run_context` resolves the canonical working directory with `get_wd(runid, prefer_active=False)`, guaranteeing it sees `/wc1/runs/co/considerable-imperative` even when a previous request already selected a pup.
- **Pup validation.** If a `pup` query string is present, the helper resolves the relative path under `_pups`, ensures it stays within that folder, and records the active child directory (`…/_pups/omni/scenarios/undisturbed`).
- **Context propagation.** The helper stores a `RunContext` on `flask.g`, exposing both the parent run root and the selected pup root. Subsequent calls to `get_wd(runid)` return the pup directory by default (`prefer_active=True`). Code that still needs the parent directory can pass `prefer_active=False` explicitly.
- **View logic.** Route handlers access nodb singletons with the context-aware `wd`, so `Ron.getInstance(wd)` and friends automatically operate on the scenario files. The main dashboard also marks pup projects as read-only to prevent destructive edits.
- **Response links.** When a view redirects or constructs URLs it preserves the `pup` argument, keeping the browser scoped to the scenario until the user navigates away.

This layer allows Omni’s child workspaces to share the existing WEPPcloud UI/REST surface without special-case routing—new endpoints simply need to call `load_run_context` (or rely on the preprocessor) and obtain paths via `get_wd()`.


## Meeting with Bill and Pete (3/13/2025)

### Mulching
using multipling coverage to adjust the percent bare

e.g. start with 80% bare (from burn severity)

#### Current Burn Severity Covers -> **Mulch Treatment 1/2-ton / acre 30% cover**
- Forest
  - High 30% -> 60%
  - Moderate 60% -> 90% 
  - Low 85% -> 100%
- Shrub
  - High 30% -> 60%
  - Moderate 55% -> 85% 
  - Low 80% -> 100%
- Grass
  - High 10% -> 40% 
  - Moderate 35% -> 65% 
  - Low 60% -> 90%

#### Current Burn Severity Covers -> **Mulch Treatment 1-ton / acre 60% cover**
- Forest
  - High 30% -> 90%
  - Moderate 60% -> 100% 
  - Low 85% -> 100%
- Shrub
  - High 30% -> 90%
  - Moderate 55% -> 100% 
  - Low 80% -> 100%
- Grass
  - High 10% -> 70% 
  - Moderate 35% -> 95% 
  - Low 60% -> 100%

Initial burn covers could be regionally dependent. More veg before fire results in more after fire (Lewis)

#### Mulching Treatments

From ERMiT
- Mulching 47% ground cover (1 Mg/ha ~1/2 ton/ac)
- Mulching 72% ground cover (2 Mg/ha ~1 ton/ac)  
- Mulching 89% ground cover (3-1/2 Mg/ha ~1-1/2 ton/ac)
- Mulching 94% ground cover (4-1/2 Mg/ha ~2 ton/ac)

Pete

**1 ton / acre straw mulch is 60% cover** what everyone is doing in reality.

wood mulch is 4x more expensive


### Seeding

seeding would only impacts 2nd year after fire. need to know the cover change with and without cover to know the change in cover. (lack of data)

use revegetation database to look at cover changes

might be fires where there are treatment boundaries
