# CI Samurai
> Automated regression fixer for WEPPcloud test suite
> **Status: Functional Beta** | **Trigger: Nightly GitHub Actions** | **Architecture: Multi-Agent + Redis Queue**

**See also:** [AGENTS.md](/workdir/wepppy/AGENTS.md#ci-samurai-agents) for CAO integration details

## Overview

CI Samurai is an autonomous test failure remediation system that converts failing pytest tests into validated fixes (via pull requests) or structured diagnostic reports (via GitHub issues). Operating as a nightly GitHub Actions workflow with distributed agent orchestration, it bridges CI infrastructure across three build hosts (nuc1, nuc2, nuc3) and leverages GPT-5-Codex agents through the CLI Agent Orchestrator (CAO) to analyze, fix, and validate test failures—all without human intervention.

**Key Innovation**: Fresh agent per failure with strict safety policies (allowlist/denylist, validation-before-merge, auto-rollback on validation failure).

### What Problem Does This Solve?

- **Nightly test regressions** accumulate and block development
- **Manual triage** of 400+ tests is time-consuming and error-prone
- **Flaky tests** obscure real issues and waste CI cycles
- **Collection errors** (import failures, missing dependencies) break entire test suites before any tests run
- **Context loss** between failure detection and fix attempts

### Who Uses This?

- **Development team** receives automated PRs with validated fixes
- **Hydrologists/domain experts** benefit from stable test suite without debugging overhead
- **DevOps/infra team** gets structured issue reports for environment problems
- **AI coding agents** learn from fix patterns and improve over time

### Key Capabilities

1. **Automated Triage** across distributed hosts (nuc1 → nuc2 → nuc3)
2. **Failure Parsing** extracts test failures AND collection errors from pytest output
3. **Agent-Per-Error** model spawns fresh GPT-5-Codex sessions for each failure
4. **Validation-Before-Merge** runs test on clean node (nuc2) before opening PR
5. **Policy Enforcement** via allowlist/denylist prevents dangerous edits
6. **Observability** with full agent transcripts, RESULT_JSON artifacts, and GitHub labels

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ GitHub Actions (self-hosted runner on forest.local)                 │
│                                                                      │
│  1. Checkout repo                                                   │
│  2. SSH to nuc1 → Run full pytest suite → triage.txt               │
│  3. Parse triage.txt → failures.jsonl (test failures + collection)  │
│  4. For each failure in failures.jsonl:                             │
│     ├─ Create CAO session (http://forest:9889)                     │
│     ├─ Send structured message to ci_samurai_fixer agent           │
│     ├─ Poll for RESULT_JSON (timeout: 120s)                        │
│     ├─ Agent validates fix on nuc2 via SSH + wctl run-pytest       │
│     ├─ Agent opens PR (success) or issue (blocked/uncertain)       │
│     └─ Persist agent transcript to agent_logs/                     │
│  5. Upload artifacts: logs, failures.jsonl, agent transcripts       │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| **Workflow** | `.github/workflows/ci-samurai-nightly-ssh.yml` | Orchestrates nightly run |
| **Makefile** | `Makefile` (target: `ci-dryrun`) | Coordinates multi-host execution |
| **Dryrun Script** | `services/cao/scripts/ci_samurai_dryrun.sh` | Runs triage/validate/flake checks |
| **Parser** | `services/cao/ci-samurai/parse_pytest_log.py` | Converts pytest logs → JSONL |
| **Fixer Loop** | `services/cao/ci-samurai/run_fixer_loop.py` | Agent orchestration + validation |
| **Agent Profiles** | `services/cao/src/cli_agent_orchestrator/agent_store/` | CAO agent behavior definitions |
| **CAO Server** | `http://forest:9889` (main), `http://nuc2:9889` (infra) | CLI Agent Orchestrator endpoints |

### Data Flow

```
triage.txt (pytest output)
  ↓ parse_pytest_log.py
failures.jsonl (test failures + collection errors)
  ↓ run_fixer_loop.py
CAO session per failure
  ↓ agent produces RESULT_JSON + optional PATCH
Validation on nuc2 (SSH + wctl run-pytest)
  ↓ success → PR | failure → Issue
GitHub PR/Issue + agent transcript artifacts
```

---

## Quick Start

### Prerequisites

- Self-hosted GitHub Actions runner on `forest.local`
- SSH access to nuc1, nuc2, nuc3 (passwordless keys)
- CAO server running on `http://forest:9889`
- GitHub CLI (`gh`) authenticated on nuc2
- Docker + `wctl` utility on all hosts

### Run Manually (Local Testing)

```bash
# Full nightly workflow (recommended for testing)
make ci-dryrun \
  NUC1=nuc1.local NUC2=nuc2.local NUC3=nuc3.local \
  REPO=/workdir/wepppy WC1=/wc1 LOOPS=3

# Parse existing triage log
python3 services/cao/ci-samurai/parse_pytest_log.py /wc1/ci-samurai/logs/YYYY-MM-DD_HH-MM-SS/triage.txt > failures.jsonl

# Run fixer loop with 3 failures max
python3 services/cao/ci-samurai/run_fixer_loop.py \
  --failures failures.jsonl \
  --repo-root . \
  --nuc2 nuc2.local \
  --repo /workdir/wepppy \
  --cao-base http://forest:9889 \
  --max-failures 3 \
  --poll-seconds 120
```

### Trigger Nightly Workflow

The workflow runs automatically at **3am PST (11:00 UTC)** or can be manually triggered:

```bash
# Via GitHub CLI
gh workflow run ci-samurai-nightly-ssh.yml

# Via GitHub UI: Actions → CI Samurai Nightly → Run workflow
```

---

## Configuration

### Workflow Environment Variables

Set in `.github/workflows/ci-samurai-nightly-ssh.yml`:

```yaml
env:
  NUC1: nuc1.local              # Triage host
  NUC2: nuc2.local              # Validation + PR/issue host
  NUC3: nuc3.local              # Flake loop host
  REPO: /workdir/wepppy         # Remote repo path
  WC1: /wc1                     # Working directory on nuc1
  LOOPS: '3'                    # Flake loop iterations
  SCOPE: ''                     # Test scope (empty = full suite)
  CAO_BASE_URL: http://forest:9889  # CAO server endpoint
```

### Safety Policies

Defined in `services/cao/ci-samurai/run_fixer_loop.py`:

```python
--allowlist "tests/**, wepppy/**/*.py"     # Editable paths
--denylist "wepppy/wepp/**, wepppy/nodb/base.py, docker/**, .github/workflows/**, deps/linux/**"
--max-failures 100                          # Per-run cap
--poll-seconds 120                          # Agent timeout
```

**Critical:** Agents cannot modify:
- WEPP Fortran interchange code (`wepppy/wepp/**`)
- NoDb core base class (`wepppy/nodb/base.py`)
- Docker configs, GitHub workflows, binary deps

### Agent Profiles

Located in `services/cao/src/cli_agent_orchestrator/agent_store/`:

- **`ci_samurai_fixer.md`** - Main worker agent (single-error resolution)
- **`ci_samurai_infra.md`** - Infrastructure validator (SSH/tooling checks)

---

## Usage Examples

### Example 1: Test Failure → Automated PR

**Scenario:** Import error in `tests/nodb/test_climate.py`

```bash
# Nightly workflow detects failure
ERROR tests/nodb/test_climate.py::test_parse_climate_catalog - ImportError: No module named 'foo'

# Agent session spawned
Created terminal: id=abc123 name=ci-fix-1730291234

# Agent analyzes, produces fix
RESULT_JSON:
{
  "action": "pr",
  "confidence": "high",
  "primary_test": "tests/nodb/test_climate.py::test_parse_climate_catalog",
  "handled_tests": ["tests/nodb/test_climate.py::test_parse_climate_catalog"],
  "pr": {
    "branch": "ci/fix/2025-10-30/test_parse_climate_catalog",
    "title": "Fix: Remove unused import in test_climate.py",
    "body": "## Problem\nImportError due to missing module 'foo'\n\n## Root Cause\nLegacy import statement...",
    "url": "https://github.com/rogerlew/wepppy/pull/456"
  }
}

# Validation on nuc2
ssh nuc2.local "cd /workdir/wepppy && wctl run-pytest -q tests/nodb/test_climate.py::test_parse_climate_catalog"
# Exit code: 0 (SUCCESS)

# PR opened with labels: ci-samurai, auto-fix
```

**Result:** PR merged after human review → test fixed

### Example 2: Collection Error → Issue Report

**Scenario:** Database corruption in `wepppy/climates/cligen/tests/`

```bash
# Parser extracts collection error
{
  "kind": "error",
  "test": "wepppy/climates/cligen/tests/geojson_export_test.py::collection_error",
  "error": "sqlite3.DatabaseError: file is not a database"
}

# Agent investigates but cannot fix
RESULT_JSON:
{
  "action": "issue",
  "confidence": "low",
  "primary_test": "wepppy/climates/cligen/tests/geojson_export_test.py::collection_error",
  "issues": [{
    "title": "CI Samurai: CLIGEN database corruption in tests",
    "body": "## Symptoms\nSQLite database file corrupted...\n\n## Hypotheses\n1. Concurrent writes...\n2. Incomplete migration...\n\n## Next Steps\n- Inspect /geodata/cligen/...",
    "url": "https://github.com/rogerlew/wepppy/issues/457"
  }]
}
```

**Result:** Issue triaged by human → database restored manually

### Example 3: Infrastructure Validation

```bash
# Infra agent checks end-to-end path
RESULT_JSON:
{
  "type": "infra_report",
  "remote_host": "nuc2.local",
  "remote_repo": "/workdir/wepppy",
  "checks": [
    { "name": "ssh", "ok": true, "details": "whoami=roger, host=nuc2" },
    { "name": "repo", "ok": true, "details": "branch=master, clean" },
    { "name": "tools", "ok": true, "details": "wctl, gh, python3.10.19" },
    { "name": "pytest", "ok": false, "details": "services/cao/test/test_flow_service.py::collection_error - ModuleNotFoundError" }
  ],
  "action": "issue",
  "confidence": "high",
  "issue": {
    "title": "Infra: Missing cli_agent_orchestrator module on nuc2",
    "body": "## Problem\nCollection error prevents CAO tests from running...",
    "url": "https://github.com/rogerlew/wepppy/issues/458"
  }
}
```

**Result:** Missing Python package installed → infra restored

---

## Developer Notes

### Adding New Safety Rules

Modify `run_fixer_loop.py`:

```python
# Add path to denylist
--denylist "wepppy/wepp/**, wepppy/nodb/base.py, wepppy/critical_module/**"

# Adjust allowlist for new test directories
--allowlist "tests/**, wepppy/**/*.py, new_tests/**"
```

### Creating Custom Agent Profiles

1. Copy existing profile: `cp ci_samurai_fixer.md my_agent.md`
2. Update YAML frontmatter (name, description, model)
3. Define role, inputs, rules, output format
4. Test with manual CAO session:
   ```bash
   curl -X POST http://forest:9889/sessions \
     -d "provider=codex&agent_profile=my_agent&session_name=test-$(date +%s)"
   ```

### Debugging Agent Sessions

```bash
# List recent CAO sessions
curl http://forest:9889/terminals | jq '.terminals[] | select(.session_name | contains("ci-fix"))'

# Get full agent transcript
curl http://forest:9889/terminals/<terminal_id>/output?mode=full > agent_output.log

# Parse for RESULT_JSON
grep -A 50 'RESULT_JSON' agent_output.log
```

### Testing Parser Changes

```bash
# Run parser on historical logs
for log in /wc1/ci-samurai/logs/*/triage.txt; do
  python3 services/cao/ci-samurai/parse_pytest_log.py "$log" | jq -s 'length'
done

# Validate JSONL schema
jq empty < failures.jsonl  # Should exit 0 if valid JSON
```

### Workflow Artifacts

After each nightly run, artifacts are available for 90 days:

- `ci-samurai-logs.tgz` - Raw triage/validate/flake logs
- `ci-samurai-failures` - Parsed `failures.jsonl`
- `ci-samurai-agent-logs` - Full agent transcripts + RESULT_JSON
- `ci-samurai-diagnose` - Summary report

Download via:
```bash
gh run download <run-id> -n ci-samurai-agent-logs
```

---

## Observability

### Metrics Tracked

- **Failure Detection**
  - Total test failures per run
  - Collection errors vs. runtime errors
  - Flaky test identification rate
  
- **Agent Performance**
  - PRs opened (with validation success)
  - Issues created (low confidence or blocked paths)
  - Timeout rate (no RESULT_JSON within 120s)
  - Average session duration

- **Fix Quality**
  - PR merge rate
  - Tests fixed per session (coalescing effectiveness)
  - Validation pass rate

### Logs and Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| **Triage logs** | `/wc1/ci-samurai/logs/<timestamp>/triage.txt` | Full pytest output |
| **Failures JSONL** | GitHub Actions artifact | Parsed test failures |
| **Agent transcripts** | `agent_logs/*.log` | Full Codex session output |
| **RESULT_JSON** | `agent_logs/*.result.json` | Structured agent decisions |
| **Patches** | `agent_logs/*.patch` | Git-unified diffs for PRs |

### GitHub Labels

All PRs/issues are tagged with:
- `ci-samurai` (identifies automation origin)
- `auto-fix` (PR only - indicates automated patch)
- `infra-check` (infrastructure validation PRs)

---

## Troubleshooting

### Common Issues

**1. "No failures.jsonl to process"**

**Cause:** Parser found no FAILED/ERROR lines in triage.txt

**Solution:**
- Check triage.txt exists: `ls -lh /wc1/ci-samurai/logs/*/triage.txt`
- Verify pytest actually ran: `grep "test session starts" <triage.txt>`
- Ensure collection errors are captured (parser updated Oct 2025)

**2. Agent timeout (no RESULT_JSON)**

**Cause:** Agent didn't emit required output within 120s

**Solution:**
- Review agent transcript: `cat agent_logs/*-noresult.log`
- Check for stuck reasoning loops or approval prompts
- Verify `--full-auto` flag in workflow
- Increase `--poll-seconds` if agent needs more time

**3. PR validation fails on nuc2**

**Cause:** Test passes locally but fails in clean environment

**Solution:**
- Check for missing dependencies: `wctl exec weppcloud pip list`
- Verify Docker image is up to date: `wctl build --no-cache`
- Review agent's validation command in transcript

**4. "CAO server not reachable"**

**Cause:** CAO service down or network issue

**Solution:**
```bash
# Check CAO health
curl http://forest:9889/health

# Restart CAO (systemd)
sudo systemctl restart cao-server

# Check logs
sudo journalctl -u cao-server -f
```

**5. SSH key errors to nuc1/nuc2/nuc3**

**Cause:** Runner doesn't have passwordless SSH configured

**Solution:**
```bash
# On runner (forest.local)
ssh-copy-id roger@nuc1.local
ssh-copy-id roger@nuc2.local
ssh-copy-id roger@nuc3.local

# Test
ssh nuc1.local 'echo ok'
```

---

## Limitations and Future Work

### Current Limitations

- **Single-threaded fixer loop** - processes one failure at a time (serial)
- **No cross-run state** - each nightly run is independent
- **Manual label management** - agents must create missing GitHub labels
- **English-only agent prompts** - no i18n support
- **CAO inbox service bug** - system prompt not included (requires manual workaround or fix in `inbox_service.py`)

### Planned Enhancements

#### Phase 1 (Q1 2026)
- [ ] Parallel agent execution (3-5 concurrent sessions)
- [ ] Persistent failure tracking (Redis DB for cross-run state)
- [ ] Auto-merge for high-confidence PRs (CI checks pass + validation success)
- [ ] Slack notifications with PR/issue summaries

#### Phase 2 (Q2 2026)
- [ ] `ci_samurai_merge` agent profile (bundle related fixes)
- [ ] Flaky test quarantine system
- [ ] Agent learning from PR review feedback
- [ ] Extended test scope: `tests/wepp`, `tests/weppcloud`

#### Phase 3 (Q3 2026)
- [ ] Multi-repo support
- [ ] Custom validation pipelines per test type
- [ ] Integration with D-Tale for data-driven failures
- [ ] Agent confidence calibration (ML-based scoring)

---

## Contributing

### For Human Developers

1. Test changes locally with `make ci-dryrun`
2. Update agent profiles in `services/cao/src/cli_agent_orchestrator/agent_store/`
3. Add tests to `tests/` with appropriate markers (`@pytest.mark.integration`)
4. Follow safety policies (respect allowlist/denylist)
5. Document new agent profiles with examples

### For AI Coding Agents

When modifying CI Samurai components:
- **Parser changes**: Add test cases to `tests/` for new failure patterns
- **Agent profiles**: Test with manual CAO session before committing
- **Workflow updates**: Validate with `actionlint` before pushing
- **Safety rules**: Never weaken allowlist/denylist without explicit approval
- **Always emit RESULT_JSON** from agent profiles to prevent timeouts

---

## Further Reading

- **[AGENTS.md](../../AGENTS.md)** - Core directives for AI coding agents
- **[CAO Documentation](../src/cli_agent_orchestrator/README.md)** - CLI Agent Orchestrator architecture
- **[Workflow Configuration](.github/workflows/ci-samurai-nightly-ssh.yml)** - GitHub Actions setup
- **[Agent Profiles](../src/cli_agent_orchestrator/agent_store/)** - Codex behavior definitions
- **[Testing Guide](../../tests/README.md)** - pytest conventions and fixtures

---

## Credits

**Developed by:** Roger Lew, GitHub Copilot, Codex  
**Institution:** University of Idaho  
**License:** BSD-3-Clause  
**Status:** Functional Beta (Oct 2025)  
**Contact:** `roger.lew@<institution>.edu`

---

**Last Updated:** October 30, 2025  
**Version:** 1.0.0-beta
