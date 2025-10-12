# wepppy NoDb Singletons

> Looking for coding ground rules? Start with `style-guide.md` in this folder for clarity and ergonomics expectations before diving into the NoDb specifics.

WEPPcloud keeps long-lived project state in a constellation of "NoDb" singleton objects instead of a relational database. Each singleton wraps a JSON (JSONPickle) file under the project's working directory and exposes a Pythonic surface for reading and mutating model inputs. Redis provides coarse-grained locking and caching so these objects can be quickly deserialized and shared across workers and RQ tasks without stomping on one another. This document outlines what the NoDb layer is, how it behaves, and how to extend it safely.

## What are they?

- **Per-run singletons.** Every `*.nodb` class is effectively a singleton per run directory (`wd`). `NoDbBase.getInstance(wd)` either loads from Redis cache/db13 or hydrates the JSON file on disk, so callers always receive the same in-memory object for that run.
- **File-backed structures.** Instances serialize themselves with `jsonpickle` into `<runid>/<name>.nodb`. The class' `filename` attribute ties the Python type to its persisted payload.
- **Redis-aware.** Instantiation primes logging, publishes into Redis status channels, and consults Redis for locks (`db0`) and cache snapshots (`db13`).
- **Domain modules.** Each major domain—watershed delineation, land use, soils, climate, WEPP configuration, run metadata (`Ron`), observed data—implements a subclass with additional behavior, helpers, and computed properties.

Typical access pattern:

```python
from wepppy.nodb.core import Wepp, Landuse, Watershed

wd = "/wc1/runs/fl/flying-cockatoo"
wepp = Wepp.getInstance(wd)
landuse = Landuse.getInstance(wd)
watershed = Watershed.getInstance(wd)
```

## How do they work?

All NoDb classes inherit from `wepppy.nodb.base.NoDbBase`, which layers common services:

- **Locking.** `with instance.locked(): ...` toggles `locked:<filename>` inside the run hash (Redis DB 0). Mutations must happen inside this context so other workers detect in-progress writes.
- **Persistence.** `dump()` writes the JSONPickle payload to disk then caches the same blob in Redis DB 13. New readers can usually skip disk I/O.
- **Logging pipeline.** Each instance wires a queue-based logger, attaches a Redis `StatusMessengerHandler`, and persists `*.log` and shared `exceptions.log` next to the `*.nodb` file.
- **Config plumbing.** Convenience methods such as `config_get_bool`, `config_get_path`, and `config_get_list` pull values from the project's `.cfg` files while preserving case sensitivity.
- **Cross-linking.** Properties like `watershed_instance` or `landuse_instance` lazily retrieve sibling NoDb singletons from the same working directory, keeping modules loosely coupled.

Creating a NoDb file:

```python
from wepppy.nodb.core import Landuse

landuse = Landuse("/tmp/runid", cfg_fn="some.cfg")  # Raises if a landuse.nodb already exists
with landuse.locked():
    landuse.mode = LanduseMode.Gridded
    landuse.mapping = "nlcd"
```

Loading an existing instance safely:

```python
from wepppy.nodb.core import Landuse

landuse = Landuse.getInstance(wd)
print(landuse.mapping)
```

### Mods

`wepppy.nodb.mods` contains optional add-ons (disturbed flows, debris, omni scenarios, etc.) that register themselves by re-exporting classes inside `mods/__init__.py`. `NoDbBase._load_mods()` imports these packages so their `getInstance` helpers are available globally.

Many mods provide their own NoDb-backed objects. Example: `wepppy.nodb.mods.disturbed.Disturbed` tracks burn severity maps, optional treatments, and integrates with `RedisPrep` timestamps. Access mirrors core modules:

```python
from wepppy.nodb.mods.disturbed import Disturbed

disturbed = Disturbed.getInstance(wd)
if disturbed.has_map:
    disturbed.logger.info("Disturbance raster found")
```

Keep mod state minimal—most features piggyback on the same locking and persistence semantics defined in `NoDbBase`.

### Trigger scheme

NoDb classes raise lifecycle triggers by stamping `RedisPrep` timestamps (stored in Redis DB 0) and writing status messages to Redis DB 2. Consumers (preflight service, UI) turn those markers into progress bars and UI affordances.

Common touchpoints:

```python
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

prep = RedisPrep.getInstance(wd)
prep.timestamp(TaskEnum.build_landuse)
prep.set_rq_job_id("build_landuse", job.id)
```

`TriggerEvents` in `base.py` enumerate major milestones. Long-running RQ jobs publish both `TriggerEvents` (via logging/status messages) and `TaskEnum` timestamps, ensuring the microservices know when a step is finished and any dependent UI panels can unlock.

