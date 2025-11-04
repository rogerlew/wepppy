# Webhook Integration Strategy for RQ API

> **Context**: Proposal to add webhook notifications to RQ API routes so they can function as standalone APIs independent of the WEPPcloud web interface.

## Executive Summary

**Recommended Approach**: Implement a centralized webhook dispatcher using RQ's built-in callback mechanism with a minimal intervention strategy that avoids touching every route and task function.

**Key Insight**: RQ already supports `on_success`, `on_failure`, and `on_stopped` callbacks. We can leverage this to create a **single webhook dispatcher callback** that all jobs use, eliminating the need to modify individual task functions.

## Current Architecture

### RQ Job Lifecycle
1. **Route Handler** (`wepppy/weppcloud/routes/rq/api/api.py`)
   - Parses request payload
   - Validates inputs
   - Updates NoDb controller state
   - Enqueues job to Redis Queue
   - Returns `job_id` to client

2. **RQ Worker** (`wepppy/rq/project_rq.py`, `wepp_rq.py`, etc.)
   - Executes task function
   - Emits status via `StatusMessenger.publish()`
   - Updates `RedisPrep` timestamps
   - Mutates NoDb controller state

3. **Status Streaming** (separate from job completion)
   - `StatusMessenger` → Redis DB 2 Pub/Sub
   - Go `status2` service → WebSocket
   - Browser consumes via `controlBase.attach_status_stream()`

### Existing Callback Infrastructure

RQ already has a callback system (seen in `hello_world` endpoint):

```python
job = q.enqueue_call(
    hello_world_rq, 
    (runid,), 
    timeout=TIMEOUT,
    on_success=Callback(report_success),
    on_failure=Callback(report_failure, timeout=10),
    on_stopped=Callback(report_stopped, timeout="2m")
)
```

**However**, this is currently only used for debugging. Most production endpoints don't use callbacks at all.

## Proposed Solution: Centralized Webhook Dispatcher

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ API Route Handler                                            │
│  • Parse webhook_url from request payload                    │
│  • Store webhook config in NoDb/Redis                        │
│  • Enqueue job WITH webhook callbacks                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ RQ Worker executes task function (unchanged)                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ RQ Callback (on_success / on_failure / on_stopped)          │
│  • Read webhook config from Redis                            │
│  • POST to client's webhook_url                              │
│  • Retry with exponential backoff                            │
│  • Log delivery status                                       │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Components

#### 1. Webhook Configuration Storage

**Option A: Extend NoDb Controllers** (Preferred)
Add webhook configuration to relevant NoDb classes:

```python
# wepppy/nodb/webhooks.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None  # HMAC signing key
    headers: dict = None  # Custom headers
    retry_count: int = 3
    timeout: int = 30
    
class WebhookMixin:
    """Mixin for NoDb controllers that support webhooks."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._webhook_config: Optional[WebhookConfig] = None
    
    @property
    def webhook_config(self) -> Optional[WebhookConfig]:
        return self._webhook_config
    
    def set_webhook(self, url: str, secret: Optional[str] = None, headers: Optional[dict] = None):
        with self.locked():
            self._webhook_config = WebhookConfig(
                url=url,
                secret=secret,
                headers=headers or {}
            )
            self.dump_and_unlock()
```

**Option B: Redis-Only Storage** (Faster to implement)
Store webhook config in Redis DB 0 with TTL:

```python
# Key pattern: webhook:{runid}:{job_id}
redis_conn.setex(
    f"webhook:{runid}:{job.id}",
    86400,  # 24 hour TTL
    json.dumps({
        "url": webhook_url,
        "secret": webhook_secret,
        "headers": custom_headers
    })
)
```

#### 2. Centralized Webhook Dispatcher

