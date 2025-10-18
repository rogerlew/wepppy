# WEPPpy API Reference

> Quick reference for key APIs, patterns, and interfaces

## Table of Contents
- [NoDb Controllers API](#nodb-controllers-api)
- [Flask Routes API](#flask-routes-api)
- [Background Jobs API](#background-jobs-api)
- [Query Engine API](#query-engine-api)
- [Common Patterns](#common-patterns)

## NoDb Controllers API

### NoDbBase (Core Class)

**Module**: `wepppy.nodb.base`

```python
from wepppy.nodb.base import NoDbBase

class NoDbBase:
    """Base class for all NoDb singleton controllers.
    
    Each instance manages state for a working directory (wd).
    State is serialized to disk and cached in Redis DB 13.
    """
    
    @classmethod
    def getInstance(cls, wd: str) -> 'NoDbBase':
        """Get or create singleton instance for working directory.
        
        Args:
            wd: Absolute path to working directory
            
        Returns:
            Singleton instance for this wd
            
        Example:
            >>> from wepppy.nodb.core import Wepp
            >>> wepp = Wepp.getInstance('/wc1/runs/my-run')
        """
        
    def locked(self) -> ContextManager:
        """Acquire distributed lock via Redis DB 0.
        
        Yields:
            Self, for use in `with` statement
            
        Raises:
            NoDbAlreadyLockedError: If lock is held by another process
            
        Example:
            >>> with wepp.locked():
            ...     wepp.some_property = 'new value'
            ...     wepp.dump_and_unlock()
        """
        
    def dump_and_unlock(self) -> None:
        """Persist state to disk and Redis cache, then release lock.
        
        Writes:
            - JSON file to {wd}/{classname}.nodb
            - Cached JSON to Redis DB 13 (72-hour TTL)
            
        Example:
            >>> with wepp.locked():
            ...     wepp.phosphorus_opts = PhosphorusOpts(surf_runoff=0.01)
            ...     wepp.dump_and_unlock()
        """
        
    @property
    def _logger(self) -> logging.Logger:
        """Per-instance logger with telemetry pipeline.
        
        Log messages automatically flow to:
        - File: {wd}/_logs/{classname}.log
        - Console: stdout
        - Redis: pub/sub channel {runid}:{classname}
        - Browser: via WebSocket (status2 service)
        
        Example:
            >>> self._logger.info("Starting climate download")
            >>> self._logger.error("Download failed", exc_info=True)
        """
```

### Climate Controller

**Module**: `wepppy.nodb.core.climate`

```python
from wepppy.nodb.core import Climate, ClimateMode

class Climate(NoDbBase):
    """Manages climate data acquisition and processing.
    
    Attributes:
        mode: ClimateMode enum (CLIGEN, OBSERVED, VANILLA, etc.)
        station_id: Selected weather station identifier
        climate_data: Downloaded climate records
    """
    
    def download_climate_data(self, station_id: str) -> None:
        """Download climate data from selected source.
        
        Args:
            station_id: Weather station identifier
            
        Raises:
            NoClimateStationSelectedError: If station_id is invalid
            
        Example:
            >>> climate = Climate.getInstance(wd)
            >>> climate.mode = ClimateMode.CLIGEN
            >>> climate.download_climate_data('14826')
        """
        
    def build_climate_files(self) -> None:
        """Generate .cli files for WEPP simulation.
        
        Writes:
            - {wd}/wepp/runs/p*.cli for each hillslope
            
        Example:
            >>> climate.build_climate_files()
        """

# Enums
class ClimateMode(IntEnum):
    """Climate data source selection."""
    UNDEFINED = -1
    CLIGEN = 0        # Statistical climate generator
    OBSERVED = 1      # Historical observations
    VANILLA = 2       # Pre-generated climate
    FUTURE = 3        # Climate projections
    DAYMET = 4        # Daymet gridded data
    GRIDMET = 5       # GridMET data
    PRISM = 6         # PRISM data
```

### Watershed Controller

**Module**: `wepppy.nodb.core.watershed`

```python
from wepppy.nodb.core import Watershed

class Watershed(NoDbBase):
    """Manages watershed abstraction and subcatchment data.
    
    Attributes:
        outlet: Outlet point coordinates
        subcatchments: List of subcatchment polygons
        channels: Channel network topology
    """
    
    def abstract_watershed(self) -> None:
        """Execute watershed abstraction via peridot/TOPAZ.
        
        Generates:
            - Subcatchment polygons (GeoJSON)
            - Channel network (GeoJSON)
            - WEPP-ready input files
            
        Raises:
            WatershedNotAbstractedError: If DEM missing
            
        Example:
            >>> watershed = Watershed.getInstance(wd)
            >>> watershed.outlet = Outlet(lat=46.8, lng=-116.8)
            >>> watershed.abstract_watershed()
        """
        
    @property
    def num_subcatchments(self) -> int:
        """Number of subcatchments in abstraction."""
        
    @property
    def total_area_km2(self) -> float:
        """Total watershed area in square kilometers."""
```

### WEPP Controller

**Module**: `wepppy.nodb.core.wepp`

```python
from wepppy.nodb.core import Wepp, PhosphorusOpts

class Wepp(NoDbBase):
    """Manages WEPP model configuration and execution.
    
    Attributes:
        phosphorus_opts: Phosphorus modeling parameters
        baseflow_opts: Baseflow routing parameters
        run_results: Simulation output summary
    """
    
    def prep_hillslopes(self) -> None:
        """Prepare hillslope input files (.slp, .man, .sol, .cli).
        
        Example:
            >>> wepp = Wepp.getInstance(wd)
            >>> wepp.prep_hillslopes()
        """
        
    def run_hillslopes(self) -> None:
        """Execute WEPP hillslope simulations (parallel).
        
        Spawns:
            - One wepp process per hillslope
            - Progress logged to Redis pub/sub
            
        Example:
            >>> wepp.run_hillslopes()  # Blocks until complete
        """
        
    def run_watershed(self) -> None:
        """Execute WEPP watershed simulation.
        
        Requires:
            - Hillslope runs complete
            - Channel input files prepared
            
        Example:
            >>> wepp.run_watershed()
        """
        
    @property
    def avg_soil_loss_tha(self) -> float:
        """Average soil loss in tonnes per hectare."""

class PhosphorusOpts:
    """Phosphorus modeling configuration.
    
    Attributes:
        surf_runoff: Surface runoff coefficient (0-1)
        lateral_flow: Lateral flow coefficient (0-1)
        baseflow: Baseflow coefficient (0-1)
        sediment: Sediment-attached coefficient (0-1)
    """
```

### Landuse Controller

**Module**: `wepppy.nodb.core.landuse`

```python
from wepppy.nodb.core import Landuse, LanduseMode

class Landuse(NoDbBase):
    """Manages land cover/use data and management files.
    
    Attributes:
        mode: LanduseMode enum (NLCD, SINGLE, etc.)
        managements: Map of cover types to management files
    """
    
    def build_managements(self) -> None:
        """Generate .man files for each subcatchment.
        
        Writes:
            - {wd}/wepp/runs/p*.man
            
        Example:
            >>> landuse = Landuse.getInstance(wd)
            >>> landuse.mode = LanduseMode.NLCD
            >>> landuse.build_managements()
        """

class LanduseMode(IntEnum):
    """Land cover data source."""
    UNDEFINED = -1
    SINGLE = 0      # Single management for entire watershed
    NLCD = 1        # National Land Cover Database
    GRIDDED = 2     # Custom gridded data
```

### Soils Controller

**Module**: `wepppy.nodb.core.soils`

```python
from wepppy.nodb.core import Soils, SoilsMode

class Soils(NoDbBase):
    """Manages soil data and WEPP soil files.
    
    Attributes:
        mode: SoilsMode enum (SSURGO, STATSGO, etc.)
        soils_map: Map of subcatchments to soil IDs
    """
    
    def build_soils(self) -> None:
        """Generate .sol files for each subcatchment.
        
        Example:
            >>> soils = Soils.getInstance(wd)
            >>> soils.mode = SoilsMode.SSURGO
            >>> soils.build_soils()
        """

class SoilsMode(IntEnum):
    """Soil data source."""
    UNDEFINED = -1
    SINGLE = 0      # Single soil for entire watershed
    SSURGO = 1      # USDA SSURGO database
    STATSGO = 2     # USDA STATSGO database
```

## Flask Routes API

### Project Routes

**Module**: `wepppy.weppcloud.routes.project`

```python
# GET /weppcloud/project/new
# Create new project

# POST /weppcloud/project/{runid}/delete
# Delete project

# GET /weppcloud/project/{runid}/export
# Export project as ZIP
```

### RQ (Background Job) Routes

**Module**: `wepppy.weppcloud.routes.rq.api`

```python
# POST /weppcloud/rq/run/{runid}/task/{task_name}
# Enqueue background task
# Response: {"job_id": "uuid", "status": "queued"}

# GET /weppcloud/rq/job/{job_id}/status
# Check job status
# Response: {"status": "finished|failed|started", "result": {...}}

# POST /weppcloud/rq/job/{job_id}/cancel
# Cancel running job
```

### Map Routes

**Module**: `wepppy.weppcloud.routes.map`

```python
# GET /weppcloud/map/{runid}
# Render map interface

# POST /weppcloud/map/{runid}/set_outlet
# Set watershed outlet point
# Payload: {"lat": 46.8, "lng": -116.8}
```

## Background Jobs API

### Job Decorator

**Module**: `wepppy.rq`

```python
from wepppy.rq import job

@job('default', timeout=3600)
def my_background_task(runid: str, **kwargs) -> dict:
    """Background task template.
    
    Args:
        runid: Run identifier (required first arg)
        **kwargs: Additional task parameters
        
    Returns:
        Dict with task results
        
    Example:
        >>> from wepppy.rq.project_rq import my_background_task
        >>> job = my_background_task.delay('copacetic-note', param1='value')
        >>> job.get_status()  # 'started'
        >>> result = job.result  # Blocks until complete
    """
    from wepppy.nodb.core import Wepp
    
    wepp = Wepp.getInstance(_join('/wc1/runs', runid))
    
    # Acquire lock for thread-safe mutations
    with wepp.locked():
        wepp._logger.info("Task started")
        
        # Do work
        wepp.some_property = kwargs.get('param1')
        
        # Persist state
        wepp.dump_and_unlock()
    
    return {'success': True, 'data': 'result'}
```

### Common Background Tasks

**Module**: `wepppy.rq.project_rq`

```python
@job('default', timeout=1800)
def run_project_task(runid: str, task_name: str) -> dict:
    """Execute project-level orchestration task.
    
    Tasks:
        - 'prep': Initialize all controllers
        - 'abstract': Watershed delineation
        - 'download_climate': Acquire climate data
        - 'build_inputs': Generate WEPP input files
    """

@job('default', timeout=7200)  
def run_wepp_simulation(runid: str) -> dict:
    """Execute full WEPP simulation.
    
    Steps:
        1. Prep hillslope files
        2. Run hillslope simulations (parallel)
        3. Run watershed simulation
        4. Generate summary outputs
    """
```

## Query Engine API

### MCP Endpoints

**Module**: `wepppy.query_engine.app.mcp`

Full specification: [wepppy/query_engine/README.md](wepppy/query_engine/README.md)

#### Get Run Info
```http
GET /query-engine/mcp/runs/{runid}
Authorization: Bearer {token}

Response:
{
  "data": {
    "id": "copacetic-note",
    "type": "run",
    "attributes": {
      "activated": true,
      "dataset_count": 84
    },
    "links": {
      "catalog": "https://.../catalog",
      "query_execute": "https://.../queries/execute"
    }
  }
}
```

#### Get Catalog
```http
GET /query-engine/mcp/runs/{runid}/catalog?include_fields=true&limit_fields=50
Authorization: Bearer {token}

Response:
{
  "data": [
    {
      "path": "datasets/hillslopes.parquet",
      "size_bytes": 102400,
      "fields": [
        {"name": "wepp_id", "type": "int32"},
        {"name": "soil_loss", "type": "double"}
      ]
    }
  ]
}
```

#### Execute Query
```http
POST /query-engine/mcp/runs/{runid}/queries/execute
Authorization: Bearer {token}
Content-Type: application/json

{
  "datasets": [
    {"path": "datasets/hillslopes.parquet", "alias": "h"}
  ],
  "columns": ["wepp_id", "soil_loss"],
  "filters": [
    {"column": "soil_loss", "operator": ">", "value": 10.0}
  ],
  "aggregations": [
    {"fn": "AVG", "column": "soil_loss", "alias": "avg_loss"}
  ],
  "order_by": [{"column": "soil_loss", "direction": "DESC"}],
  "limit": 100
}

Response:
{
  "data": {
    "type": "query_execute",
    "attributes": {
      "result": {
        "records": [
          {"wepp_id": 42, "avg_loss": 15.3}
        ],
        "row_count": 1,
        "schema": [
          {"name": "wepp_id", "type": "int32"},
          {"name": "avg_loss", "type": "double"}
        ]
      }
    }
  },
  "meta": {
    "execution": {
      "duration_ms": 87
    }
  }
}
```

### Python Query API

**Module**: `wepppy.query_engine.core`

```python
from wepppy.query_engine import run_query, activate_query_engine

# Activate parquet generation for a run
activate_query_engine(runid='/wc1/runs/copacetic-note')

# Execute query
result = run_query(
    runid='copacetic-note',
    datasets=[
        {'path': 'datasets/hillslopes.parquet', 'alias': 'h'}
    ],
    columns=['wepp_id', 'soil_loss'],
    filters=[
        {'column': 'soil_loss', 'operator': '>', 'value': 10.0}
    ],
    limit=100
)

print(result['records'])  # List of dicts
print(result['schema'])   # Field metadata
```

## Common Patterns

### Pattern 1: Create New Run

```python
from wepppy.nodb import RedisPrep
from wepppy.nodb.core import Ron, Climate, Watershed

# Create working directory
runid = 'my-new-run'
wd = RedisPrep.create_working_directory(runid, base_dir='/wc1/runs')

# Initialize controllers
ron = Ron.getInstance(wd)
with ron.locked():
    ron.name = 'My Project'
    ron.dump_and_unlock()

climate = Climate.getInstance(wd)
watershed = Watershed.getInstance(wd)

print(f"Created run: {runid}")
```

### Pattern 2: Load Existing Run

```python
from wepppy.nodb.core import Wepp

# Load from disk (or Redis cache)
wd = '/wc1/runs/existing-run'
wepp = Wepp.getInstance(wd)

# Access state (no lock needed for reads)
print(f"Soil loss: {wepp.avg_soil_loss_tha:.2f} t/ha")

# Mutate state (lock required)
with wepp.locked():
    wepp.phosphorus_opts.surf_runoff = 0.02
    wepp.dump_and_unlock()
```

### Pattern 3: Background Task with Progress

```python
from wepppy.rq import job

@job('default', timeout=3600)
def long_task(runid: str, num_steps: int) -> dict:
    from wepppy.nodb.core import Wepp
    
    wepp = Wepp.getInstance(_join('/wc1/runs', runid))
    
    for i in range(num_steps):
        # Log progress (streams to browser)
        wepp._logger.info(f"Step {i+1}/{num_steps}", extra={
            'progress': (i+1) / num_steps * 100
        })
        
        # Do work
        time.sleep(1)
    
    return {'success': True}
```

### Pattern 4: Rust Integration

```python
# Try Rust, fallback to Python
try:
    from wepppyo3.raster_characteristics import extract_value
    USE_RUST = True
except ImportError:
    USE_RUST = False

def get_raster_value(raster_path, x, y):
    if USE_RUST:
        return extract_value(raster_path, x, y)
    else:
        # Pure Python fallback
        import rasterio
        with rasterio.open(raster_path) as src:
            row, col = src.index(x, y)
            return src.read(1)[row, col]
```

### Pattern 5: WebSocket Status Updates

```javascript
// Front-end controller
class MyController {
    constructor() {
        this.base = controlBase;
        
        // Subscribe to WebSocket channel
        this.base.subscribeToStatus((msg) => {
            if (msg.channel === 'wepp') {
                this.updateProgress(msg.data);
            }
        });
    }
    
    updateProgress(data) {
        document.getElementById('log-panel').innerText += data.message + '\n';
        document.getElementById('progress-bar').value = data.progress || 0;
    }
}
```

### Pattern 6: Query Engine Integration

```python
from wepppy.query_engine import run_query

def get_high_erosion_hillslopes(runid: str, threshold: float):
    """Query hillslopes with soil loss above threshold."""
    result = run_query(
        runid=runid,
        datasets=[
            {'path': 'datasets/hillslopes.parquet', 'alias': 'h'}
        ],
        columns=['wepp_id', 'soil_loss', 'area_ha'],
        filters=[
            {'column': 'soil_loss', 'operator': '>', 'value': threshold}
        ],
        order_by=[
            {'column': 'soil_loss', 'direction': 'DESC'}
        ],
        limit=50
    )
    
    return result['records']
```

## Error Handling

### NoDb Exceptions

```python
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.core import WatershedNotAbstractedError

try:
    with wepp.locked():
        wepp.dump_and_unlock()
except NoDbAlreadyLockedError as e:
    print(f"Lock held by: {e.owner}")
    
try:
    watershed.get_channel_network()
except WatershedNotAbstractedError:
    print("Run watershed abstraction first")
```

### RQ Job Failures

```python
from rq import get_current_job

@job('default', timeout=3600)
def task_with_error_handling(runid: str) -> dict:
    job = get_current_job()
    
    try:
        # Do work
        result = risky_operation()
        return {'success': True, 'result': result}
    except Exception as e:
        # Log to job meta
        job.meta['error'] = str(e)
        job.save_meta()
        
        # Log to run logs
        wepp = Wepp.getInstance(_join('/wc1/runs', runid))
        wepp._logger.error(f"Task failed: {e}", exc_info=True)
        
        raise  # Re-raise for RQ to mark as failed
```

---

**See Also**:
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [AGENTS.md](AGENTS.md) - AI agent coding guide
- [docs/dev-notes/style-guide.md](docs/dev-notes/style-guide.md) - Coding conventions

**Last Updated**: 2025-10-18
