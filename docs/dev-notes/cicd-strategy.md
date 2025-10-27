# CI/CD Strategy: Agent-Driven Development Pipeline Vision Document

> **Living Document** – Comprehensive guide from current state (haphazard patching) to full CI/CD pipeline with automated testing gates, GitHub runners, and three-tier deployment (dev → test-production → production).

## Authorship
**AI agents maintain this document. Update when CI/CD infrastructure, test coverage, or deployment procedures change.**

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Target Architecture](#target-architecture)
3. [GitHub Runners Infrastructure](#github-runners-infrastructure)
4. [Testing Strategy & Coverage Gaps](#testing-strategy--coverage-gaps)
5. [CI Pipeline Design](#ci-pipeline-design)
6. [Deployment Environments](#deployment-environments)
7. [Release Process](#release-process)
8. [Rollback & Safety](#rollback--safety)
9. [Agent-Driven Development Integration](#agent-driven-development-integration)
10. [Implementation Roadmap](#implementation-roadmap)
11. [Operational Playbooks](#operational-playbooks)

---

## Current State Assessment

### Deployment Architecture (2025-10-26)

| Environment | Host | Domain | Deployment | Gating Criteria | Status |
|-------------|------|--------|------------|-----------------|--------|
| **Development** | forest.bearhive.internal | wc.bearhive.duckdns.org | docker-compose.dev.yml | None - rapid iteration | ✅ Active |
| **Test Production** | forest1.bearhive.internal | wc-prod.bearhive.duckdns.org | docker-compose.prod.yml | CI passes - auto-deploy | ✅ Active |
| **Production** | wepp1 | wepp.cloud | systemctl at commit 05ffcab3d7fa5b77266f9cfa4ec1e8d41f543877 | **Functional validation** (see below) | ✅ Active |

**Key Distinction:**
- **Test-prod**: No hurdles - deploys automatically when CI passes
- **Production**: Requires comprehensive functional validation before promotion

### Current Deployment Process

**Reality:** Haphazard patching and manual deployments

```bash
# Typical deployment today (from commit logs):
# 1. Make changes on dev machine
# 2. Test locally with docker-compose.dev.yml
# 3. SSH to forest1 (test production)
# 4. git pull + docker compose restart
# 5. Check if it works
# 6. If good, SSH to wepp1 (production)
# 7. git pull + docker compose restart
# 8. Hope nothing breaks
```

**Problems:**
- No automated testing between environments
- No rollback strategy documented
- Configuration drift between environments
- No visibility into what's deployed where
- Breaking changes reach production
- Database migrations are manual and risky

### Test Coverage Analysis

**Current Test Suite:**
- 92 test files (`.py`)
- Coverage spans: NoDb controllers, Flask routes, microservices, query engine
- Go microservices: status2, preflight2 (separate test suites)
- Frontend: Jest tests + Playwright smoke tests

**Coverage Gaps (Identified):**
1. **Integration Testing**
   - No end-to-end tests through full stack
   - Missing cross-service communication tests
   - No chaos/resilience testing

2. **Deployment Testing**
   - Production Docker image not tested in CI
   - No smoke tests against production-like environment
   - Database migration testing manual

3. **Performance Testing**
   - No performance regression detection
   - No load testing automation
   - Response time SLOs not enforced

4. **Security Testing**
   - No automated dependency scanning
   - No SAST/DAST in pipeline
   - Secrets management not validated

### Infrastructure Context

**Team Structure:**
- Solo developer: Roger
- AI agents: Primary development workforce
  - gpt-5-codex lead developer
  - Claude Sonnet 4.5 lead bug hunter
  - Claude Sonnet 4.5 document author for humans
- Docker group membership: `roger:docker` (required for runners)

**Homelab Architecture:**
- forest.bearhive.internal (dev server)
- forest1.bearhive.internal (test production)
- wepp1 (production server)
- All behind pfSense/HAProxy with TLS termination

---

## Target Architecture

### Three-Tier Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer / Agent                        │
└────────────────────┬────────────────────────────────────────────┘
                     │ Push to GitHub
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Repository (master)                  │
│  • Triggers CI on push/PR                                       │
│  • GitHub Actions workflows execute                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Lint    │    │ Test    │    │ Build   │
│ • mypy  │    │ • pytest│    │ • Docker│
│ • ruff  │    │ • go    │    │   image │
│ • eslint│    │   test  │    │ • Tag   │
└────┬────┘    └────┬────┘    └────┬────┘
     │              │              │
     └──────────────┼──────────────┘
                    │ All gates pass
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  GitHub Container Registry                      │
│  • Stores tested Docker images                                  │
│  • Tagged with commit SHA + version                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ Auto-deploy (test-prod only)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│               Test Production (forest1)                         │
│  • Automatic deployment on master merge                         │
│  • Smoke tests run post-deploy                                  │
│  • Monitored for errors (24-hour soak)                          │
└────────────────────┬────────────────────────────────────────────┘
                     │ Manual promotion
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Production (wepp1)                             │
│  • Manual trigger required                                      │
│  • Blue/green deployment                                        │
│  • Automatic rollback on health check failure                   │
└─────────────────────────────────────────────────────────────────┘
```

### Quality Gates

Each stage enforces specific criteria before proceeding:

| Stage | Gates | Failure Action |
|-------|-------|----------------|
| **Pre-commit** | Lint (local), fast tests | Block commit (optional) |
| **CI: Validate** | mypy, ruff, eslint, prettier | Fail PR check |
| **CI: Test** | pytest (unit+integration), go test, npm test | Fail PR check |
| **CI: Build** | Docker build, image scan, SARIF upload | Fail PR check |
| **Test Production** | Smoke tests, health checks, error rate | Alert + block promotion |
| **Production** | Health checks, canary metrics | Auto-rollback |

---

## GitHub Runners Infrastructure

### Runner Architecture

**Self-hosted runners on homelab infrastructure:**

```
forest.bearhive.internal (Primary Runner Host)
├── runner-1 (Primary)
│   ├── User: roger:docker
│   ├── Labels: [self-hosted, linux, x64, homelab]
│   ├── Capacity: 48 cores, 128GB RAM
│   └── Purpose: CI builds, tests, deployments
├── runner-2 (Secondary - Optional)
│   └── Same config, load balancing
└── Deployment targets accessible via SSH
    ├── forest1.bearhive.internal (test-prod)
    └── wepp1 (production)
```

### Runner Setup

**1. Install GitHub Actions Runner**

```bash
# On forest.bearhive.internal as roger
cd /home/roger
mkdir actions-runner && cd actions-runner

# Download latest runner (check GitHub for current version)
curl -o actions-runner-linux-x64-2.311.0.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure runner (requires GitHub repo admin token)
./config.sh --url https://github.com/rogerlew/wepppy \
            --token <GITHUB_REGISTRATION_TOKEN> \
            --name forest-runner-1 \
            --labels self-hosted,linux,x64,homelab \
            --work _work

# Install as systemd service (run as roger)
sudo ./svc.sh install roger
sudo ./svc.sh start
```

**2. Verify Docker Access**

```bash
# Ensure roger is in docker group
sudo usermod -aG docker roger
newgrp docker

# Test docker access without sudo
docker ps
docker compose version

# Verify runner can execute docker commands
systemctl status actions.runner.rogerlew-wepppy.forest-runner-1.service
```

**3. Runner Configuration File**

Create `/home/roger/actions-runner/.env`:
```bash
# Docker access
DOCKER_HOST=unix:///var/run/docker.sock

# SSH access to deployment targets
SSH_AGENT_PID=<inherit from service>
SSH_AUTH_SOCK=/run/user/$(id -u roger)/keyring/ssh

# Secrets (managed via GitHub Secrets, not committed)
POSTGRES_PASSWORD=<from_github_secret>
SECRET_KEY=<from_github_secret>
SECURITY_PASSWORD_SALT=<from_github_secret>
```

**4. SSH Key Setup for Deployments**

```bash
# Generate deployment key (no passphrase for automation)
ssh-keygen -t ed25519 -C "github-runner-deployment" -f ~/.ssh/github_runner_deploy
chmod 600 ~/.ssh/github_runner_deploy

# Add public key to authorized_keys on forest1 and wepp1
ssh-copy-id -i ~/.ssh/github_runner_deploy.pub roger@forest1.bearhive.internal
ssh-copy-id -i ~/.ssh/github_runner_deploy.pub roger@wepp1

# Add to runner's SSH config
cat >> ~/.ssh/config <<EOF
Host forest1
  HostName forest1.bearhive.internal
  User roger
  IdentityFile ~/.ssh/github_runner_deploy
  StrictHostKeyChecking accept-new

Host wepp1
  HostName wepp1
  User roger
  IdentityFile ~/.ssh/github_runner_deploy
  StrictHostKeyChecking accept-new
EOF
```

### Multiple Runners (Optional Scaling)

If workload increases, add more runners on the same host:

```bash
# Second runner instance
cd /home/roger
mkdir actions-runner-2 && cd actions-runner-2
# ... repeat setup with different name ...
./config.sh --name forest-runner-2 ...
```

**Benefits:**
- Parallel job execution
- Isolation between test runs
- No shared state issues

**Single Runner Strategy (Start Here):**
- Simpler to manage
- Sufficient for solo dev + agents
- Upgrade to multiple runners when queue depth exceeds SLOs

---

## Testing Strategy & Coverage Gaps

### Current Coverage Matrix

| Area | Test Files | Coverage | Status | Priority |
|------|-----------|----------|--------|----------|
| NoDb Controllers | tests/nodb/* | ~70% | ⚠️ Missing edge cases | High |
| Flask Routes | tests/weppcloud/routes/* | ~60% | ⚠️ Gaps in error handling | High |
| Microservices | tests/microservices/* | ~50% | ⚠️ Missing integration | High |
| Go Services | services/*/internal/*_test.go | ~65% | ⚠️ Need integration tags | Medium |
| Frontend (Jest) | static-src/__tests__/* | ~55% | ⚠️ Component coverage gaps | Medium |
| Smoke Tests | tests/smoke/* | Minimal | ❌ Not in CI | High |
| Load Tests | - | 0% | ❌ Nonexistent | Low |
| Security Tests | - | 0% | ❌ Nonexistent | Medium |

### Gap Analysis & Remediation

#### 1. Integration Testing Gaps

**Current State:** Tests mock dependencies heavily; cross-service flows untested

**Required Tests:**
```python
# tests/integration/test_full_run_workflow.py
@pytest.mark.integration
@pytest.mark.slow
def test_create_watershed_to_wepp_run(live_services):
    """End-to-end: Create project → delineate → climate → soils → WEPP run"""
    # Requires: Redis, PostgreSQL, RQ workers, microservices
    # Validates: Full happy path, ~2 minutes
    pass

# tests/integration/test_cross_service_communication.py
@pytest.mark.integration
def test_status_stream_propagation(live_redis, live_status2):
    """Verify NoDb logs flow through status2 WebSocket"""
    pass
```

**Implementation Priority:** High (blocks confident deployments)

#### 2. Deployment Smoke Tests

**Current State:** Playwright tests exist but not integrated with CI

**Development Strategy:**
1. **Manual visual QA first** (human eyeballs only)
   - Deploy to forest (dev environment)
   - Click through all configurations: vanilla, disturbed, portland, rhem, eu, au, earth
   - Validate visual appearance, spacing, alignment, UX flow
   - Fix issues until UI "feels right"
   - Only humans can catch subtle visual/UX regressions initially

2. **Backend pipeline tests with `test_run_rq`**
   - Use scaffolded `test_run_rq()` function in `wepppy/rq/project_rq.py`
   - **Runs directly in CI/CD pipeline** - no RQ workers, no dashboard needed
   - Executes full preparation pipeline inline (no queue dependency)
   - Clones base project, clears locks, runs DEM/landuse/climate/WEPP
   - Returns tuple of cleared lock identifiers
   - **Small watersheds complete in <1 minute** when fully automated
   - Validates backend workflows before frontend integration

3. **Frontend component tests (Jest)**
   - Fast unit tests for controllers, API wiring, event handlers
   - No backend dependency needed
   - Runs in CI for quick feedback

4. **End-to-end browser tests (Playwright)**
   - Full browser automation with debugging capabilities
   - Uses `test_run_rq` backend for reproducible starting state
   - Can inspect network, console logs, take screenshots
   - Only automate after manual QA establishes baseline

**Test Profile Strategy (Selective, Not Factorial):**

Instead of testing every combination (7 configs × N watersheds × M climates = explosion), 
use **targeted test profiles** that cover variation dimensions efficiently:

```python
# tests/integration/test_profiles.py
"""
Test profiles provide comprehensive coverage without factorial explosion.
Each profile tests a specific dimension of variation.
"""

# Profile 1: Configuration Coverage (all configs, same small watershed)
CONFIG_COVERAGE = [
    {'profile': 'vanilla-quick', 'config': 'vanilla', 'watershed': 'small_idaho', 'runtime': '45s'},
    {'profile': 'disturbed-quick', 'config': 'disturbed', 'watershed': 'small_idaho', 'runtime': '50s'},
    {'profile': 'portland-quick', 'config': 'portland', 'watershed': 'small_oregon', 'runtime': '55s'},
    {'profile': 'rhem-quick', 'config': 'rhem', 'watershed': 'small_rangeland', 'runtime': '60s'},
    {'profile': 'eu-quick', 'config': 'eu-disturbed', 'watershed': 'small_spain', 'runtime': '50s'},
    {'profile': 'au-quick', 'config': 'au-disturbed', 'watershed': 'small_australia', 'runtime': '50s'},
    {'profile': 'earth-quick', 'config': 'earth', 'watershed': 'small_generic', 'runtime': '45s'},
]

# Profile 2: Watershed Size Variation (vanilla config, different sizes)
WATERSHED_SIZE = [
    {'profile': 'tiny-watershed', 'config': 'vanilla', 'watershed': 'tiny_5ha', 'runtime': '30s'},
    {'profile': 'small-watershed', 'config': 'vanilla', 'watershed': 'small_50ha', 'runtime': '45s'},
    {'profile': 'medium-watershed', 'config': 'vanilla', 'watershed': 'medium_500ha', 'runtime': '2m'},
    {'profile': 'large-watershed', 'config': 'vanilla', 'watershed': 'large_5000ha', 'runtime': '8m'},
]

# Profile 3: Climate Variation (vanilla config, small watershed, different climates)
CLIMATE_VARIATION = [
    {'profile': 'climate-gridmet', 'config': 'vanilla', 'climate_mode': 'gridmet', 'runtime': '50s'},
    {'profile': 'climate-daymet', 'config': 'vanilla', 'climate_mode': 'daymet', 'runtime': '50s'},
    {'profile': 'climate-prism', 'config': 'vanilla', 'climate_mode': 'prism', 'runtime': '50s'},
    {'profile': 'climate-observed', 'config': 'vanilla', 'climate_mode': 'observed', 'runtime': '45s'},
    {'profile': 'climate-agdc', 'config': 'eu-disturbed', 'climate_mode': 'agdc', 'runtime': '50s'},
]

# Profile 4: Geographic Variation (vanilla config, different regions)
GEOGRAPHIC = [
    {'profile': 'geo-idaho', 'config': 'vanilla', 'region': 'idaho', 'runtime': '45s'},
    {'profile': 'geo-montana', 'config': 'vanilla', 'region': 'montana', 'runtime': '45s'},
    {'profile': 'geo-oregon', 'config': 'vanilla', 'region': 'oregon', 'runtime': '45s'},
    {'profile': 'geo-california', 'config': 'vanilla', 'region': 'california', 'runtime': '50s'},
    {'profile': 'geo-spain', 'config': 'eu-disturbed', 'region': 'spain', 'runtime': '50s'},
    {'profile': 'geo-australia', 'config': 'au-disturbed', 'region': 'australia', 'runtime': '50s'},
]

# Profile 5: Edge Cases (stress testing)
EDGE_CASES = [
    {'profile': 'edge-steep-terrain', 'config': 'vanilla', 'scenario': 'steep_slopes', 'runtime': '1m'},
    {'profile': 'edge-flat-terrain', 'config': 'vanilla', 'scenario': 'flat_watershed', 'runtime': '40s'},
    {'profile': 'edge-many-channels', 'config': 'vanilla', 'scenario': 'complex_network', 'runtime': '2m'},
    {'profile': 'edge-single-hillslope', 'config': 'vanilla', 'scenario': 'minimal_watershed', 'runtime': '25s'},
]

# CI/CD Test Suite Tiers
TIER_FAST = CONFIG_COVERAGE[:3]  # 3 configs, ~2.5 minutes total
TIER_STANDARD = CONFIG_COVERAGE + CLIMATE_VARIATION  # All configs + climates, ~8 minutes
TIER_COMPREHENSIVE = CONFIG_COVERAGE + WATERSHED_SIZE + CLIMATE_VARIATION + GEOGRAPHIC  # ~18 minutes
TIER_FULL = [*CONFIG_COVERAGE, *WATERSHED_SIZE, *CLIMATE_VARIATION, *GEOGRAPHIC, *EDGE_CASES]  # ~30 minutes
```

**Backend Pipeline Tests (Foundation):**
```python
# tests/integration/test_pipeline_full.py
import pytest
from wepppy.rq.project_rq import test_run_rq
from tests.integration.test_profiles import (
    CONFIG_COVERAGE, TIER_FAST, TIER_STANDARD, TIER_COMPREHENSIVE
)

@pytest.mark.integration
@pytest.mark.fast
@pytest.mark.parametrize('profile', TIER_FAST)
def test_pipeline_fast_tier(profile, tmp_path):
    """Fast tier: 3 configs, runs in ~2.5 minutes (PR checks)"""
    runid = provision_test_run_from_profile(profile, tmp_path)
    locks_cleared = test_run_rq(runid)
    validate_successful_run(runid, profile['config'])

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize('profile', TIER_STANDARD)
def test_pipeline_standard_tier(profile, tmp_path):
    """Standard tier: All configs + climates, ~8 minutes (main branch)"""
    runid = provision_test_run_from_profile(profile, tmp_path)
    locks_cleared = test_run_rq(runid)
    validate_successful_run(runid, profile['config'])

@pytest.mark.integration
@pytest.mark.comprehensive
@pytest.mark.parametrize('profile', TIER_COMPREHENSIVE)
def test_pipeline_comprehensive_tier(profile, tmp_path):
    """Comprehensive tier: ~18 minutes (nightly or pre-release)"""
    runid = provision_test_run_from_profile(profile, tmp_path)
    locks_cleared = test_run_rq(runid)
    validate_successful_run(runid, profile['config'])

def provision_test_run_from_profile(profile, base_dir):
    """Create test run matching profile specification"""
    config = profile['config']
    watershed = profile.get('watershed', 'small_idaho')
    climate_mode = profile.get('climate_mode', 'gridmet')
    
    # Load watershed template
    template_path = f'tests/data/watersheds/{watershed}.json'
    runid = create_test_run(config=config, template=template_path)
    
    # Override climate if specified
    if 'climate_mode' in profile:
        climate = Climate.getInstance(get_wd(runid))
        climate.climate_mode = climate_mode
    
    return runid

def validate_successful_run(runid, config):
    """Common validation for all test runs"""
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    wepp = Wepp.getInstance(wd)
    
    assert wepp.run_successful, f"WEPP run failed for {config}"
    assert os.path.exists(wepp.loss_grid_path), f"Loss grid missing for {config}"
    assert ron.config == config, f"Config mismatch: expected {config}, got {ron.config}"
```

**CI/CD Integration (Tiered Execution):**
```yaml
# .github/workflows/pr.yml
test-backend-fast:
  runs-on: [self-hosted, linux, homelab]
  steps:
    - name: Fast Backend Tests (3 configs, ~2.5 min)
      run: wctl run-pytest tests/integration -m "integration and fast"

# .github/workflows/main.yml (after merge to master)
test-backend-standard:
  runs-on: [self-hosted, linux, homelab]
  steps:
    - name: Standard Backend Tests (all configs + climates, ~8 min)
      run: wctl run-pytest tests/integration -m "integration and slow"

# .github/workflows/nightly.yml or manual trigger
test-backend-comprehensive:
  runs-on: [self-hosted, linux, homelab]
  steps:
    - name: Comprehensive Backend Tests (~18 min)
      run: wctl run-pytest tests/integration -m "integration and comprehensive"
```

**Frontend E2E Tests (After Manual QA):**
```javascript
// tests/smoke/test_full_workflow.spec.js
import { test, expect } from '@playwright/test';

test('vanilla workflow end-to-end', async ({ page }) => {
    // 1. Create run via test-support API
    const response = await page.request.post('/tests/api/create-run', {
        data: { config: 'vanilla' }
    });
    const { runid, url } = await response.json();
    
    // 2. Navigate and execute workflow
    await page.goto(url);
    
    await page.click('#btn-fetch-dem');
    await page.waitForSelector('.status-success');
    
    await page.click('#btn-build-climate');
    await page.waitForSelector('.climate-built-indicator');
    
    await page.click('#btn-run-wepp');
    await page.waitForSelector('.wepp-complete', { timeout: 300000 });
    
    // 3. Debug capabilities
    await page.screenshot({ path: 'test-results/workflow.png' });
    
    // 4. Verify no console errors
    const errors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text());
    });
    expect(errors).toHaveLength(0);
    
    // 5. Cleanup
    await page.request.delete(`/tests/api/run/${runid}`);
});
```

**Basic Deployment Smoke Script:**
```bash
# tests/smoke/post_deploy_smoke.sh
#!/bin/bash
# Runs after deployment to test-prod or prod
set -euo pipefail

BASE_URL=${1:-http://localhost:8080}
echo "Running smoke tests against $BASE_URL"

# 1. Health check
curl -f "$BASE_URL/health" || exit 1

# 2. Create test run (via TEST_SUPPORT_ENABLED endpoints)
response=$(curl -X POST "$BASE_URL/tests/api/create-run" \
  -H "Content-Type: application/json" \
  -d '{"config": "dev_unit_1"}')
runid=$(echo "$response" | jq -r '.runid')

# 3. Verify run accessible
curl -f "$BASE_URL/runs/$runid/dev_unit_1" || exit 1

# 4. Cleanup
curl -X DELETE "$BASE_URL/tests/api/run/$runid"

echo "✅ Smoke tests passed"
```

**Playwright Debugging Features:**
- `page.pause()` - Interactive debugger with step-through
- `--headed` mode - Watch tests execute in real browser
- Network inspection - Capture all API calls and responses
- Console log capture - Detect JavaScript errors
- Screenshots/videos - Visual debugging artifacts
- Trace viewer - Replay test execution step-by-step
- Element inspector - Debug selectors interactively

**Implementation Priority:** Critical (prevents broken deployments)

#### 3. Performance Regression Tests

**Current State:** No baseline metrics, no automated checks

**Required Tests:**
```python
# tests/performance/test_wepp_run_benchmarks.py
@pytest.mark.benchmark
def test_hillslope_runtime_baseline(benchmark_fixture):
    """Ensure hillslope runs complete within SLO"""
    runtime = run_hillslope_batch(n=10)
    assert runtime < 30.0, f"SLO violated: {runtime}s > 30s"
    
@pytest.mark.benchmark
def test_catalog_generation_performance():
    """Ensure markdown-doc catalog stays under 5 seconds"""
    from subprocess import run, PIPE
    result = run(["markdown-doc", "catalog"], stdout=PIPE, stderr=PIPE, timeout=10)
    # Assert based on timing in result
```

**Implementation Priority:** Medium (quality of life, prevents regressions)

#### 4. Database Migration Testing

**Current State:** Manual `flask db upgrade`, no validation

**Required Tests:**
```python
# tests/migrations/test_migration_safety.py
@pytest.mark.migrations
def test_migrations_reversible(postgres_container):
    """Ensure migrations can upgrade and downgrade safely"""
    # Apply all migrations
    run_alembic_upgrade()
    
    # Verify schema
    assert_table_exists("users")
    assert_table_exists("runs")
    
    # Downgrade one step
    run_alembic_downgrade(steps=1)
    
    # Re-upgrade
    run_alembic_upgrade()
    
@pytest.mark.migrations
def test_migration_data_integrity(postgres_with_data):
    """Ensure migrations don't corrupt existing data"""
    # Seed data
    create_test_runs(n=10)
    
    # Apply migration
    run_alembic_upgrade()
    
    # Verify data intact
    assert_runs_count() == 10
```

**Implementation Priority:** Critical (migrations are high-risk)

### 5. Configuration Coverage Testing

**Current State:** No systematic testing of all supported configurations

**Required Tests:**

```python
# tests/integration/test_all_configurations.py
import pytest

CONFIGURATIONS = [
    'vanilla',
    'disturbed', 
    'portland',
    'rhem',
    'eu-disturbed',
    'au-disturbed',
    'earth'
]

@pytest.mark.integration
@pytest.mark.parametrize('config', CONFIGURATIONS)
def test_configuration_creates_successfully(config):
    """Verify each configuration can initialize a project"""
    runid = create_test_run(config=config)
    ron = Ron.getInstance(get_wd(runid))
    
    assert ron.config == config
    assert ron.valid
    
    # Cleanup
    cleanup_test_run(runid)

@pytest.mark.integration
@pytest.mark.parametrize('config', CONFIGURATIONS)
def test_configuration_core_workflow(config):
    """Test delineation → climate → soils → landuse for each config"""
    runid = create_test_run(config=config)
    
    # Delineate watershed
    response = trigger_delineation(runid, config)
    assert response['Success']
    
    # Build climate
    response = trigger_climate(runid, config)
    assert response['Success']
    
    # Build soils
    response = trigger_soils(runid, config)
    assert response['Success']
    
    # Build landuse
    response = trigger_landuse(runid, config)
    assert response['Success']
    
    # Verify NoDb state
    ron = Ron.getInstance(get_wd(runid))
    watershed = Watershed.getInstance(get_wd(runid))
    climate = Climate.getInstance(get_wd(runid))
    
    assert watershed.delineation_complete
    assert climate.climate_built
    
    cleanup_test_run(runid)
```

**Configuration-specific validation:**

```python
# tests/integration/test_portland_specifics.py
@pytest.mark.integration
def test_portland_mod_loaded():
    """Portland mod uses custom landuse/soils"""
    runid = create_test_run(config='portland')
    
    landuse = Landuse.getInstance(get_wd(runid))
    # Portland should have portland-specific management map
    assert 'portland' in landuse.landuse_db_path.lower()

# tests/integration/test_rhem_workflow.py
@pytest.mark.integration
def test_rhem_execution():
    """RHEM model executes for rangeland configs"""
    runid = create_test_run(config='rhem')
    
    # RHEM-specific workflow
    response = trigger_rhem_run(runid)
    assert response['Success']
    
    # Verify RHEM outputs exist
    rhem = Rhem.getInstance(get_wd(runid))
    assert rhem.has_results

# tests/integration/test_europe_climate.py
@pytest.mark.integration  
def test_eu_climate_assignment():
    """Europe configs use AGDC monthly climate"""
    runid = create_test_run(config='eu-disturbed')
    
    climate = Climate.getInstance(get_wd(runid))
    # Should use AGDC mode for Europe
    assert climate.climate_mode == ClimateMode.AGDC_Monthly
```

**Implementation Priority:** High (blocks confident production deployments)

### 6. Legacy Project Loading Tests

**Current State:** No automated testing of old project compatibility

**Required Tests:**

```python
# tests/migrations/test_legacy_projects.py
import pytest
from pathlib import Path

# Store sample legacy .nodb files from different eras
LEGACY_SAMPLES = Path(__file__).parent / 'data' / 'legacy_samples'

@pytest.mark.migrations
@pytest.mark.parametrize('project_dir', [
    'sample_2023_vanilla',
    'sample_2024_disturbed',
    'sample_2024_portland',
    'sample_2023_rhem',
])
def test_legacy_project_loads(project_dir):
    """Ensure old projects load with current code"""
    legacy_path = LEGACY_SAMPLES / project_dir
    
    # Try loading Ron (primary entry point)
    ron = Ron.getInstance(str(legacy_path))
    assert ron is not None
    assert ron.runid
    
    # Try loading each controller
    try:
        watershed = Watershed.getInstance(str(legacy_path))
        climate = Climate.getInstance(str(legacy_path))
        landuse = Landuse.getInstance(str(legacy_path))
        soils = Soils.getInstance(str(legacy_path))
        wepp = Wepp.getInstance(str(legacy_path))
    except Exception as e:
        pytest.fail(f"Failed to load legacy project: {e}")

@pytest.mark.migrations
def test_legacy_module_redirects():
    """Verify _LEGACY_MODULE_REDIRECTS covers all renames"""
    from wepppy.nodb.base import NoDbBase
    
    # Should not raise ImportError
    NoDbBase._ensure_legacy_module_imports()
    
    # Test specific old module paths
    old_paths = [
        'wepppy.nodb.baer',  # Moved to mods.baer
        'wepppy.nodb.disturbed',  # Moved to mods.disturbed
    ]
    
    for old_path in old_paths:
        # Should be importable due to redirects
        try:
            __import__(old_path)
        except ImportError as e:
            pytest.fail(f"Legacy redirect missing for {old_path}: {e}")
```

**Implementation Priority:** Critical (breaks user trust if old projects don't load)

### Test Execution Strategy

**Local Development:**
```bash
# Fast feedback loop (< 10 seconds)
wctl run-pytest tests/nodb/test_climate.py -v

# Pre-commit gate (< 2 minutes)
wctl run-pytest tests --maxfail=1 -m "not slow"

# Full suite before PR (< 10 minutes)
wctl run-pytest tests --maxfail=1
```

**CI Pipeline:**
```yaml
# .github/workflows/test.yml
- name: Unit Tests (Fast)
  run: wctl run-pytest tests -m "unit" --maxfail=1
  
- name: Integration Tests (Slow)
  run: wctl run-pytest tests -m "integration" --maxfail=1
  
- name: Go Microservices
  run: |
    wctl run-status-tests
    wctl run-preflight-tests -tags=integration
```

---

## CI Pipeline Design

### Implemented Workflows (2025-10-31)

| Workflow | File | Trigger | Runner | Notes |
|----------|------|---------|--------|-------|
| Docs Quality | `.github/workflows/docs-quality.yml` | PRs and pushes touching Markdown/wctl | `self-hosted`, `Linux`, `X64`, `homelab` | Executes `wctl doc-lint` scoped to docs-related paths (avoids `.docker-data`), `wctl doc-bench`, normalizes SARIF to CodeQL v3 schema, and runs `cargo fmt/clippy/test` when the markdown-doc workspace is present (`MARKDOWN_DOC_WORKSPACE`). Requires markdown-doc binaries pre-installed; uploads SARIF to Code Scanning and archives JSON results. |

### Workflow Structure

**Three primary workflows:**

1. **Pull Request Validation** (`.github/workflows/pr.yml`)
   - Triggered on: PR open/update
   - Runs on: Self-hosted runner
   - Purpose: Fast feedback, block broken code

2. **Main Branch CI/CD** (`.github/workflows/main.yml`)
   - Triggered on: Push to master
   - Runs on: Self-hosted runner
   - Purpose: Build images, deploy to test-prod

3. **Production Deployment** (`.github/workflows/deploy-prod.yml`)
   - Triggered on: Manual workflow_dispatch
   - Runs on: Self-hosted runner
   - Purpose: Promote to production

### Pull Request Validation Workflow

**File:** `.github/workflows/pr.yml`

```yaml
name: Pull Request Validation

on:
  pull_request:
    branches: [master]
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '_notes/**'

jobs:
  lint:
    runs-on: [self-hosted, linux, homelab]
    steps:
      - uses: actions/checkout@v4
      
      - name: Python Lint (ruff, mypy)
        run: |
          wctl exec weppcloud ruff check wepppy/
          wctl exec weppcloud mypy wepppy/nodb/core/
      
      - name: Go Lint (services)
        run: |
          wctl exec status-build go fmt ./...
          wctl exec preflight-build go fmt ./...
      
      - name: Frontend Lint
        run: wctl run-npm lint
      
      - name: Markdown Docs Lint
        run: wctl doc-lint --format sarif > results.sarif
        continue-on-error: true
      
      - name: Validate SARIF Output
        run: |
          if [ ! -s results.sarif ]; then
            echo '{"version": "2.1.0", "runs": []}' > results.sarif
          fi
      
      - name: Upload SARIF Results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
          category: documentation

  test-python:
    runs-on: [self-hosted, linux, homelab]
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Unit Tests
        run: wctl run-pytest tests -m "unit" --maxfail=1 --cov=wepppy --cov-report=xml
      
      - name: Integration Tests
        run: wctl run-pytest tests -m "integration" --maxfail=1
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: coverage.xml
          flags: python

  test-go:
    runs-on: [self-hosted, linux, homelab]
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Status2 Tests
        run: wctl run-status-tests
      
      - name: Status2 Integration Tests
        run: wctl run-status-tests -tags=integration ./internal/server
      
      - name: Preflight2 Tests
        run: wctl run-preflight-tests
      
      - name: Preflight2 Integration Tests
        run: wctl run-preflight-tests -tags=integration ./internal/server

  test-frontend:
    runs-on: [self-hosted, linux, homelab]
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Jest Tests
        run: wctl run-npm test
      
      - name: Build Static Assets
        run: wctl build-static-assets

  build-image:
    runs-on: [self-hosted, linux, homelab]
    needs: [test-python, test-go, test-frontend]
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Production Image
        run: |
          docker compose -f docker/docker-compose.prod.yml build weppcloud
          docker tag wepppy:latest ghcr.io/rogerlew/wepppy:pr-${{ github.event.pull_request.number }}
      
      - name: Scan Image for Vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/rogerlew/wepppy:pr-${{ github.event.pull_request.number }}
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Validate Trivy SARIF
        run: |
          if [ ! -s trivy-results.sarif ]; then
            echo '{"version": "2.1.0", "runs": []}' > trivy-results.sarif
          fi
      
      - name: Upload Trivy Results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif
          category: container-security
```

### Main Branch CI/CD Workflow

**File:** `.github/workflows/main.yml`

```yaml
name: Main Branch CI/CD

on:
  push:
    branches: [master]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: [self-hosted, linux, homelab]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=ref,event=branch
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and Push Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
  
  deploy-test-prod:
    runs-on: [self-hosted, linux, homelab]
    needs: build-and-push
    environment:
      name: test-production
      url: https://wc-prod.bearhive.duckdns.org
    steps:
      - name: Deploy to forest1
        run: |
          ssh forest1 'cd /opt/wepppy && \
            git pull && \
            docker compose -f docker/docker-compose.prod.yml pull weppcloud && \
            docker compose -f docker/docker-compose.prod.yml up -d weppcloud && \
            docker compose -f docker/docker-compose.prod.yml restart caddy'
      
      - name: Wait for Health Check
        run: |
          for i in {1..30}; do
            if curl -f https://wc-prod.bearhive.duckdns.org/health; then
              echo "✅ Health check passed"
              exit 0
            fi
            echo "⏳ Waiting for service... ($i/30)"
            sleep 10
          done
          echo "❌ Health check failed"
          exit 1
      
      - name: Run Smoke Tests
        run: |
          bash tests/smoke/post_deploy_smoke.sh https://wc-prod.bearhive.duckdns.org
      
      - name: Notify Deployment
        if: success()
        run: |
          echo "🚀 Deployed commit ${{ github.sha }} to test-production"
```

### Production Deployment Workflow

**File:** `.github/workflows/deploy-prod.yml`

```yaml
name: Production Deployment

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker image tag to deploy (default: master-<latest_sha>)'
        required: false
        type: string
      skip_smoke_tests:
        description: 'Skip smoke tests (use only in emergency)'
        required: false
        type: boolean
        default: false

jobs:
  deploy-production:
    runs-on: [self-hosted, linux, homelab]
    environment:
      name: production
      url: https://wepp.cloud
    steps:
      - uses: actions/checkout@v4
      
      - name: Determine Image Tag
        id: image_tag
        run: |
          if [ -n "${{ inputs.image_tag }}" ]; then
            echo "tag=${{ inputs.image_tag }}" >> $GITHUB_OUTPUT
          else
            echo "tag=master-$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT
          fi
      
      - name: Verify Image Exists
        run: |
          docker manifest inspect ghcr.io/rogerlew/wepppy:${{ steps.image_tag.outputs.tag }}
      
      - name: Backup Production Database
        run: |
          ssh wepp1 'docker compose -f /opt/wepppy/docker/docker-compose.prod.yml \
            run --rm postgres-backup bash -lc \
            "pg_dump -h \$PGHOST -U \$PGUSER -d \$PGDATABASE -Fc \
            -f /backups/pre-deploy-$(date +%Y%m%d-%H%M%S).dump"'
      
      - name: Deploy to wepp1 (Blue-Green)
        run: |
          ssh wepp1 'cd /opt/wepppy && \
            git pull && \
            export WEPPCLOUD_IMAGE=ghcr.io/rogerlew/wepppy:${{ steps.image_tag.outputs.tag }} && \
            docker compose -f docker/docker-compose.prod.yml pull weppcloud && \
            docker compose -f docker/docker-compose.prod.yml up -d weppcloud && \
            docker compose -f docker/docker-compose.prod.yml restart caddy'
      
      - name: Health Check with Rollback
        run: |
          for i in {1..30}; do
            if curl -f https://wepp.cloud/health; then
              echo "✅ Health check passed"
              exit 0
            fi
            echo "⏳ Waiting for service... ($i/30)"
            sleep 10
          done
          
          echo "❌ Health check failed - Rolling back"
          ssh wepp1 'cd /opt/wepppy && \
            docker compose -f docker/docker-compose.prod.yml logs --tail=100 weppcloud && \
            docker compose -f docker/docker-compose.prod.yml rollback weppcloud'
          exit 1
      
      - name: Run Smoke Tests
        if: ${{ !inputs.skip_smoke_tests }}
        run: |
          bash tests/smoke/post_deploy_smoke.sh https://wepp.cloud
      
      - name: Monitor Error Rate (5 min)
        run: |
          echo "📊 Monitoring error rate for 5 minutes..."
          # TODO: Query Redis/logs for error rate
          # If errors spike above baseline, auto-rollback
      
      - name: Tag Release
        if: success()
        run: |
          git tag -a "prod-$(date +%Y%m%d-%H%M%S)" \
            -m "Production deployment: ${{ steps.image_tag.outputs.tag }}"
          git push origin --tags
```

---

## Deployment Environments

### Environment Configuration Matrix

| Setting | Development | Test Production | Production |
|---------|-------------|-----------------|------------|
| **Host** | forest | forest1 | wepp1 |
| **Domain** | wc.bearhive.duckdns.org | wc-prod.bearhive.duckdns.org | wepp.cloud |
| **Compose File** | docker-compose.dev.yml | docker-compose.prod.yml | docker-compose.prod.yml |
| **Image Source** | Local build | ghcr.io (master-*) | ghcr.io (tagged) |
| **Data Volumes** | Bind mounts | Named volumes | Named volumes |
| **Auto-deploy** | Manual | ✅ On master push | ❌ Manual only |
| **Rollback** | N/A | Manual | Automated |
| **Health Checks** | Optional | Required | Required + monitoring |
| **Backup Frequency** | None | Daily | Hourly + pre-deploy |

### Environment-Specific Configuration

**1. Development (forest.bearhive.internal)**

```bash
# docker/.env.dev
UID=1000
GID=1000
POSTGRES_PASSWORD=localdev
SECRET_KEY=<dev_secret>
SECURITY_PASSWORD_SALT=<dev_salt>
EXTERNAL_HOST=wc.bearhive.duckdns.org

# Features enabled
TEST_SUPPORT_ENABLED=true
BATCH_RUNNER_ENABLED=true
DEBUG=true
```

**Purpose:**
- Rapid iteration with bind mounts
- Live reload for code changes
- Minimal security constraints
- Agent workspace

**2. Test Production (forest1.bearhive.internal)**

```bash
# /opt/wepppy/docker/.env
UID=33  # www-data
GID=1234  # webgroup
POSTGRES_PASSWORD=<from_github_secrets>
SECRET_KEY=<from_github_secrets>
SECURITY_PASSWORD_SALT=<from_github_secrets>
EXTERNAL_HOST=wc-prod.bearhive.duckdns.org

# Features
TEST_SUPPORT_ENABLED=false
BATCH_RUNNER_ENABLED=true
DEBUG=false

# Image override (set by CI)
WEPPCLOUD_IMAGE=ghcr.io/rogerlew/wepppy:master-<sha>
```

**Purpose:**
- Pre-production validation environment
- **No hurdles** - auto-deploys when master CI passes
- Functional testing ground for all configurations
- Legacy project compatibility validation
- Select user acceptance testing

**3. Production (wepp1)**

```bash
# /opt/wepppy/docker/.env
UID=33
GID=1234
POSTGRES_PASSWORD=<vault_secret>
SECRET_KEY=<vault_secret>
SECURITY_PASSWORD_SALT=<vault_secret>
EXTERNAL_HOST=wepp.cloud

# Features
TEST_SUPPORT_ENABLED=false
BATCH_RUNNER_ENABLED=true
DEBUG=false

# Image pinned to tested tag
WEPPCLOUD_IMAGE=ghcr.io/rogerlew/wepppy:prod-20251026-143022
```

**Purpose:**
- Public-facing service (wepp.cloud)
- **Maximum stability** - requires functional validation gate
- All configurations must work (vanilla, portland, rhem, eu, au, earth, etc.)
- Legacy projects must load correctly
- Production data integrity critical

### Secrets Management

**GitHub Secrets (Repository Settings):**
```
POSTGRES_PASSWORD_PROD
SECRET_KEY_PROD
SECURITY_PASSWORD_SALT_PROD
GITHUB_RUNNER_DEPLOY_KEY  # SSH key for deployments
```

**On Deployment Targets:**
```bash
# /opt/wepppy/docker/.env (owned by root, readable by docker group)
chmod 640 /opt/wepppy/docker/.env
chown root:docker /opt/wepppy/docker/.env

# Never commit secrets to git
git update-index --assume-unchanged docker/.env
```

---

## Release Process

### Semantic Versioning

**Version scheme:** `YYYY.MM.PATCH[-PRERELEASE]`

Examples:
- `2025.10.1` - October 2025, first patch
- `2025.10.2-beta` - Pre-release
- `2025.11.1` - November 2025 release

### Release Checklist

#### 1. Prepare Release (Agent or Human)

```bash
# Create release branch
git checkout -b release/2025.10.1

# Update version in relevant files
echo "2025.10.1" > VERSION
sed -i 's/version = .*/version = "2025.10.1"/' pyproject.toml

# Update CHANGELOG.md
cat >> CHANGELOG.md <<EOF
## [2025.10.1] - $(date +%Y-%m-%d)

### Added
- Feature X
- Feature Y

### Fixed
- Bug Z

### Changed
- Refactored module A
EOF

# Commit and push
git add VERSION pyproject.toml CHANGELOG.md
git commit -m "Release 2025.10.1"
git push origin release/2025.10.1
```

#### 2. Validate Release Branch

```bash
# Trigger PR validation
gh pr create --base master --head release/2025.10.1 \
  --title "Release 2025.10.1" \
  --body "Release checklist: ..."

# Wait for all CI checks to pass
# Review with Roger if significant changes
```

#### 3. Merge and Deploy to Test Production

```bash
# Merge to master (triggers auto-deploy to test-prod)
gh pr merge release/2025.10.1 --squash

# Monitor test production deployment
watch -n 5 'curl -s https://wc-prod.bearhive.duckdns.org/health | jq'

# Run extended smoke tests
cd tests/smoke
npm run smoke -- --base-url https://wc-prod.bearhive.duckdns.org
```

#### 4. Functional Validation (Critical Gate Before Production)

**This is the real hurdle for production deployment - not arbitrary time delays.**

**Required Validation Checklist:**

##### A. Legacy Project Compatibility
- [ ] **Older NoDb serialization** - Verify projects from 2023-2024 load correctly
  ```bash
  # Test loading legacy .nodb files
  python tests/migrations/test_legacy_project_loader.py --samples 10
  ```
- [ ] **NoDb schema migrations** - Ensure backward compatibility or provide migration path
  ```bash
  # Verify _LEGACY_MODULE_REDIRECTS cover all renamed modules
  python -c "from wepppy.nodb.base import NoDbBase; NoDbBase._ensure_legacy_module_imports()"
  ```
- [ ] **Database schema compatibility** - Old runs can query new schema
  ```bash
  # Run Alembic migration tests
  wctl run-pytest tests/migrations/ --maxfail=1
  ```

##### B. Core Configuration Validation
Test all major configuration types in test-prod:
- [ ] **Vanilla** - Basic WEPP runs (US)
- [ ] **Disturbed** - Burn severity workflows
- [ ] **Portland** - Portland-specific mod
- [ ] **RHEM** - Rangeland Hydrology and Erosion Model
- [ ] **EU** - Europe configurations
- [ ] **AU** - Australia configurations  
- [ ] **EARTH** - Global configurations

**Validation script:**
```bash
# Test each config type creates successfully
for config in vanilla disturbed portland rhem eu au earth; do
  echo "Testing $config..."
  response=$(curl -X POST https://wc-prod.bearhive.duckdns.org/tests/api/create-run \
    -H "Content-Type: application/json" \
    -d "{\"config\": \"$config\"}")
  
  runid=$(echo "$response" | jq -r '.runid')
  if [ "$runid" == "null" ]; then
    echo "❌ Failed to create $config run"
    exit 1
  fi
  
  # Verify run accessible
  curl -f "https://wc-prod.bearhive.duckdns.org/runs/$runid/$config" || exit 1
  
  # Cleanup
  curl -X DELETE "https://wc-prod.bearhive.duckdns.org/tests/api/run/$runid"
  
  echo "✅ $config validated"
done
```

##### C. Ancillary Functionality Tests
- [ ] **RHEM integration** - Rangeland model execution
  ```bash
  # Create RHEM run, verify it builds and executes
  python tests/integration/test_rhem_workflow.py
  ```
- [ ] **WEPPcloudR reports** - R visualization generation
  ```bash
  # Test R service endpoint
  curl -f https://wc-prod.bearhive.duckdns.org/runs/test-run/vanilla/WEPPcloudR/loss_summary.R
  ```
- [ ] **Batch runner** - GeoJSON upload and template processing
  ```bash
  python tests/integration/test_batch_runner.py
  ```
- [ ] **Export formats** - DSS, ArcGIS, legacy formats
  ```bash
  # Test each export type
  wctl run-pytest tests/weppcloud/test_export_formats.py
  ```

##### D. Configuration-Specific Features
- [ ] **Portland mod** - Portland-specific landuse/soils
  ```python
  # tests/integration/test_portland_mod.py
  def test_portland_configuration():
      run = create_run(config="portland")
      # Verify Portland-specific behavior
  ```
- [ ] **Europe mod** - EU climate, soils, management
  ```python
  # tests/integration/test_europe_configurations.py
  def test_eu_climate_assignment():
      run = create_run(config="eu-disturbed")
      # Verify AGDC monthly climate selection
  ```
- [ ] **Australia mod** - AU landuse, ASRIS soils
  ```python
  # tests/integration/test_australia_configurations.py  
  def test_au_soil_assignment():
      run = create_run(config="au-disturbed")
      # Verify ASRIS soil lookup
  ```

##### E. Migration Path Testing (If Schema Changed)
If database or NoDb schema changed:
- [ ] Write migration script in `wepppy/migrations/`
- [ ] Test migration on copy of production data
- [ ] Verify rollback works
- [ ] Document migration in release notes

**Migration test pattern:**
```python
# tests/migrations/test_nodb_schema_migration.py
def test_migrate_v1_to_v2(sample_v1_projects):
    """Ensure old projects can load with new code"""
    for project_dir in sample_v1_projects:
        ron = Ron.getInstance(project_dir)
        assert ron.load_successfully
        # Test critical properties accessible
```

**Validation queries:**
```bash
# Check error rate in test-prod
ssh forest1 "docker compose -f /opt/wepppy/docker/docker-compose.prod.yml \
  exec redis redis-cli --scan --pattern '*:error:*' | wc -l"

# Check recent logs for configuration-specific errors
ssh forest1 "docker compose -f /opt/wepppy/docker/docker-compose.prod.yml \
  logs --since 2h weppcloud | grep -E 'portland|rhem|europe|australia' -i"
```

**Timeline:** Functional validation typically takes 4-8 hours of active testing, not passive waiting.

#### 5. Promote to Production

```bash
# Determine image tag from test-prod deployment
IMAGE_TAG=$(ssh forest1 "docker inspect wepppy-weppcloud-1 \
  --format '{{index .Config.Image}}'" | cut -d: -f2)

# Trigger production deployment via GitHub UI
gh workflow run deploy-prod.yml \
  -f image_tag=$IMAGE_TAG \
  -f skip_smoke_tests=false

# Monitor deployment
gh run watch
```

#### 6. Post-Deployment Validation

```bash
# Verify production health
curl -f https://wepp.cloud/health

# Run smoke tests
bash tests/smoke/post_deploy_smoke.sh https://wepp.cloud

# Check user-facing functionality
# - Create new run
# - Execute watershed delineation
# - Run WEPP model

# Tag release in git
git tag -a v2025.10.1 -m "Production release 2025.10.1"
git push origin v2025.10.1
```

### Emergency Hotfix Process

**When production is broken:**

```bash
# 1. Create hotfix branch from production tag
git checkout v2025.10.1
git checkout -b hotfix/critical-bug

# 2. Fix the bug (minimal changes)
# ... make fix ...
git commit -m "Hotfix: Fix critical bug"

# 3. Fast-track through CI (skip some gates if necessary)
gh pr create --base master --head hotfix/critical-bug \
  --title "HOTFIX: Critical bug" \
  --label "hotfix"

# 4. Deploy immediately after PR merge
gh workflow run deploy-prod.yml \
  -f image_tag=master-$(git rev-parse --short HEAD) \
  -f skip_smoke_tests=true  # Only in emergency

# 5. Backport to release branch
git checkout release/2025.10.2
git cherry-pick <hotfix_commit>
```

---

## Rollback & Safety

### Automatic Rollback Triggers

**Production deployment auto-rolls back if:**
1. Health check fails after 5 minutes
2. Error rate exceeds 5% within first 10 minutes
3. Database connection pool exhausted
4. Critical service unavailable (Redis, PostgreSQL)

### Manual Rollback Procedure

**1. Identify Last Known Good Version**

```bash
# List recent production tags
git tag -l 'prod-*' --sort=-creatordate | head -5

# Example output:
prod-20251026-143022  # Current (broken)
prod-20251025-091511  # Last known good
prod-20251024-162033
```

**2. Execute Rollback**

```bash
# SSH to production server
ssh wepp1

cd /opt/wepppy

# Set image to last known good version
export WEPPCLOUD_IMAGE=ghcr.io/rogerlew/wepppy:prod-20251025-091511

# Pull and restart
docker compose -f docker/docker-compose.prod.yml pull weppcloud
docker compose -f docker/docker-compose.prod.yml up -d weppcloud
docker compose -f docker/docker-compose.prod.yml restart caddy

# Verify health
curl -f https://wepp.cloud/health
```

**3. Database Rollback (If Needed)**

```bash
# List available backups
docker compose -f docker/docker-compose.prod.yml \
  exec postgres-backup ls -lt /backups | head -10

# Restore specific backup
docker compose -f docker/docker-compose.prod.yml stop weppcloud rq-worker

docker compose -f docker/docker-compose.prod.yml \
  exec postgres pg_restore \
  -h postgres -U wepppy -d wepppy --clean \
  /backups/pre-deploy-20251025-091500.dump

docker compose -f docker/docker-compose.prod.yml start weppcloud rq-worker
```

### Blue-Green Deployment (Future Enhancement)

**Goal:** Zero-downtime deployments with instant rollback

```yaml
# docker-compose.prod-bluegreen.yml (future)
services:
  weppcloud-blue:
    image: ${WEPPCLOUD_IMAGE_BLUE}
    # ... config ...
  
  weppcloud-green:
    image: ${WEPPCLOUD_IMAGE_GREEN}
    # ... config ...
  
  caddy:
    # Routes traffic to active color
    environment:
      ACTIVE_COLOR: ${ACTIVE_COLOR:-blue}
```

**Deployment flow:**
1. Deploy new version to inactive color (green)
2. Health check green instance
3. Flip traffic from blue → green in Caddy
4. Monitor for 10 minutes
5. If issues: flip back to blue (instant rollback)
6. If stable: decommission blue, make green the new stable

---

## Agent-Driven Development Integration

### Agent Workflow with CI/CD

**Typical agent development cycle:**

```
Agent receives task
  ↓
1. Pull latest master
2. Create feature branch (feat/agent-<task>)
3. Implement changes (code + tests + docs)
4. Run local validation:
   - wctl run-pytest tests --maxfail=1
   - wctl run-npm check
   - wctl doc-lint --staged
5. Commit and push to GitHub
   ↓
GitHub Actions triggers PR validation
  ↓
Agent monitors CI results via GitHub API
  ↓
If failures: Agent fixes issues, pushes fixes
  ↓
All checks pass: Agent requests review (or auto-merge if delegated)
  ↓
After merge: Agent monitors test-prod deployment
  ↓
If errors in test-prod: Agent investigates logs, prepares hotfix
  ↓
After 24h soak: Agent can trigger prod deployment
```

### Agent Autonomy Levels

**Level 1: Supervised (Current State)**
- Agent implements features
- Human reviews PRs
- Human approves deployments

**Level 2: Semi-Autonomous (Near-term Goal)**
- Agent implements + tests
- Auto-merge on green CI
- Agent deploys to test-prod
- Human approves prod deployment

**Level 3: Fully Autonomous (Future State)**
- Agent manages full lifecycle
- Agent promotes to production after soak
- Human oversight via metrics/alerts only

### Agent-Accessible Telemetry

**1. CI Status via GitHub API**

```python
# Agent checks CI status before proceeding
import requests

def check_ci_status(repo, pr_number, github_token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/checks"
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(url, headers=headers)
    checks = response.json()["check_runs"]
    
    all_passed = all(check["conclusion"] == "success" for check in checks)
    return all_passed
```

**2. Deployment Health via /health Endpoint**

```python
def validate_deployment(environment_url):
    import time
    for attempt in range(30):
        try:
            response = requests.get(f"{environment_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                return health["status"] == "healthy"
        except:
            time.sleep(10)
    return False
```

**3. Error Rate Monitoring**

```python
# Agent queries Redis for error rate
def check_error_rate(redis_host, timeframe_minutes=10):
    import redis
    r = redis.Redis(host=redis_host, db=0)
    
    # Count error keys in last N minutes
    pattern = "error:*"
    errors = r.scan_iter(match=pattern)
    
    count = sum(1 for _ in errors)
    threshold = 50  # Max errors in timeframe
    
    return count < threshold
```

### Agent Decision Framework

**When agent encounters CI failure:**

```python
def handle_ci_failure(failure_logs):
    if "SyntaxError" in failure_logs:
        return "FIXABLE: Syntax error - auto-fix and re-push"
    
    elif "ImportError" in failure_logs:
        return "FIXABLE: Missing dependency - update requirements"
    
    elif "AssertionError" in failure_logs:
        if "expected" in failure_logs and "got" in failure_logs:
            return "FIXABLE: Test expectation mismatch - update test or code"
        else:
            return "INVESTIGATE: Logic error - analyze test context"
    
    elif "timeout" in failure_logs.lower():
        return "INVESTIGATE: Performance regression or infrastructure issue"
    
    else:
        return "ESCALATE: Unknown failure - human review required"
```

---

## Automated Agent Task Orchestration

### Overview

Building on the [god-tier prompting strategy](../god-tier-prompting-strategy.md) and [work package framework](../work-packages/README.md), we can implement automated agent task orchestration using today's LLMs. The system uses a **Lead-Worker architecture** where a lead agent decomposes work into atomic tasks and coordinates worker agents executing those tasks in parallel.

**Key insight:** Modern LLMs (Claude Sonnet 4, GPT-4, etc.) can reliably orchestrate complex workflows when given:
1. Explicit task definitions (standardized prompts)
2. Observable system state (CI status, deployment health, test results)
3. Decision frameworks (deterministic failure classification)
4. Feedback loops (agent-contributed improvements to prompts)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Lead Agent (Orchestrator)                │
│  - Monitors GitHub webhooks (PR events, CI status)          │
│  - Decomposes failures into atomic tasks                    │
│  - Generates standardized prompts from templates            │
│  - Dispatches tasks to worker agent pool                    │
│  - Aggregates results and updates work package tracker      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Task Queue (Redis DB 10)                │
│  Schema: {                                                  │
│    "task_id": "ci-fix-001",                                 │
│    "type": "fix_test_failure",                              │
│    "priority": "high",                                      │
│    "prompt": "<standardized prompt with context>",          │
│    "inputs": ["test logs", "source files"],                 │
│    "deliverables": ["fixed code", "passing tests"],         │
│    "validation": ["wctl run-pytest tests/path"],            │
│    "timeout_minutes": 30,                                   │
│    "retry_count": 0,                                        │
│    "created_at": "2025-10-26T10:30:00Z"                     │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┬─────────────┐
                ▼                           ▼             ▼
       ┌────────────────┐         ┌────────────────┐  ┌────────────────┐
       │ Worker Agent 1 │         │ Worker Agent 2 │  │ Worker Agent N │
       │  - Pull task   │         │  - Pull task   │  │  - Pull task   │
       │  - Execute     │         │  - Execute     │  │  - Execute     │
       │  - Validate    │         │  - Validate    │  │  - Validate    │
       │  - Report      │         │  - Report      │  │  - Report      │
       └────────────────┘         └────────────────┘  └────────────────┘
```

### Implementation Components

#### 1. Lead Agent Service (`wepppy/agents/lead_agent.py`)

```python
"""
Lead agent that monitors CI/CD pipeline and orchestrates worker agents.
Runs as a persistent service with Redis-backed state.
"""
import redis
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from github import Github
from wepppy.nodb.base import NoDbBase

class LeadAgent:
    """Orchestrates automated agent tasks for CI/CD pipeline"""
    
    def __init__(self, redis_host: str = 'localhost', github_token: str = None):
        self.redis = redis.Redis(host=redis_host, db=10, decode_responses=True)
        self.github = Github(github_token)
        self.repo = self.github.get_repo("rogerlew/wepppy")
    
    def monitor_ci_events(self):
        """Poll GitHub for CI status changes"""
        # In production, use webhooks instead of polling
        while True:
            prs = self.repo.get_pulls(state='open')
            for pr in prs:
                # Check CI status
                checks = pr.get_commits().reversed[0].get_check_runs()
                for check in checks:
                    if check.conclusion == 'failure':
                        self.handle_ci_failure(pr, check)
            time.sleep(60)  # Poll every minute
    
    def handle_ci_failure(self, pr, check):
        """Decompose CI failure into actionable tasks"""
        logs = self.fetch_ci_logs(check)
        failure_type = self.classify_failure(logs)
        
        if failure_type in ['FIXABLE']:
            task = self.generate_fix_task(pr, check, logs, failure_type)
            self.enqueue_task(task)
        elif failure_type in ['INVESTIGATE']:
            task = self.generate_investigation_task(pr, check, logs)
            self.enqueue_task(task)
        else:  # ESCALATE
            self.notify_human(pr, check, logs)
    
    def classify_failure(self, logs: str) -> str:
        """Classify failure using decision framework"""
        if "SyntaxError" in logs:
            return "FIXABLE"
        elif "ImportError" in logs:
            return "FIXABLE"
        elif "AssertionError" in logs and "expected" in logs:
            return "FIXABLE"
        elif "timeout" in logs.lower():
            return "INVESTIGATE"
        else:
            return "ESCALATE"
    
    def generate_fix_task(self, pr, check, logs, failure_type) -> Dict:
        """Generate standardized task from prompt template"""
        # Load prompt template
        template = self.load_template('ci_fix_task.prompt.md')
        
        # Populate with context
        prompt = template.format(
            pr_number=pr.number,
            pr_title=pr.title,
            check_name=check.name,
            failure_logs=logs,
            failure_type=failure_type,
            branch=pr.head.ref,
            repo="rogerlew/wepppy"
        )
        
        return {
            "task_id": f"ci-fix-{pr.number}-{check.id}",
            "type": "fix_test_failure",
            "priority": "high",
            "prompt": prompt,
            "inputs": {
                "pr_number": pr.number,
                "branch": pr.head.ref,
                "logs": logs
            },
            "deliverables": [
                "Fixed code committed to branch",
                "Tests passing in CI",
                "Comment on PR with fix summary"
            ],
            "validation": [
                "wctl run-pytest tests --maxfail=1",
                "git diff --name-only | wc -l <= 5"  # Max 5 files changed
            ],
            "timeout_minutes": 30,
            "retry_count": 0,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def enqueue_task(self, task: Dict):
        """Push task to Redis queue"""
        task_json = json.dumps(task)
        self.redis.lpush("agent:tasks:pending", task_json)
        self.redis.hset(f"agent:task:{task['task_id']}", mapping=task)
        
        # Publish to agent workers
        self.redis.publish("agent:tasks:new", task['task_id'])
    
    def monitor_task_completion(self):
        """Watch for completed tasks and update GitHub"""
        pubsub = self.redis.pubsub()
        pubsub.subscribe("agent:tasks:completed")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                task_id = message['data']
                task = self.redis.hgetall(f"agent:task:{task_id}")
                self.handle_task_completion(task)
    
    def handle_task_completion(self, task: Dict):
        """Process completed task results"""
        pr_number = task['inputs']['pr_number']
        pr = self.repo.get_pull(pr_number)
        
        if task['status'] == 'success':
            pr.create_issue_comment(
                f"🤖 Automated fix applied by agent\n\n"
                f"**Task:** {task['type']}\n"
                f"**Changes:** {task['changes_summary']}\n"
                f"**Validation:** ✅ All checks passed\n\n"
                f"Please review and merge if acceptable."
            )
        else:
            pr.create_issue_comment(
                f"🤖 Agent attempted fix but encountered issues\n\n"
                f"**Task:** {task['type']}\n"
                f"**Error:** {task['error_message']}\n\n"
                f"Human review required."
            )
```

#### 2. Worker Agent Service (`wepppy/agents/worker_agent.py`)

```python
"""
Stateless worker agents that pull tasks from Redis queue and execute them.
Each worker is a fresh LLM instance with no memory of previous tasks.
"""
import redis
import json
import subprocess
from typing import Dict

class WorkerAgent:
    """Executes atomic tasks dispatched by lead agent"""
    
    def __init__(self, agent_id: str, redis_host: str = 'localhost'):
        self.agent_id = agent_id
        self.redis = redis.Redis(host=redis_host, db=10, decode_responses=True)
        self.working_dir = "/tmp/agent_workspace"
    
    def run(self):
        """Main worker loop - pull tasks and execute"""
        pubsub = self.redis.pubsub()
        pubsub.subscribe("agent:tasks:new")
        
        print(f"Worker {self.agent_id} ready")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                task_id = message['data']
                task = self.claim_task(task_id)
                if task:
                    self.execute_task(task)
    
    def claim_task(self, task_id: str) -> Optional[Dict]:
        """Atomically claim task using Redis lock"""
        lock_key = f"agent:task:{task_id}:lock"
        if self.redis.set(lock_key, self.agent_id, nx=True, ex=1800):
            task_json = self.redis.rpop("agent:tasks:pending")
            if task_json:
                return json.loads(task_json)
        return None
    
    def execute_task(self, task: Dict):
        """Execute task following standardized prompt"""
        task_id = task['task_id']
        
        try:
            # Update status
            self.redis.hset(f"agent:task:{task_id}", "status", "running")
            self.redis.hset(f"agent:task:{task_id}", "worker_id", self.agent_id)
            
            # Setup workspace
            self.setup_workspace(task)
            
            # Execute prompt (this is where LLM API call happens)
            result = self.execute_prompt(task['prompt'], task)
            
            # Validate deliverables
            validation_passed = self.validate_deliverables(
                task['deliverables'], 
                task['validation']
            )
            
            if validation_passed:
                self.redis.hset(f"agent:task:{task_id}", "status", "success")
                self.redis.hset(f"agent:task:{task_id}", "result", json.dumps(result))
                self.redis.publish("agent:tasks:completed", task_id)
            else:
                raise Exception("Validation failed")
                
        except Exception as e:
            self.redis.hset(f"agent:task:{task_id}", "status", "failed")
            self.redis.hset(f"agent:task:{task_id}", "error", str(e))
            self.redis.publish("agent:tasks:failed", task_id)
            
            # Retry logic
            retry_count = int(task.get('retry_count', 0))
            if retry_count < 2:
                task['retry_count'] = retry_count + 1
                self.redis.lpush("agent:tasks:pending", json.dumps(task))
    
    def execute_prompt(self, prompt: str, task: Dict) -> Dict:
        """
        Execute LLM prompt and return result.
        In production, this calls OpenAI/Anthropic API.
        """
        # Pseudo-code - actual implementation depends on LLM provider
        from anthropic import Anthropic
        
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Build messages with context
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Stream response and execute tool calls
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=messages,
            tools=self.get_available_tools()
        )
        
        # Agent executes file edits, runs tests, commits changes
        # Returns summary of actions taken
        return {
            "changes": response.content,
            "files_modified": ["list", "of", "files"],
            "validation_output": "test results"
        }
    
    def validate_deliverables(self, deliverables: List[str], 
                             validation_commands: List[str]) -> bool:
        """Run validation commands to verify deliverables"""
        for cmd in validation_commands:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True,
                cwd=self.working_dir
            )
            if result.returncode != 0:
                return False
        return True
```

#### 3. Prompt Templates (`docs/prompt_templates/ci_fix_task.prompt.md`)

```markdown
# CI Test Failure Fix Task

**Mission:** Fix failing test in PR #{pr_number}

**Context:**
- PR: {pr_title}
- Branch: `{branch}`
- Check: {check_name}
- Failure Type: {failure_type}

**Failure Logs:**
```
{failure_logs}
```

**Your Task:**
1. Checkout branch `{branch}` from `{repo}`
2. Analyze failure logs to identify root cause
3. Implement minimal fix (≤5 files changed)
4. Run validation: `wctl run-pytest tests --maxfail=1`
5. Commit changes with message: "Agent fix: {failure_type} in {check_name}"
6. Push to branch

**Deliverables:**
- Fixed code committed to branch
- All tests passing locally
- Summary comment with:
  - Root cause analysis
  - Files changed
  - Validation results

**Validation Gates:**
- [ ] Tests pass: `wctl run-pytest tests`
- [ ] No new lint errors: `wctl run-npm lint`
- [ ] Max 5 files changed

**Constraints:**
- Do NOT modify test expectations unless failure is in test itself
- Do NOT make unrelated changes
- Do NOT push directly to master
- If unclear, ESCALATE to human review

**Reference Documentation:**
- AGENTS.md: Development patterns
- tests/AGENTS.md: Testing conventions
- docs/dev-notes/cicd-strategy.md: CI/CD workflow
```

#### 4. Task Monitoring Dashboard (`wepppy/agents/dashboard.py`)

```python
"""
Web dashboard for monitoring agent task execution.
Shows task queue, worker status, success/failure rates.
"""
from flask import Blueprint, render_template, jsonify
import redis

agent_dashboard = Blueprint('agent_dashboard', __name__)

@agent_dashboard.route('/agents/dashboard')
def dashboard():
    """Render agent orchestration dashboard"""
    return render_template('agents/dashboard.html')

@agent_dashboard.route('/agents/api/status')
def get_status():
    """Get current agent system status"""
    r = redis.Redis(host='localhost', db=10, decode_responses=True)
    
    # Count tasks by status
    pending = r.llen("agent:tasks:pending")
    
    # Get active workers
    workers = []
    for key in r.scan_iter("agent:task:*:lock"):
        worker_id = r.get(key)
        if worker_id:
            workers.append(worker_id)
    
    # Recent completions
    completed_keys = list(r.scan_iter("agent:task:*"))
    recent_tasks = []
    for key in completed_keys[-20:]:
        task = r.hgetall(key)
        if task:
            recent_tasks.append(task)
    
    return jsonify({
        "pending_tasks": pending,
        "active_workers": len(set(workers)),
        "recent_tasks": recent_tasks,
        "success_rate": calculate_success_rate(recent_tasks)
    })

def calculate_success_rate(tasks):
    if not tasks:
        return 0
    successes = sum(1 for t in tasks if t.get('status') == 'success')
    return (successes / len(tasks)) * 100
```

### Deployment

**Docker Compose service additions:**

```yaml
# docker/docker-compose.dev.yml
services:
  agent-lead:
    build:
      context: ..
      dockerfile: docker/Dockerfile.dev
    command: python -m wepppy.agents.lead_agent
    environment:
      - REDIS_HOST=redis
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - redis
    restart: unless-stopped

  agent-worker-1:
    build:
      context: ..
      dockerfile: docker/Dockerfile.dev
    command: python -m wepppy.agents.worker_agent --id worker-1
    environment:
      - REDIS_HOST=redis
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - redis
    restart: unless-stopped
  
  # Scale workers as needed
  agent-worker-2:
    extends: agent-worker-1
    command: python -m wepppy.agents.worker_agent --id worker-2
```

### Operational Metrics

**Key metrics to track:**

1. **Task throughput:** Tasks completed per hour
2. **Success rate:** % of tasks that pass validation on first attempt
3. **Retry rate:** % of tasks requiring retries
4. **Escalation rate:** % of tasks escalated to humans
5. **Time to resolution:** Minutes from failure to fix deployed
6. **Cost per task:** LLM API costs per task type

**Dashboard queries:**

```python
# Success rate by task type
def get_success_rate_by_type():
    r = redis.Redis(host='localhost', db=10)
    tasks = get_all_tasks()
    
    by_type = {}
    for task in tasks:
        task_type = task['type']
        if task_type not in by_type:
            by_type[task_type] = {'success': 0, 'total': 0}
        
        by_type[task_type]['total'] += 1
        if task['status'] == 'success':
            by_type[task_type]['success'] += 1
    
    return {
        t: (stats['success'] / stats['total']) * 100 
        for t, stats in by_type.items()
    }
```

### Human Oversight Integration

**Approval gates for high-risk tasks:**

```python
REQUIRES_HUMAN_APPROVAL = [
    'database_migration',
    'api_contract_change',
    'security_patch',
    'production_deployment'
]

def requires_approval(task_type: str) -> bool:
    return task_type in REQUIRES_HUMAN_APPROVAL

# In worker agent
if requires_approval(task['type']):
    result = execute_task_dry_run(task)
    request_human_approval(task, result)
    wait_for_approval(task['task_id'])
    # Continue only after approval
```

**Notification channels:**

```python
def notify_human(event: str, context: Dict):
    """Send notifications via multiple channels"""
    # Email
    send_email(
        to="roger@wepppy.org",
        subject=f"Agent Alert: {event}",
        body=json.dumps(context, indent=2)
    )
    
    # Slack (if configured)
    if SLACK_WEBHOOK:
        requests.post(SLACK_WEBHOOK, json={
            "text": f"🤖 Agent event: {event}",
            "attachments": [{"text": str(context)}]
        })
    
    # SMS for critical failures (via Twilio)
    if event == "CRITICAL":
        send_sms("+1234567890", f"Agent system critical: {context['error']}")
```

### Future Enhancements

**Phase 2 (Agent self-improvement):**
- Agents analyze their own failure patterns
- Automatically update prompt templates based on lessons learned
- Generate new test cases when bugs are found

**Phase 3 (Multi-agent collaboration):**
- Lead agent decomposes large features into parallel sub-tasks
- Worker agents communicate via shared Redis state
- Agents review each other's code before committing

**Phase 4 (Autonomous deployment):**
- Agents monitor production metrics post-deployment
- Automatic rollback if error rate exceeds threshold
- Agents propose optimizations based on performance telemetry

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2) 🎯 **Start Here**

**Goals:**
- Setup GitHub self-hosted runner
- Create basic CI workflows
- Integrate existing tests into CI

**Tasks:**
1. [ ] Install and configure GitHub Actions runner on forest
2. [ ] Setup SSH keys for deployment access
3. [ ] Create `.github/workflows/pr.yml` (lint + test)
4. [ ] Add GitHub Secrets for credentials
5. [ ] Test PR validation workflow with sample PR
6. [ ] Document runner maintenance in `docs/dev-notes/github-runner-ops.md`

**Acceptance Criteria:**
- PR checks run automatically on every push
- Linters catch style violations
- Test failures block merge
- Agent can monitor CI status via GitHub API

**Estimated Effort:** 2-3 days (agent + Roger)

### Phase 2: Test Coverage Expansion (Week 3-4)

**Goals:**
- Fill critical test gaps
- Improve integration test coverage
- Add performance benchmarks

**Tasks:**
1. [ ] Implement integration tests for full run workflow
2. [ ] Add database migration tests
3. [ ] Create post-deployment smoke test script
4. [ ] Add performance regression benchmarks
5. [ ] Wire smoke tests into CI pipeline
6. [ ] Achieve 75%+ coverage on core modules

**Acceptance Criteria:**
- Integration tests cover happy path + 3 error scenarios
- Smoke tests validate deployments
- Performance baselines documented
- Coverage report in CI artifacts

**Estimated Effort:** 5-7 days (primarily agent work)

### Phase 3: Automated Deployment to Test-Prod (Week 5-6)

**Goals:**
- Auto-deploy master to forest1
- Health check validation
- Deployment notifications

**Tasks:**
1. [ ] Create `.github/workflows/main.yml` (build + deploy)
2. [ ] Setup GitHub Container Registry push
3. [ ] Implement SSH deployment to forest1
4. [ ] Add health check validation post-deploy
5. [ ] Configure deployment notifications (Slack/email)
6. [ ] Test rollback procedure

**Acceptance Criteria:**
- Master branch merges trigger test-prod deployment
- Deployment fails if health checks don't pass
- Logs/metrics accessible for debugging
- Rollback can be executed in < 5 minutes

**Estimated Effort:** 3-4 days

### Phase 4: Production Deployment Pipeline (Week 7-8)

**Goals:**
- Manual production deployment workflow
- Blue-green deployment strategy
- Automatic rollback on failure

**Tasks:**
1. [ ] Create `.github/workflows/deploy-prod.yml`
2. [ ] Implement pre-deployment database backup
3. [ ] Add health check with auto-rollback
4. [ ] Setup production monitoring
5. [ ] Document release process
6. [ ] Test full release cycle (test-prod → prod)

**Acceptance Criteria:**
- Production deployments require manual trigger
- Database backed up before every deploy
- Failed deployments auto-rollback
- Release process documented and tested

**Estimated Effort:** 4-5 days

### Phase 5: Agent Autonomy Features (Week 9-10)

**Goals:**
- Agent can monitor deployments
- Agent can trigger rollbacks
- Agent can manage release cycle

**Tasks:**
1. [ ] Build agent API client for GitHub Actions
2. [ ] Create agent monitoring dashboard
3. [ ] Implement agent decision framework
4. [ ] Add agent-triggered deployment capability
5. [ ] Setup alert routing to agent
6. [ ] Document agent operational procedures

**Acceptance Criteria:**
- Agent can query CI status programmatically
- Agent can detect deployment issues
- Agent can execute rollback via API
- Agent decision logs auditable

**Estimated Effort:** 5-7 days

### Phase 6: Advanced Features (Week 11+)

**Optional enhancements:**
- [ ] Blue-green deployment for zero downtime
- [ ] Canary deployments (10% traffic → 50% → 100%)
- [ ] A/B testing infrastructure
- [ ] Chaos engineering tests
- [ ] Load testing automation
- [ ] Multi-region deployment (future scaling)

---

## Operational Playbooks

### Playbook 1: Runner Maintenance

**Check Runner Health:**
```bash
# SSH to forest.bearhive.internal
ssh forest

# Check runner service status
systemctl status actions.runner.rogerlew-wepppy.forest-runner-1.service

# View recent logs
journalctl -u actions.runner.rogerlew-wepppy.forest-runner-1.service -n 100

# Check disk space (runners accumulate artifacts)
df -h /home/roger/actions-runner/_work

# Cleanup old artifacts (safe to run)
cd /home/roger/actions-runner/_work
find . -name "*.log" -mtime +7 -delete
find . -type d -empty -delete
```

**Restart Runner:**
```bash
sudo systemctl restart actions.runner.rogerlew-wepppy.forest-runner-1.service
sudo systemctl status actions.runner.rogerlew-wepppy.forest-runner-1.service
```

**Update Runner:**
```bash
# Stop service
sudo systemctl stop actions.runner.rogerlew-wepppy.forest-runner-1.service

# Download latest version
cd /home/roger/actions-runner
curl -o actions-runner-linux-x64-<VERSION>.tar.gz \
  -L https://github.com/actions/runner/releases/download/v<VERSION>/actions-runner-linux-x64-<VERSION>.tar.gz

# Extract and reconfigure
tar xzf ./actions-runner-linux-x64-<VERSION>.tar.gz
./config.sh --url https://github.com/rogerlew/wepppy

# Restart service
sudo systemctl start actions.runner.rogerlew-wepppy.forest-runner-1.service
```

### Playbook 2: Investigate CI Failure

**Step 1: Identify Failure**
```bash
# Via GitHub UI: Check "Actions" tab for failed run
# Or via CLI:
gh run list --workflow=pr.yml --limit 5

# Get details
gh run view <RUN_ID>
```

**Step 2: Download Logs**
```bash
gh run download <RUN_ID>
cd <RUN_ID>
cat logs/<JOB_NAME>/*.txt
```

**Step 3: Reproduce Locally**
```bash
# Checkout PR branch
gh pr checkout <PR_NUMBER>

# Run same commands as CI
wctl run-pytest tests -m "unit" --maxfail=1

# Check environment differences
wctl exec weppcloud env | sort > ci-env.txt
env | sort > local-env.txt
diff ci-env.txt local-env.txt
```

**Step 4: Fix and Retest**
```bash
# Make fix
git add <files>
git commit -m "Fix CI failure: <description>"
git push

# Monitor CI
gh run watch
```

### Playbook 3: Emergency Production Rollback

**Trigger:** Production error rate spiking, users reporting issues

**Step 1: Confirm Issue**
```bash
# Check health endpoint
curl -f https://wepp.cloud/health || echo "Health check FAILED"

# Check logs for errors
ssh wepp1 "docker compose -f /opt/wepppy/docker/docker-compose.prod.yml \
  logs --since 10m weppcloud | grep -i error | tail -20"
```

**Step 2: Execute Rollback**
```bash
# Identify last known good version
ssh wepp1 "docker images | grep wepppy"

# Rollback to previous image
ssh wepp1 'cd /opt/wepppy && \
  export WEPPCLOUD_IMAGE=ghcr.io/rogerlew/wepppy:prod-<PREVIOUS_TAG> && \
  docker compose -f docker/docker-compose.prod.yml up -d weppcloud && \
  docker compose -f docker/docker-compose.prod.yml restart caddy'

# Verify health restored
for i in {1..10}; do
  curl -f https://wepp.cloud/health && echo "✅ Healthy" && break
  sleep 5
done
```

**Step 3: Notify and Document**
```bash
# Create incident report
cat > /tmp/incident.md <<EOF
# Production Incident: $(date)

## Timeline
- $(date -d '10 minutes ago'): Issue detected
- $(date -d '5 minutes ago'): Rollback initiated
- $(date): Service restored

## Root Cause
<To be investigated>

## Action Items
- [ ] Investigate root cause
- [ ] Add regression test
- [ ] Update deployment checklist
EOF

# Notify team (Slack, email, etc.)
```

### Playbook 4: Deploy Hotfix to Production

**Scenario:** Critical bug in production, bypassing normal soak period

**Step 1: Create Hotfix**
```bash
# Branch from production tag
git checkout v2025.10.1
git checkout -b hotfix/urgent-fix

# Make minimal fix
# ... edit files ...

git add .
git commit -m "Hotfix: <description>"
git push origin hotfix/urgent-fix
```

**Step 2: Fast-Track CI**
```bash
# Create PR with hotfix label
gh pr create --base master --head hotfix/urgent-fix \
  --title "HOTFIX: Urgent fix" \
  --label "hotfix" \
  --body "Emergency fix for production issue"

# Monitor CI (should pass if fix is good)
gh run watch
```

**Step 3: Deploy Directly to Production**
```bash
# Merge PR
gh pr merge hotfix/urgent-fix --squash

# Get commit SHA
SHA=$(git rev-parse --short HEAD)

# Deploy to production immediately
gh workflow run deploy-prod.yml \
  -f image_tag=master-$SHA \
  -f skip_smoke_tests=true  # Only in true emergency

# Monitor deployment
gh run watch
```

**Step 4: Verify Fix**
```bash
# Check production health
curl -f https://wepp.cloud/health

# Verify bug is fixed (manual test)
# ... test specific functionality ...

# Monitor for 30 minutes
watch -n 60 'curl -s https://wepp.cloud/health | jq'
```

---

## CodeQL Action v3 Migration & SARIF Handling

### Background: CodeQL Action v2 Retirement (January 2025)

The CodeQL Action v2, including the `upload-sarif` component, was officially retired on **January 10, 2025**, following:
- Deprecation announcement in **January 2024**
- Planned end-of-support date in **December 2024**

**Retirement Rationale:**
- **GHES Compatibility:** Aligned with deprecation of older GitHub Enterprise Server versions (e.g., GHES 3.11), where CodeQL bundles shipped with deprecated GHES releases are retired to maintain security and compatibility.
- **Security & Maintenance:** Ensures users migrate to actively maintained versions that incorporate bug fixes, security enhancements, and performance improvements.
- **Risk Reduction:** Eliminates exposure to unpatched vulnerabilities in unmaintained tooling.

**Impact:** Workflows using v2 now fail with errors prompting updates to v3. No further updates or support are provided for v2.

### CodeQL Action v3 Specification

The v3 specification builds on v2 with several key updates focused on reliability, consistency, and enhanced SARIF upload handling:

#### 1. SARIF Post-Processing Behavior (v3.31.0+)

Post-processing steps (e.g., adding fingerprints for alert tracking across runs) are **always applied** to generated SARIF files during `analyze` or `upload-sarif` steps, regardless of whether an upload occurs.

- **Previous Behavior (v2):** Post-processing was conditional on upload intent.
- **New Behavior (v3):** Ensures more consistent file preparation, but may increase resource usage for custom workflows where uploads are skipped (e.g., via the `upload` input in `analyze`).
- **Impact:** No direct change to `upload-sarif` itself, but workflows benefit from uniform file structure.

#### 2. Handling Multiple SARIF Runs (Breaking Change - July 2025)

Starting **July 22, 2025**, code scanning **no longer automatically combines** multiple SARIF runs within the same file if they share the same tool and category properties.

- **Previous Behavior (v2):** Multiple runs with the same tool/category were automatically merged.
- **New Behavior (v3):** Users must upload separate runs individually or adjust SARIF generation to avoid duplication.
- **Error Message:** `"multiple SARIF runs with the same category"` if not handled correctly.
- **Migration Strategy:** Review SARIF generation logic to ensure single-run files or unique categories per run.

#### 3. CodeQL Bundle and Tooling Updates

v3 bumps the minimum CodeQL CLI bundle to versions like **2.17.6** (with defaults up to **2.23.3**), incorporating:
- Newer language support
- Query improvements
- Bug fixes
- Enhanced analysis accuracy for recent programming languages and frameworks

#### 4. New Experimental Features

- **`setup-codeql` Action:** Installs the CodeQL CLI without database initialization, useful for custom tooling or non-production scenarios.

#### 5. Permissions and Integration Requirements

v3 enforces stricter permissions and provides better error handling:

| Requirement | Details |
|-------------|---------|
| **Permissions** | `security_events: write` required for uploads |
| **Upload Methods** | GitHub Actions, API, or CodeQL CLI |
| **SARIF Format** | Must comply with SARIF 2.1.0 specification |
| **Required Fields** | At least one `run` object, valid `commit_sha` and `ref` |
| **Error Handling** | Clear error messages for "Resource not accessible" or "Not Found" (often due to missing repo settings or invalid SARIF structures) |

#### 6. Migration Path from v2 to v3

**Update Workflow YAML:**
```yaml
# Before (v2)
      - name: Upload SARIF Results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: results.sarif

# After (v3)
- name: Upload SARIF Results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

**Testing Checklist:**
- [ ] Validate SARIF output against SARIF 2.1.0 specification
- [ ] Ensure single-run files or unique categories per run
- [ ] Verify `commit_sha` and `ref` are correctly set
- [ ] Test for breaking changes (post-processing, multi-run handling)
- [ ] Review repository settings: Code Scanning must be enabled
- [ ] Check permissions: `security_events: write` in workflow

### SARIF Validation Best Practices

To prevent upload failures, workflows should validate SARIF files before upload:

```yaml
- name: Generate SARIF Report
  run: wctl doc-lint --format sarif > docs-lint.sarif
  continue-on-error: true

- name: Validate SARIF Output
  run: |
    # Check if file is empty or missing
    if [ ! -s docs-lint.sarif ]; then
      echo "Warning: SARIF file is empty or missing"
      echo '{"version": "2.1.0", "runs": []}' > docs-lint.sarif
    fi
    
    # Validate JSON syntax
    if ! jq empty docs-lint.sarif 2>/dev/null; then
      echo "Error: Invalid JSON in SARIF file"
      echo '{"version": "2.1.0", "runs": []}' > docs-lint.sarif
    fi

- name: Upload SARIF to Code Scanning
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: docs-lint.sarif
    category: documentation
```

**Key Validation Steps:**
1. **File Existence:** Check if SARIF file exists and is non-empty (`[ ! -s file ]`)
2. **JSON Syntax:** Validate with `jq empty` to catch malformed JSON
3. **Minimal Valid SARIF:** Create fallback with `{"version": "2.1.0", "runs": []}` if generation fails
4. **Category Uniqueness:** Assign unique `category` values to prevent merge conflicts

### Third-Party Tool Compatibility

When using third-party tools (e.g., Trivy, Anchore, ESLint) that generate SARIF:

```yaml
- name: Run Trivy Security Scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'weppcloud:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Validate Trivy SARIF
  run: |
    if [ ! -s trivy-results.sarif ]; then
      echo '{"version": "2.1.0", "runs": []}' > trivy-results.sarif
    fi

- name: Upload Trivy Results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: trivy-results.sarif
    category: container-security
```

**Common Issues:**
- **Empty Runs:** Tool finds no issues but produces invalid SARIF (missing `runs` array)
- **Category Conflicts:** Multiple scans with same category in single workflow
- **Large Files:** SARIF files exceeding GitHub's size limits (10 MB recommended maximum)

### Wepppy Implementation Status (2025-10-26)

| Workflow | Status | Notes |
|----------|--------|-------|
| `docs-quality.yml` | ✅ Migrated to v3 | Includes SARIF validation (empty file handling) |
| `pr.yml` (planned) | ⏳ Pending | Will use v3 from initial implementation |
| `main.yml` (planned) | ⏳ Pending | Container scans will use v3 with Trivy |

**References:**
- [CodeQL Action Repository](https://github.com/github/codeql-action) - Clone available at `/workdir/codeql-action`
- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [GitHub Code Scanning Documentation](https://docs.github.com/en/code-security/code-scanning)

---

## Summary & Next Steps

### Current State → Target State

**Before CI/CD:**
- ❌ Manual deployments via SSH + git pull
- ❌ No automated testing between environments
- ❌ Configuration drift
- ❌ No rollback strategy
- ❌ Breaking changes reach production

**After CI/CD:**
- ✅ Automated testing on every PR
- ✅ Test-production auto-deploys on merge
- ✅ Production deploys with health checks + auto-rollback
- ✅ Configuration managed via GitHub Secrets
- ✅ Agent-driven development with safety nets

### Immediate Actions (Roger + Agent)

**Week 1 (Roger):**
1. Setup GitHub self-hosted runner on forest
2. Configure SSH keys for deployment access
3. Add GitHub Secrets for prod credentials

**Week 2 (Agent):**
1. Create initial `.github/workflows/pr.yml`
2. Test PR validation workflow
3. Document runner operations

**Week 3-4 (Agent):**
1. Expand test coverage (integration, smoke, migrations)
2. Wire tests into CI pipeline
3. Achieve 75%+ coverage

**Week 5+ (Agent + Roger):**
1. Implement test-prod auto-deploy
2. Build production deployment workflow
3. Test full release cycle

### Success Metrics

**Operational Metrics:**
- Time to deploy: < 10 minutes (target)
- Failed deployments: < 5% (target)
- Rollback time: < 5 minutes
- Test coverage: > 75% (target)

**Quality Metrics:**
- Bugs reaching production: -80%
- Mean time to recovery: < 15 minutes
- Deployment frequency: 2-3x per week (sustainable)

**Agent Autonomy Metrics:**
- PRs requiring human review: < 20% (target)
- Agent-triggered rollbacks: Successfully handled
- Agent decision accuracy: > 95%

---

## References

- [GitHub Actions: Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Docker Compose Production Guide](../../docker/README.md)
- [Test Suite Documentation](../../tests/README.md)
- [Agent Development Manifesto](../../AGENTIC_AI_SYSTEMS_MANIFESTO.md)
- [Work Packages: Documentation Tooling](../work-packages/20251025_markdown_doc_toolkit/)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-10-26  
**Maintainer:** AI Agents (with Roger oversight)  
**Review Cadence:** Quarterly or after major infrastructure changes
