# WEPPpy Microservices

> Lightweight Starlette-based services for file browsing, elevation queries, and GDAL operations within the wepppy ecosystem.

> **See also:** [AGENTS.md](../../AGENTS.md) for microservices architecture, deployment topology, and Redis integration notes.

## Overview

This directory contains lightweight microservices built with Starlette that provide specialized functionality for the WEPPcloud application. These services are designed to be fast, focused, and independently deployable, handling tasks that benefit from dedicated processes outside the main Flask application.

**Key characteristics:**
- **Async-first**: Built on Starlette/ASGI for high-concurrency scenarios
- **Run-scoped**: Services operate within the context of specific WEPPcloud runs
- **Self-contained**: Minimal dependencies; can be deployed independently
- **Fast**: Optimized for specific tasks (file serving, elevation lookups, GDAL operations)

**Separation from `webservices/`:**
- `wepppy/microservices/`: Lightweight Starlette services (file browsing, elevation queries)
- `wepppy/webservices/`: Heavier Flask/FastAPI services (climate data, raster servers, D-Tale integration)

## Services

### Browse Microservice

**File**: `browse.py`  
**Documentation**: [README.browse.md](README.browse.md)

Provides filesystem browsing, file downloads, and GDAL metadata extraction for run directories.

**Key endpoints:**
- `GET /browse/<path>` - List directory contents or download files
- `GET /gdalinfo/<path>` - Extract raster metadata via GDAL

**Use cases:**
- Browsing run output files through the web interface
- Downloading simulation results
- Inspecting GeoTIFF metadata without GDAL client-side

### Elevation Query Service

**File**: `elevationquery.py`

Run-scoped elevation tile server that provides on-demand DEM queries for watershed delineation and analysis.

**Key features:**
- Serves elevation data from configured DEM sources
- Mirrors legacy elevation service API for backward compatibility
- Custom exception handlers for transparent error reporting
- Starlette-based for high throughput

**Typical usage:**
```python
# Called by watershed delineation modules
response = requests.get(
    f"http://elevationquery:8000/runs/{runid}/{config}/elevation",
    params={"lng": -116.5, "lat": 43.2}
)
elevation = response.json()["elevation"]
```

**Deployment**: Runs as a separate container in Docker Compose stacks; see `docker/docker-compose.dev.yml`.

## Architecture

### Request Flow

1. **Client request** → WEPPcloud Flask app
2. **Flask delegates** → Microservice via internal HTTP
3. **Microservice** processes (file I/O, GDAL, elevation lookup)
4. **Response** returned to Flask → Client

### Integration with WEPPcloud

Microservices integrate with the main application through:
- **Internal networking**: Services communicate via Docker network or localhost
- **Run context**: Services accept `runid` and `config` parameters to locate run directories
- **Shared filesystem**: Access to `/geodata/weppcloud_runs` for run data
- **Error handling**: Structured JSON errors compatible with frontend expectations

## Development

### Running Locally

Microservices are included in the Docker Compose development stack:

```bash
cd docker
docker compose -f docker-compose.dev.yml up
```

Individual services can be tested directly:

```bash
# From within the dev container
cd /workdir/wepppy/wepppy/microservices
uvicorn browse:app --host 0.0.0.0 --port 8001 --reload
```

### Adding a New Microservice

1. **Create the module**: Add `myservice.py` with a Starlette app
   ```python
   from starlette.applications import Starlette
   from starlette.responses import JSONResponse
   from starlette.routing import Route
   
   async def my_endpoint(request):
       return JSONResponse({"status": "ok"})
   
   app = Starlette(routes=[
       Route("/myservice", my_endpoint),
   ])
   ```

2. **Add to Docker Compose**: Register in `docker/docker-compose.dev.yml`
   ```yaml
   myservice:
     build:
       context: ..
       dockerfile: docker/Dockerfile.dev
     command: uvicorn wepppy.microservices.myservice:app --host 0.0.0.0 --port 8002
     volumes:
       - ../wepppy:/workdir/wepppy
       - geodata:/geodata
   ```

3. **Update routing**: Configure Flask to proxy requests to the new service

4. **Document**: Add description to this README and create dedicated docs if complex

### Testing

Test microservices independently before integration:

```bash
# Unit tests
wctl run-pytest tests/microservices/

# Manual testing with curl
curl http://localhost:8001/browse/runs/abc123/tahoe
```

### Common Patterns

**Run-scoped endpoints:**
```python
from starlette.routing import Route

async def run_scoped_handler(request):
    runid = request.path_params['runid']
    config = request.path_params['config']
    # Access run directory
    wd = f"/geodata/weppcloud_runs/{runid}/{config}"
    # ...
    
Route("/runs/{runid}/{config}/resource", run_scoped_handler)
```

**Error handling:**
```python
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException

async def my_handler(request):
    try:
        # Process request
        pass
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )
```

## Deployment

### Docker

Microservices run as separate containers in production:

```bash
docker compose -f docker-compose.prod.yml up -d
```

**Key considerations:**
- **Health checks**: Implement `/health` endpoints for load balancer probes
- **Logging**: Structured logs to stdout for container log aggregation
- **Resource limits**: Set memory/CPU limits in Docker Compose
- **Networking**: Use internal Docker networks; only expose via reverse proxy

### Environment Variables

Common configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `WEPPCLOUD_RUNS_DIR` | `/geodata/weppcloud_runs` | Base directory for run storage |
| `GEODATA_DIR` | `/geodata` | Geospatial data mount point |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Troubleshooting

**Service not responding:**
- Check Docker container status: `docker ps`
- Review logs: `docker logs <container_name>`
- Verify network connectivity between Flask app and microservice

**File not found errors:**
- Confirm `/geodata` mount is accessible
- Verify run directory exists and permissions are correct
- Check `runid` and `config` parameters are correct

**GDAL errors:**
- Ensure GDAL binaries are installed in container
- Verify raster files are valid (not corrupted)
- Check file permissions and path resolution

## Further Reading

- [README.browse.md](README.browse.md) - Detailed browse service documentation
- [AGENTS.md](../../AGENTS.md) - Microservices architecture and patterns
- [docker/README.md](../../docker/README.md) - Docker deployment guide
- [wepppy/webservices/](../webservices/) - Related Flask/FastAPI services
- [Starlette Documentation](https://www.starlette.io/) - Framework reference

## Credits

Built on Starlette ASGI framework for high-performance async Python services.

License: BSD-3 Clause (see [../../license.txt](../../license.txt))