```python
# wepppy/rq/webhook_callbacks.py
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional

import requests
import redis
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.status_messenger import StatusMessenger

logger = logging.getLogger(__name__)


def _get_webhook_config(job_id: str, runid: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve webhook configuration from Redis."""
    try:
        with redis.Redis(**redis_connection_kwargs(RedisDB.Default)) as conn:
            if runid:
                key = f"webhook:{runid}:{job_id}"
            else:
                # Fallback: scan for job_id
                key_pattern = f"webhook:*:{job_id}"
                keys = conn.keys(key_pattern)
                if not keys:
                    return None
                key = keys[0].decode('utf-8')
            
            config_json = conn.get(key)
            if config_json:
                return json.loads(config_json)
    except Exception as exc:
        logger.error(f"Failed to retrieve webhook config for {job_id}: {exc}")
    return None


def _sign_payload(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()


def _deliver_webhook(
    url: str,
    payload: Dict[str, Any],
    secret: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    retry_count: int = 3,
    timeout: int = 30
) -> bool:
    """
    Deliver webhook with retry logic.
    
    Returns:
        True if delivery succeeded, False otherwise.
    """
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    request_headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'WEPPcloud-Webhook/1.0'
    }
    
    if secret:
        signature = _sign_payload(payload_bytes, secret)
        request_headers['X-Webhook-Signature'] = f"sha256={signature}"
    
    if headers:
        request_headers.update(headers)
    
    for attempt in range(retry_count):
        try:
            response = requests.post(
                url,
                data=payload_bytes,
                headers=request_headers,
                timeout=timeout,
                allow_redirects=False
            )
            
            if response.status_code < 300:
                logger.info(f"Webhook delivered to {url} (attempt {attempt + 1})")
                return True
            
            logger.warning(
                f"Webhook delivery failed: {response.status_code} "
                f"(attempt {attempt + 1}/{retry_count})"
            )
            
        except requests.exceptions.RequestException as exc:
            logger.warning(
                f"Webhook delivery error: {exc} "
                f"(attempt {attempt + 1}/{retry_count})"
            )
        
        if attempt < retry_count - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    logger.error(f"Webhook delivery failed after {retry_count} attempts")
    return False


def webhook_on_success(job: Job, connection: redis.Redis, result: Any, *args, **kwargs):
    """Callback invoked when RQ job completes successfully."""
    config = _get_webhook_config(job.id)
    if not config:
        return result
    
    # Extract runid from job args if available
    runid = None
    if job.args and len(job.args) > 0:
        runid = job.args[0]
    
    payload = {
        'event': 'job.success',
        'job_id': job.id,
        'runid': runid,
        'timestamp': time.time(),
        'result': result if isinstance(result, (dict, list, str, int, float, bool, type(None))) else str(result)
    }
    
    success = _deliver_webhook(
        url=config['url'],
        payload=payload,
        secret=config.get('secret'),
        headers=config.get('headers'),
        retry_count=config.get('retry_count', 3),
        timeout=config.get('timeout', 30)
    )
    
    if success and runid:
        StatusMessenger.publish(
            f'{runid}:webhook',
            f'Webhook delivered for job {job.id}'
        )
    
    return result


def webhook_on_failure(job: Job, connection: redis.Redis, type, value, traceback):
    """Callback invoked when RQ job fails."""
    config = _get_webhook_config(job.id)
    if not config:
        return
    
    runid = None
    if job.args and len(job.args) > 0:
        runid = job.args[0]
    
    payload = {
        'event': 'job.failure',
        'job_id': job.id,
        'runid': runid,
        'timestamp': time.time(),
        'error': {
            'type': str(type),
            'message': str(value),
            'traceback': str(traceback)
        }
    }
    
    _deliver_webhook(
        url=config['url'],
        payload=payload,
        secret=config.get('secret'),
        headers=config.get('headers'),
        retry_count=config.get('retry_count', 3),
        timeout=config.get('timeout', 30)
    )


def webhook_on_stopped(job: Job, connection: redis.Redis):
    """Callback invoked when RQ job is stopped/cancelled."""
    config = _get_webhook_config(job.id)
    if not config:
        return
    
    runid = None
    if job.args and len(job.args) > 0:
        runid = job.args[0]
    
    payload = {
        'event': 'job.stopped',
        'job_id': job.id,
        'runid': runid,
        'timestamp': time.time()
    }
    
    _deliver_webhook(
        url=config['url'],
        payload=payload,
        secret=config.get('secret'),
        headers=config.get('headers'),
        retry_count=config.get('retry_count', 3),
        timeout=config.get('timeout', 30)
    )
```

#### 3. Route Handler Modifications (Minimal Touch)

Create a helper function to wrap job enqueuing:

```python
# wepppy/weppcloud/routes/rq/api/_webhook_utils.py
from typing import Any, Callable, Dict, Optional, Tuple

import redis
from rq import Queue, Callback
from flask import request

from wepppy.rq.webhook_callbacks import (
    webhook_on_success,
    webhook_on_failure, 
    webhook_on_stopped
)
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


def enqueue_with_webhook(
    queue: Queue,
    func: Callable,
    args: Tuple,
    timeout: int,
    runid: str,
    payload: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Enqueue RQ job with optional webhook callbacks.
    
    Reads webhook configuration from request payload and attaches
    callbacks if webhook_url is provided.
    
    Args:
        queue: RQ Queue instance
        func: Task function to execute
        args: Arguments for task function
        timeout: Job timeout in seconds
        runid: Run identifier
        payload: Parsed request payload (from parse_request_payload)
    
    Returns:
        RQ Job instance
    """
    if payload is None:
        payload = {}
    
    webhook_url = payload.get('webhook_url')
    webhook_secret = payload.get('webhook_secret')
    webhook_headers_raw = payload.get('webhook_headers')
    
    # Parse webhook headers if provided
    webhook_headers = None
    if webhook_headers_raw:
        if isinstance(webhook_headers_raw, dict):
            webhook_headers = webhook_headers_raw
        elif isinstance(webhook_headers_raw, str):
            try:
                webhook_headers = json.loads(webhook_headers_raw)
            except json.JSONDecodeError:
                pass
    
    # Enqueue without callbacks if no webhook configured
    if not webhook_url:
        return queue.enqueue_call(func, args, timeout=timeout)
    
    # Store webhook config in Redis
    with redis.Redis(**redis_connection_kwargs(RedisDB.Default)) as conn:
        # Pre-generate job ID to store config before enqueueing
        job = queue.enqueue_call(
            func, 
            args, 
            timeout=timeout,
            on_success=Callback(webhook_on_success),
            on_failure=Callback(webhook_on_failure, timeout=10),
            on_stopped=Callback(webhook_on_stopped, timeout=10)
        )
        
        # Store webhook config
        config = {
            'url': webhook_url,
            'secret': webhook_secret,
            'headers': webhook_headers or {}
        }
        conn.setex(
            f"webhook:{runid}:{job.id}",
            86400,  # 24 hour TTL
            json.dumps(config)
        )
    
    return job
```

#### 4. Update Individual Routes (Surgical Changes)

Example transformation for `api_build_landuse`:

**Before:**
```python
with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = q.enqueue_call(build_landuse_rq, (runid,), timeout=TIMEOUT)
    prep.set_rq_job_id('build_landuse_rq', job.id)
```

**After:**
```python
from wepppy.weppcloud.routes.rq.api._webhook_utils import enqueue_with_webhook

with _redis_conn() as redis_conn:
    q = Queue(connection=redis_conn)
    job = enqueue_with_webhook(
        queue=q,
        func=build_landuse_rq,
        args=(runid,),
        timeout=TIMEOUT,
        runid=runid,
        payload=payload  # Already parsed via parse_request_payload
    )
    prep.set_rq_job_id('build_landuse_rq', job.id)
```

**Key Benefits:**
- Only 3 lines changed per route
- No changes to RQ task functions
- Backward compatible (works without webhook_url)
- Centralized webhook logic

## Regression Prevention Strategy

### 1. Feature Flag
Add environment variable to enable/disable webhooks:

```python
# wepppy/config/webhook_settings.py
import os

WEBHOOKS_ENABLED = os.environ.get('WEPPCLOUD_WEBHOOKS_ENABLED', 'false').lower() == 'true'
WEBHOOK_TIMEOUT = int(os.environ.get('WEPPCLOUD_WEBHOOK_TIMEOUT', '30'))
WEBHOOK_RETRY_COUNT = int(os.environ.get('WEPPCLOUD_WEBHOOK_RETRY_COUNT', '3'))
```

Guard webhook logic:
```python
if WEBHOOKS_ENABLED and webhook_url:
    # Attach callbacks
    pass
else:
    # Original enqueue path
    pass
```

### 2. Phased Rollout

**Phase 1: Infrastructure** (Week 1)
- Implement `webhook_callbacks.py`
- Implement `_webhook_utils.py`
- Add feature flag
- Write unit tests

**Phase 2: Pilot Routes** (Week 2)
- Convert 2-3 low-traffic routes:
  - `api_build_landuse`
  - `api_build_soils`
  - `api_build_climate`
- Test with staging environment
- Monitor webhook delivery logs

**Phase 3: Main Routes** (Week 3)
- Convert remaining routes:
  - `api_run_wepp`
  - `api_run_ash`
  - `api_run_omni`
  - `fetch_dem_and_build_channels`
  - `api_build_subcatchments_and_abstract_watershed`

**Phase 4: Edge Cases** (Week 4)
- `api_fork`
- `api_archive` / `api_restore_archive`
- Batch operations

### 3. Testing Strategy