### Modules overview

Below is a tour of the core singletons. Each section highlights what the class manages, common helpers, and gotchas when extending the code.

#### `Ron` Run Object Node

- Purpose: stores run manifest (name, owner, scenario metadata, flags like `readonly` and `public`).
- Key APIs: `Ron.getInstance(wd)`, `ron.name`, `ron.scenario`, `ron.stub` (JSON-safe view for templates).
- Integration: used by UI templates, README editor, and authorization helpers. Because many routes call `Ron.getInstance`, keep the payload lean.

```python
from wepppy.nodb.core import Ron

ron = Ron.getInstance(wd)
print(f"Run {ron.name} in scenario {ron.scenario}")
```

#### `RedisPrep`

- Purpose: central run hash inside Redis DB 0. Tracks booleans (`attrs:*`), timestamps (`timestamps:*`), RQ job IDs (`rq:*`), archive pointers, and lock status.
- Key APIs: `timestamp(TaskEnum)`, `set_rq_job_id(key, job_id)`, `dump()` to persist to `redisprep.dump` for cold starts.
- Notes: `RedisPrep.getInstance(wd)` loads the hash straight from Redis; calling `.dump()` mirrors it to disk for offline diagnostics.

```python
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum

prep = RedisPrep.getInstance(wd)
prep.timestamp(TaskEnum.run_wepp_watershed)
print(prep.get_rq_job_ids())
```

#### `Watershed`

- Purpose: owns watershed abstraction artifacts—TauDEM outputs, Peridot flowpaths, channel summaries, extents, and delineation metadata.
- Highlights: caches expensive raster-derived summaries, exposes `run_abstract_watershed` helpers, and guards operations behind `WatershedNotAbstractedError`.
- Gotchas: large JSON payloads; use `_post_instance_loaded` to normalize/transcode when structure changes (see `TRANSIENT_FIELDS`).

```python
from wepppy.nodb.core import Watershed, WatershedNotAbstractedError

watershed = Watershed.getInstance(wd)
translator = watershed.translator_factory()
wepp_id = translator.wepp(top=topaz_id)
```

#### `Landuse`

- Purpose: manages land cover rasters, mappings to WEPP managements, and single-selection metadata.
- Traits: `mode`, `mapping`, `domlc_d` caches, fractional cover support, MOFE (multi-ofe) buffers. `_post_instance_loaded` enforces key ordering for deterministic output.
- Pattern: always mutate via `with landuse.locked():` to keep lock flags in sync.

#### `Soils`

- Purpose: orchestrates SSURGO/ESDAC fetches, textural interpolation, and mapping to WEPP soil parameters.
- Hooks: interacts with `wepppy.wepp.soils.utils.WeppSoilUtil`, caches derived soil files, tracks whether soils were rebuilt for MOFE scenarios.
- Considerations: soils payloads can be huge—ensure new attributes remain serializable and prune transient caches when dumping.

#### `Climate`

- Purpose: builds CLI/PRN files, samples from Cligen stations, and generates gridded time series (PRISM, GRIDMET, Daymet).
- Features: supports multiple modes (single station, gridded, RCP futures), uses thread/process pools to parallelize fetches, and stores `ClimateMode` along with derived summaries.
- Note: because building climate often streams remote data, be careful to keep network handles and thread pools out of the persisted object (use transient attributes or remove them before dump).

#### `Wepp`

- Purpose: central orchestrator for running WEPP: holds binary paths, generated runs (`wepp/runs`), baseflow/snow configs, selected scenarios, and convenience wrappers around `wepp_runner` utilities.
- Patterns: heavy use of `StatusMessenger` to stream real-time progress; interacts closely with `Watershed`, `Landuse`, `Soils`, and `Climate` instances.
- Locking: functions like `run_wepp_rq` obtain `Wepp.getInstance(wd)` and immediately check `wepp.islocked()` to avoid overlapping runs.

#### `Observed`

- Purpose: stores observed data feeds (rain gauges, sediment measurements) for calibration runs.
- Behavior: primarily acts as a structured cache of uploaded CSV/JSON, enabling UI comparisons without hitting a database.

#### `Unitizer`

- Purpose: tracks unit conversions and scaling parameters across the run (e.g., metric vs imperial toggles).
  Internal wepppy uses units of convenience. Sometimes these are SI, sometimes they are English. The models do not attempt to book-keep both SI and English units. The unitizer allows values and their types to be specified in reports and viewed in either SI or English units from WEPPcloud

### Philosophy

NoDb trades relational rigor for portability and developer ergonomics.

