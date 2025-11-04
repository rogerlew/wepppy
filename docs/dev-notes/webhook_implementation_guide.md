# Webhook Implementation Guide

> **Quick reference for implementing webhook support in RQ API routes**

## TL;DR

Add webhook callbacks to any RQ route with 3 simple changes:

```python
# Before
with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = q.enqueue_call(build_landuse_rq, (runid,), timeout=TIMEOUT)

# After
from wepppy.weppcloud.routes.rq.api._webhook_utils import enqueue_with_webhook

with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = enqueue_with_webhook(q, build_landuse_rq, (runid,), TIMEOUT, runid, payload)
```

**Zero changes required** to RQ task functions.

## Route Inventory

Total routes requiring updates: **~25-30**

### Core Workflow Routes (High Priority)
- ✅ `fetch_dem_and_build_channels` - DEM acquisition + channel delineation
- ✅ `api_set_outlet` - Outlet placement
- ✅ `api_build_subcatchments_and_abstract_watershed` - Watershed abstraction
- ✅ `api_build_landuse` - Landuse overlay
- ✅ `api_build_treatments` - Treatment application
- ✅ `api_build_soils` - Soil parameter generation
- ✅ `api_build_climate` - Climate forcing
- ✅ `api_run_wepp` - WEPP execution
- ✅ `api_post_dss_export_rq` - DSS export

### Model Execution Routes
- ✅ `api_run_ash` - Ash transport modeling
- ✅ `api_run_omni` - Omni scenario runner
- ✅ `api_run_omni_contrasts` - Omni contrast analysis
- ✅ `api_run_debris_flow` - Debris flow prediction
- ✅ `api_run_rhem` - RHEM hillslope erosion
- ✅ `api_rap_ts_acquire` - RAP timeseries acquisition

### Utility Routes
- ✅ `api_fork` - Project forking
- ✅ `api_archive` - Project archival
- ✅ `api_restore_archive` - Archive restoration
- ✅ `api_run_batch` - Batch runner (admin only)

### Special Cases
- ⚠️ `build_landuse_and_soils` - UUID-based (no runid), different pattern
- ⚠️ `hello_world` - Debug endpoint, already has callbacks

## File Change Summary

### New Files
```
wepppy/rq/webhook_callbacks.py              # Core webhook dispatcher
wepppy/weppcloud/routes/rq/api/_webhook_utils.py  # Helper for routes
wepppy/config/webhook_settings.py           # Configuration
tests/weppcloud/routes/rq/test_webhook_integration.py  # Unit tests
tests/integration/test_webhook_e2e.py       # Integration tests
docs/api-specs/webhook_api.md               # API documentation
```

### Modified Files
```
wepppy/weppcloud/routes/rq/api/api.py       # All route handlers (~25 functions)
docker/docker-compose.dev.yml               # Add WEPPCLOUD_WEBHOOKS_ENABLED
docker/docker-compose.prod.yml              # Add WEPPCLOUD_WEBHOOKS_ENABLED
docker/requirements-uv.txt                  # Add 'requests' if not present
```

## Step-by-Step Migration

### Step 1: Route Pattern Analysis

Most routes follow one of two patterns:

**Pattern A: Simple Enqueue**
```python
with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = q.enqueue_call(some_rq_function, (runid,), timeout=TIMEOUT)
    prep.set_rq_job_id('some_rq_function', job.id)
```

**Pattern B: Enqueue with kwargs**
```python
with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = q.enqueue_call(
        some_rq_function,
        (runid,),
        kwargs={'payload': data},
        timeout=TIMEOUT
    )
    prep.set_rq_job_id('some_rq_function', job.id)
```

### Step 2: Create Batch Migration Script