#### Unit Tests
```python
# tests/weppcloud/routes/rq/test_webhook_integration.py
import json
import pytest
from unittest.mock import Mock, patch, call
import responses

from wepppy.rq.webhook_callbacks import (
    webhook_on_success,
    webhook_on_failure,
    _deliver_webhook,
    _sign_payload
)


@responses.activate
def test_webhook_on_success_delivers_payload():
    """Verify webhook delivers correct payload on job success."""
    responses.add(
        responses.POST,
        'https://example.com/webhook',
        json={'received': True},
        status=200
    )
    
    job = Mock()
    job.id = 'test-job-123'
    job.args = ('test-runid',)
    
    with patch('wepppy.rq.webhook_callbacks._get_webhook_config') as mock_config:
        mock_config.return_value = {
            'url': 'https://example.com/webhook',
            'secret': 'test-secret'
        }
        
        result = webhook_on_success(job, None, {'status': 'complete'})
        
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        payload = json.loads(request.body)
        
        assert payload['event'] == 'job.success'
        assert payload['job_id'] == 'test-job-123'
        assert payload['runid'] == 'test-runid'
        assert 'X-Webhook-Signature' in request.headers


@responses.activate
def test_webhook_delivery_retries_on_failure():
    """Verify webhook retries on transient failures."""
    responses.add(
        responses.POST,
        'https://example.com/webhook',
        json={'error': 'server error'},
        status=500
    )
    
    success = _deliver_webhook(
        url='https://example.com/webhook',
        payload={'test': 'data'},
        retry_count=3,
        timeout=5
    )
    
    assert not success
    assert len(responses.calls) == 3  # Retried 3 times


def test_webhook_signature_matches_expected():
    """Verify HMAC signature matches expected format."""
    payload = b'{"test": "data"}'
    secret = 'my-secret-key'
    
    signature = _sign_payload(payload, secret)
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    assert signature == expected
```

#### Integration Tests
```python
# tests/integration/test_webhook_e2e.py
import json
import pytest
import responses
from flask import Flask

from wepppy.weppcloud.app import create_app
from wepppy.nodb.core import Ron


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@responses.activate
def test_build_landuse_webhook_delivery(app, tmp_path):
    """End-to-end test: API call → job execution → webhook delivery."""
    
    # Setup webhook receiver
    webhook_calls = []
    
    def webhook_handler(request):
        webhook_calls.append(json.loads(request.body))
        return (200, {}, json.dumps({'received': True}))
    
    responses.add_callback(
        responses.POST,
        'https://example.com/webhook',
        callback=webhook_handler
    )
    
    # Create test run
    runid = 'test-webhook-run'
    config = 'test.cfg'
    wd = tmp_path / runid
    wd.mkdir()
    
    # Initialize Ron
    ron = Ron(str(wd), config)
    
    with app.test_client() as client:
        # Make API call with webhook
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
        assert 'job_id' in job_data
        
        # Wait for job completion (in test, this should be fast)
        # ... job execution logic ...
        
        # Verify webhook was called
        assert len(webhook_calls) == 1
        webhook_payload = webhook_calls[0]
        
        assert webhook_payload['event'] == 'job.success'
        assert webhook_payload['job_id'] == job_data['job_id']
        assert webhook_payload['runid'] == runid
```

#### Smoke Tests
Use existing playback infrastructure to verify no regressions:

```bash
# Run playback tests with webhooks disabled (default)
wctl run-pytest tests/profile_recorder/test_playback_session.py

# Run playback tests with webhooks enabled
WEPPCLOUD_WEBHOOKS_ENABLED=true wctl run-pytest tests/profile_recorder/test_playback_session.py
```

### 4. Monitoring & Observability

#### Webhook Delivery Metrics
```python
# wepppy/rq/webhook_callbacks.py (additions)
from wepppy.nodb.status_messenger import StatusMessenger

# After delivery attempt
StatusMessenger.publish(
    'webhooks:telemetry',
    json.dumps({
        'job_id': job.id,
        'runid': runid,
        'url': url,
        'status': 'success' if success else 'failed',
        'attempts': attempt + 1,
        'timestamp': time.time()
    })
)
```

#### Dashboard Integration
Extend RQ dashboard to show webhook status:

```python
# wepppy/weppcloud/routes/rq/job_dashboard/routes.py
@job_dashboard_bp.route('/job/<job_id>/webhook')
def get_job_webhook_status(job_id):
    """Fetch webhook delivery status for a job."""
    with redis.Redis(**redis_connection_kwargs(RedisDB.Default)) as conn:
        # Scan for webhook config
        keys = conn.keys(f'webhook:*:{job_id}')
        if not keys:
            return jsonify({'webhook_configured': False})
        
        config_json = conn.get(keys[0])
        config = json.loads(config_json) if config_json else {}
        
        return jsonify({
            'webhook_configured': True,
            'url': config.get('url'),
            'delivery_status': 'pending'  # TODO: track status
        })
```