#### Advantages

- **File-based portability.** A run directory remains self-contained: zip it, move it, and the NoDb JSONs boot in a new environment.
- **Schema flexibility.** Adding attributes rarely requires migrations—`jsonpickle` tolerates missing fields, and `_post_instance_loaded` can reshape legacy payloads.
- **Rich Python surface.** Developers consume domain-specific methods instead of crafting SQL queries, keeping business logic near the data it manipulates.
- **Redis acceleration.** In-memory caching and locking let distributed workers share state with minimal contention while still crashing safely to disk.

#### Disadvantages

- **Backward compatibility pressure.** Overriding property attributes needs `_js_decode_replacements` or similar shims to keep legacy runs loadable.
- **Lock discipline.** Mutations must happen inside `with instance.locked():` blocks. Forgetting to lock means concurrent RQ jobs can overwrite each other or `dump()` will raise. Or forgetting to lock leads to lost assignments.
- **Large payloads.** JSONPickle files balloon as projects grow. Keep derived rasters, time series, and caches on disk, not inside the JSON.
- **Serialization quirks.** Objects must remain picklable—no open file handles, lambdas, or complex iterators stored on the instance. Numpy objects make the JSON ugly
- **Learning curve.** The pattern is bespoke; newcomers must internalize lock semantics, Redis requirements, and where transient artifacts live.

#### Compatibility hacks

Historical payloads sometimes require awkward patches (re-ordered dicts, renamed classes, stub properties). When introducing schema changes:

1. Add `_js_decode_replacements` entries to translate legacy module paths.
2. Implement `_post_instance_loaded` to normalize instances after decode.
3. Provide upgrade scripts in `nodb/scripts/` if the change is too large to fix lazily.

### Working with locks

`locked()` automatically calls `dump_and_unlock()` on success. If an exception bubbles out, the context manager resets the Redis flag to `false` but skips `dump()`. Always rethrow or handle errors so callers know the state may be incomplete.

### Redis integration recap

- `db0`: hash per run (locks, attrs, timestamps, RQ job IDs, archive pointer).
- `db2`: Pub/Sub channels for streaming logs (`StatusMessenger` → `services/status2`).
- `db13`: cached JSONPickle blobs for faster cold loads.

Ensure Redis is reachable before manipulating NoDb instances: startup code in `base.py` logs CRITICAL errors and falls back to slow path if the cache is offline.

### Adding a new NoDb singleton

1. Derive from `NoDbBase`, set `filename`, and implement `__init__` to create default structure inside `with self.locked():`.
2. Provide a `getInstance` wrapper (usually via package exports) so call sites never touch the constructor directly.
3. Keep persisted attributes simple (numbers, strings, lists, dicts). When storing heavy artifacts, write to the run directory and track paths in the JSON instead.
4. Use `_post_instance_loaded` to normalize or seed transient fields after decode.
5. When refactoring, update tests under `wepppy/nodb/tests` to cover new flags and backward compatibility behavior.

```python
from wepppy.nodb.base import NoDbBase

class Example(NoDbBase):
    filename = "example.nodb"

    def __init__(self, wd, cfg_fn):
        super().__init__(wd, cfg_fn)
        with self.locked():
            self._version = 1
            self._items = []

    @classmethod
    def _post_instance_loaded(cls, inst):
        inst = super()._post_instance_loaded(inst)
        inst._items = list(inst._items or [])
        return inst
```

### Operational notes

- Projects can be flagged READONLY with file based mechanism. READONLY projects will raise Exception on `locked()`
- To recover from a wedged lock (e.g., worker crash), call `wepppy.nodb.base.clear_locks(runid)`. This helper function is low level and uses relection to iterate over all the `NoDbBase` subclasses.

## Appendix: Frequently used helpers

- `NoDbBase.getInstanceFromRunID(runid)` fetches by run identifier without knowing the full path.
- `NoDbBase.timed("task")` context manager logs start/end to Redis and log files.
- `clear_locks(runid)` (from `base.py`) resets `locked:*` flags for all NoDb files in a run—helpful after interrupted RQ batches. (With the locked contextmanager and redis file locking; locking has become much more reliable)
- `lock_statuses(runid)` returns current lock booleans for UI diagnostics.
- Redis is non-persistent `RedisPrep.dump()` writes the run hash to `redisprep.dump`; `lazy_load()` restores it into Redis if necessary. The dump contains timestamps of when operations finished to populate the preflight checklist.

Armed with these patterns you can extend the NoDb layer confidently, keeping WEPPcloud projects portable while coordinating complex build pipelines across distributed workers.