```python
#!/usr/bin/env python3
# scripts/migrate_routes_to_webhooks.py
import re
from pathlib import Path

API_FILE = Path('wepppy/weppcloud/routes/rq/api/api.py')

# Pattern to match enqueue_call
PATTERN_A = re.compile(
    r'job = q\.enqueue_call\((\w+), \(([^)]+)\), timeout=(\w+)\)',
    re.MULTILINE
)

PATTERN_B = re.compile(
    r'job = q\.enqueue_call\(\s*(\w+),\s*\(([^)]+)\),\s*kwargs=\{([^}]+)\},\s*timeout=(\w+)\s*\)',
    re.MULTILINE | re.DOTALL
)

def migrate_pattern_a(match):
    func_name = match.group(1)
    args = match.group(2)
    timeout = match.group(3)
    
    # Extract runid (first arg)
    runid = args.split(',')[0].strip()
    
    return (
        f'job = enqueue_with_webhook(\n'
        f'        queue=q,\n'
        f'        func={func_name},\n'
        f'        args=({args}),\n'
        f'        timeout={timeout},\n'
        f'        runid={runid},\n'
        f'        payload=payload\n'
        f'    )'
    )

def migrate_pattern_b(match):
    func_name = match.group(1)
    args = match.group(2)
    kwargs_content = match.group(3)
    timeout = match.group(4)
    
    runid = args.split(',')[0].strip()
    
    return (
        f'job = enqueue_with_webhook(\n'
        f'        queue=q,\n'
        f'        func={func_name},\n'
        f'        args=({args}),\n'
        f'        kwargs={{{kwargs_content}}},\n'
        f'        timeout={timeout},\n'
        f'        runid={runid},\n'
        f'        payload=payload\n'
        f'    )'
    )

def main():
    content = API_FILE.read_text()
    
    # Add import at top
    if 'from wepppy.weppcloud.routes.rq.api._webhook_utils import enqueue_with_webhook' not in content:
        import_line = 'from wepppy.weppcloud.routes.rq.api._webhook_utils import enqueue_with_webhook\n'
        # Insert after other imports
        content = content.replace(
            'from ..._common import roles_required, parse_request_payload\n',
            'from ..._common import roles_required, parse_request_payload\n' + import_line
        )
    
    # Migrate Pattern A
    content = PATTERN_A.sub(migrate_pattern_a, content)
    
    # Migrate Pattern B
    content = PATTERN_B.sub(migrate_pattern_b, content)
    
    # Write back
    API_FILE.write_text(content)
    print(f'✅ Migrated {API_FILE}')

if __name__ == '__main__':
    main()
```

### Step 3: Function-by-Function Transformation

**Example: `api_build_landuse`**

```diff
@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_landuse', methods=['POST'])
def api_build_landuse(runid, config):
    try:
        wd = get_wd(runid)
        landuse = Landuse.getInstance(wd)

        payload = parse_request_payload(
            request,
            boolean_fields=(
                "checkbox_burn_shrubs",
                "checkbox_burn_grass",
                "burn_shrubs",
                "burn_grass",
            ),
        )
        
        # ... validation logic ...
        
        prep = RedisPrep.getInstance(wd)
        prep.remove_timestamp(TaskEnum.build_landuse)

        with _redis_conn() as redis_conn:
            q = Queue(connection=redis_conn)
-           job = q.enqueue_call(build_landuse_rq, (runid,), timeout=TIMEOUT)
+           job = enqueue_with_webhook(
+               queue=q,
+               func=build_landuse_rq,
+               args=(runid,),
+               timeout=TIMEOUT,
+               runid=runid,
+               payload=payload
+           )
            prep.set_rq_job_id('build_landuse_rq', job.id)
        
    except Exception as e:
        if isinstance(e, WatershedNotAbstractedError):
            return exception_factory(e.__name__, e.__doc__, runid=runid)
        else:
            return exception_factory('Building Landuse Failed', runid=runid)
        
    return jsonify({'Success': True, 'job_id': job.id})
```

### Step 4: Handle Special Cases

**UUID-based route (`build_landuse_and_soils`)**:
```python
# This route doesn't have runid, use UUID as identifier
job = enqueue_with_webhook(
    queue=q,
    func=land_and_soil_rq,
    args=(None, extent, cfg, nlcd_db, ssurgo_db),
    timeout=TIMEOUT,
    runid=uuid,  # Use UUID as runid substitute
    payload=data
)
```

**Routes without payload parsing**:
```python
# Manually construct payload if parse_request_payload not called
payload = {
    'webhook_url': request.form.get('webhook_url'),
    'webhook_secret': request.form.get('webhook_secret')
}

job = enqueue_with_webhook(
    queue=q,
    func=some_rq_function,
    args=(runid,),
    timeout=TIMEOUT,
    runid=runid,
    payload=payload
)
```

## Validation Checklist

After migration, verify each route:

- [ ] Import added: `from wepppy.weppcloud.routes.rq.api._webhook_utils import enqueue_with_webhook`
- [ ] `enqueue_call` replaced with `enqueue_with_webhook`
- [ ] All required parameters passed: `queue`, `func`, `args`, `timeout`, `runid`, `payload`
- [ ] `runid` parameter matches first arg in `args` tuple
- [ ] `payload` variable exists (from `parse_request_payload` or manual construction)
- [ ] Existing error handling unchanged
- [ ] Return statement unchanged

## Testing Each Route

### Manual Test Template

```bash
# 1. Enable webhooks
export WEPPCLOUD_WEBHOOKS_ENABLED=true

# 2. Start webhook receiver (use ngrok or requestbin.com)
ngrok http 5000

# 3. Make API call with webhook
curl -X POST http://localhost:8000/runs/test-run/dev.cfg/rq/api/build_landuse \
  -H "Content-Type: application/json" \
  -d '{
    "landuse_mode": "1",
    "landuse_db": "nlcd",
    "webhook_url": "https://your-ngrok-url.ngrok.io/webhook",
    "webhook_secret": "test-secret"
  }'

# 4. Wait for job completion
# 5. Verify webhook received at ngrok dashboard
```

### Automated Test Template

```python
@responses.activate
def test_api_build_landuse_webhook(tmp_path):
    """Verify webhook delivery for build_landuse endpoint."""
    webhook_payloads = []
    
    def capture_webhook(request):
        webhook_payloads.append(json.loads(request.body))
        return (200, {}, '{"received": true}')
    
    responses.add_callback(
        responses.POST,
        'https://example.com/webhook',
        callback=capture_webhook
    )
    
    # Setup test run
    runid = 'test-webhook'
    config = 'test.cfg'
    wd = tmp_path / runid
    wd.mkdir()
    
    # ... initialize NoDb controllers ...
    
    with app.test_client() as client:
        response = client.post(
            f'/runs/{runid}/{config}/rq/api/build_landuse',
            json={
                'landuse_mode': '1',
                'landuse_db': 'nlcd',
                'webhook_url': 'https://example.com/webhook',
                'webhook_secret': 'test-secret'
            }
        )
        
        assert response.status_code == 200
        job_data = response.get_json()
        
        # Wait for job + webhook delivery
        # ...
        
        assert len(webhook_payloads) == 1
        assert webhook_payloads[0]['event'] == 'job.success'
        assert webhook_payloads[0]['runid'] == runid
```

## Rollback Plan

If issues arise, rollback is simple:

```bash
# 1. Disable webhooks via environment variable
export WEPPCLOUD_WEBHOOKS_ENABLED=false

# 2. Restart services
wctl restart weppcloud
wctl restart rq-worker

# 3. (Optional) Revert code changes
git revert <commit-sha>
```

The `enqueue_with_webhook` helper gracefully falls back to standard `enqueue_call` when webhooks are disabled or not configured.

## Performance Impact

**Expected overhead per job**:
- Webhook config storage: ~1ms (Redis write)
- Webhook delivery: ~100-500ms (HTTP POST, async from job execution)
- Total impact on job completion: ~0-5% (callbacks run after job finishes)

**Mitigation**:
- Webhook delivery runs in separate RQ callback
- Does not block job execution
- Configurable timeout (default 30s)
- Exponential backoff on retries

## Documentation Updates

After migration, update:

1. **API Documentation** (`docs/api-specs/`):
   - Add webhook parameters to each endpoint
   - Document webhook payload schemas
   - Add signature verification examples

2. **README** (`readme.md`):
   - Add webhook section to API usage guide
   - Document environment variables

3. **OpenAPI Spec** (if exists):
   - Add `webhook_url`, `webhook_secret`, `webhook_headers` to request schemas

4. **Frontend Controllers** (if webhook UI needed):
   - Add webhook configuration inputs to relevant controls
   - Display webhook delivery status in job dashboard

## Success Criteria

Migration is complete when:

- [ ] All 25-30 routes use `enqueue_with_webhook`
- [ ] Unit tests pass (90%+ coverage for webhook module)
- [ ] Integration tests pass (E2E webhook delivery verified)
- [ ] Playback tests pass (no regressions with webhooks disabled)
- [ ] Manual testing confirms webhook delivery for 5 representative routes
- [ ] Documentation updated
- [ ] Feature flag deployed to production (disabled initially)
- [ ] Monitoring dashboard shows webhook metrics
- [ ] Beta users successfully use webhook API