## API Contract

### Request Format
```json
POST /runs/{runid}/{config}/rq/api/build_landuse
{
  "landuse_mode": "1",
  "landuse_db": "nlcd",
  "webhook_url": "https://example.com/webhooks/weppcloud",
  "webhook_secret": "your-signing-key",
  "webhook_headers": {
    "X-Custom-Header": "value"
  }
}
```

### Webhook Payload (Success)
```json
{
  "event": "job.success",
  "job_id": "abc123-def456",
  "runid": "test-run-2024",
  "timestamp": 1704067200.0,
  "result": {
    "status": "complete",
    "details": "..."
  }
}
```

### Webhook Payload (Failure)
```json
{
  "event": "job.failure",
  "job_id": "abc123-def456",
  "runid": "test-run-2024",
  "timestamp": 1704067200.0,
  "error": {
    "type": "ValueError",
    "message": "Invalid landuse mode",
    "traceback": "..."
  }
}
```

### Webhook Headers
```
POST /webhooks/weppcloud HTTP/1.1
Host: example.com
Content-Type: application/json
User-Agent: WEPPcloud-Webhook/1.0
X-Webhook-Signature: sha256=abc123...
X-Custom-Header: value
```

### Signature Verification (Client Side)
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature on client side."""
    if not signature.startswith('sha256='):
        return False
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    received = signature.replace('sha256=', '')
    return hmac.compare_digest(expected, received)
```

## Security Considerations

1. **URL Validation**: Only allow HTTPS URLs (except localhost for testing)
2. **Secret Storage**: Never log webhook secrets
3. **Rate Limiting**: Prevent webhook spam
4. **Timeout**: Enforce max webhook delivery time
5. **SSRF Protection**: Validate webhook URLs against internal network ranges

```python
from urllib.parse import urlparse

def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL for security."""
    parsed = urlparse(url)
    
    # Require HTTPS (except localhost)
    if parsed.scheme not in ('https', 'http'):
        return False
    if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1'):
        return False
    
    # Block internal networks
    if parsed.hostname in ('10.', '192.168.', '172.'):
        return False
    
    return True
```

## Migration Checklist

- [ ] Implement `webhook_callbacks.py` module
- [ ] Implement `_webhook_utils.py` helper
- [ ] Add feature flag configuration
- [ ] Write unit tests for webhook delivery
- [ ] Write integration tests for route handlers
- [ ] Update 3 pilot routes
- [ ] Test pilot routes in staging
- [ ] Update remaining routes (batch operation)
- [ ] Update API documentation
- [ ] Add webhook delivery monitoring
- [ ] Update RQ dashboard to show webhook status
- [ ] Security audit (URL validation, SSRF protection)
- [ ] Performance testing (webhook timeout impact)
- [ ] Deploy to production with feature flag disabled
- [ ] Enable feature flag for beta users
- [ ] Full rollout

## Estimated Effort

- **Infrastructure**: 2-3 days
- **Pilot Routes**: 1-2 days
- **Full Migration**: 2-3 days (automated with script)
- **Testing**: 2-3 days
- **Documentation**: 1 day
- **Total**: ~2 weeks

## Alternative Approaches Considered

### 1. Modify Every RQ Task Function
**Rejected**: Would require touching 30+ functions, high regression risk.

### 2. Add Webhook Endpoint Separate from RQ
**Rejected**: Would duplicate job status tracking, breaks single source of truth.

### 3. Use Redis Pub/Sub for Webhook Triggers
**Possible Future Enhancement**: Could batch webhook deliveries, but adds complexity.

### 4. External Webhook Service (e.g., Svix, Hookdeck)
**Future Consideration**: Commercial SaaS for webhook reliability, but adds dependency.

## Conclusion

The proposed centralized webhook dispatcher leverages RQ's existing callback infrastructure to add webhook support with minimal code changes. The phased rollout strategy and comprehensive testing plan minimize regression risk while enabling WEPPcloud APIs to function independently of the web interface.

**Next Steps**:
1. Review and approve this design
2. Create work package in `docs/work-packages/`
3. Implement infrastructure components
4. Begin pilot phase with 3 routes
5. Full rollout after successful pilot
