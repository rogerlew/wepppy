# CI Samurai - Nightly Test Maintenance & Bug Fixing

> **Status:** Proposed  
> **Tier:** Normie (production code access, human review gates)  
> **Trigger:** GitHub Actions nightly workflow (~3am PST)  
> **Runner:** Self-hosted Proxmox VPS

## Overview

CI Samurai is an autonomous agent swarm that analyzes test failures, diagnoses root causes, and either fixes them with comprehensive reports or escalates unclear cases with detailed investigation notes. The system leverages GPT-5-Codex reasoning via CAO to act as a "lead developer overnight shift," handling both test maintenance and production bug fixes.

**Key principle:** Agents fix what they understand confidently and escalate what they don't, rather than artificially restricting scope to test-only changes. Quality comes from transparency (detailed reports) rather than permission boundaries.

## System Roles

- **Supervisor agent** orchestrates the nightly run: enforces hygiene, distributes failures, reviews worker output, and handles GitHub interactions (PR/issue creation, summary notifications).
- **Worker agents** focus on individual failures: run diagnostics, implement fixes within the allowlist, draft reports, and return artifacts to the supervisor.
- **Telemetry pipeline** captures run metadata, PR outcomes, and reviewer feedback so confidence thresholds can be tuned over time.
- **Human reviewers** remain the merge gate, ensuring every proposed fix is scrutinized before landing in mainline.

## Workflow

### Agent Execution Cycle

Each nightly run follows a strict hygiene cycle to prevent state contamination:

1. **Clean Workspace Setup**
   - Clone fresh repository to isolated workspace (`/tmp/ci-samurai-YYYYMMDD-HHMMSS/`)
   - Checkout `master` branch and hard reset to `origin/master` to ensure the run begins from a pristine tree
   - Verify Docker dev stack is healthy (`wctl up -d --wait`)

2. **Test Execution**
   - Run full test suites sequentially (avoid parallel flakiness during diagnosis):
     ```bash
     wctl run-pytest tests/ --tb=short --maxfail=20 > pytest-output.txt 2>&1
     wctl run-npm test > npm-output.txt 2>&1
     ```
   - Capture exit codes, stdout, stderr for each suite
   - Automatically rerun failing tests once to separate true regressions from suspected flakes; tag reruns that pass as `flake_candidate` for triage
   - Parse output to extract structured failure data (file, line, error type, stack trace)

3. **Failure Triage**
   - Supervisor agent receives failure list
   - Assigns each failure to worker agent for parallel diagnosis
   - Worker reruns the failing test or suite in isolation to confirm reproduction; non-reproducible failures flow into flake handling instead of fix attempts
   - Workers analyze root cause and assess confidence (High/Medium/Low)

4. **Action Dispatch**
   - **High Confidence** → Worker implements fix, re-validates, formats PR
   - **Low Confidence** → Worker documents investigation, formats issue
   - **Medium Confidence** → Worker attempts fix; if validation fails after 2 retries, escalate to issue

5. **PR/Issue Creation**
   - Supervisor collects worker outputs
   - Creates PRs via `gh pr create` with structured descriptions
   - Creates issues via `gh issue create` with `ci-samurai-needs-guidance` label
   - Posts summary to Slack/email with links

6. **Workspace Cleanup**
   - Delete isolated workspace (`rm -rf /tmp/ci-samurai-YYYYMMDD-HHMMSS/`)
   - Ensures no state carries over to next night's run

### Confidence Assessment Framework

Agents rate diagnostic confidence based on:

**HIGH Confidence Indicators:**
- Error pattern matches known catalog (missing mock, import error, outdated assertion)
- Root cause isolated to single file with clear fix
- Similar fix applied successfully in git history
- Re-validation passes on first attempt

**MEDIUM Confidence Indicators:**
- Root cause identified but fix requires multiple files
- Edge cases exist but agent has mitigation strategy
- API contract change with clear migration path

**LOW Confidence Indicators:**
- Intermittent failures (fails <80% of runs)
- Multiple plausible root causes
- Requires domain knowledge agent lacks (hydrology, WEPP model internals)
- Cross-cutting architectural changes needed
- Involves FORTRAN/Rust binaries or geospatial kernels

## Safety Mechanisms

### 1. Scope Restrictions (Pilot Phase)

During calibration, agents operate under path allowlists to prevent high-risk modifications:

**Allowed paths:**
- `tests/**` (all test files)
- `wepppy/weppcloud/controllers_js/__tests__/**` (frontend tests)
- `wepppy/**/*.py` (Python production code, excluding denylist below)

**Denied paths (require human escalation):**
- `wepppy/wepp/**` (WEPP model file generators - fragile)
- `wepppy/topo/peridot/**` (Rust watershed abstraction - high risk)
- `wepppy/nodb/base.py` (NoDb core - affects all controllers)
- `deps/linux/**` (FORTRAN binaries)
- `docker/**` (infrastructure config)
- `.github/workflows/**` (CI/CD)

Agents attempting to modify denied paths automatically escalate to issue, regardless of confidence. The supervisor validates every diff against the allowlist before a worker can open a PR, preventing local git tricks from bypassing policy.

**Post-calibration:** Allowlist expands as telemetry proves agent safety in each domain.

### 2. Validation Requirements

- **Test-only changes:** Run affected test file(s) → must pass
- **Single-file production changes:** Run full test suite → must pass
- **Multi-file changes:** Run full test suite → must pass, plus manual spot-check of related integration tests
- **Max 3 validation attempts:** If third attempt fails, escalate to issue

### 3. Report Quality Enforcement

All PRs must include:
- **Problem:** What broke and how it manifested (with error messages)
- **Root Cause:** Why it broke (with code snippets showing "before" state)
- **Solution:** How the fix works (with code snippets showing "after" state)
- **Testing:** Validation commands run and results
- **Edge Cases:** What corner cases were considered and how they're handled
- **Confidence:** Agent's self-assessed confidence with justification

Supervisor rejects PR submissions missing any section and forces agent to retry.

### 4. Regression Detection

Each nightly run checks for regressions introduced by previous agent PRs:
- Track which tests passed in previous run
- Flag new failures in tests that previously passed
- Cross-reference with merged agent PRs from past 7 days
- If correlation found, create high-priority issue: `ci-samurai-regression`

### 5. Human Review Gates

- **No auto-merge:** All PRs require human approval before merging
- **Review checklist:** Reviewer confirms each required section is present and accurate
- **Feedback loop:** Reviewer marks PR outcome (merge-as-is / merge-with-edits / reject) for confidence calibration

### 6. Flake Handling

- Single automatic rerun attempts to confirm flake suspicion before work begins; failures that pass on rerun are tagged and excluded from fix queues.
- Supervisor tracks recurring flakes with counters; once a threshold triggers (default: 3 occurrences in 7 days) the system files an issue tagged `ci-samurai-flake` for human prioritization.
- Flake-tagged tests remain visible in nightly summaries so humans can spot growing instability trends.

## Confidence Calibration System

### Telemetry Collection

Agent PRs are tagged with metadata for learning:
```yaml
# .github/pr-metadata/ci-samurai-PR123.yml
pr_number: 123
agent_confidence: high
failure_type: missing_mock
files_changed: 3
tests_affected: 9
created_at: 2025-10-29T03:15:00Z
```

PR review outcomes are captured via GitHub webhook:
- `merged_without_modification` → confidence was accurate
- `merged_with_human_edits` → confidence slightly overestimated
- `closed_without_merge` → confidence significantly overestimated

### Learning Loop

Monthly calibration analysis:
1. Query merged PRs with `ci-samurai` label
2. Compute accuracy metrics per confidence level:
   - HIGH confidence → merge-without-mod rate (target: ≥90%)
   - MEDIUM confidence → merge-with-edits rate (target: ≥70%)
   - LOW confidence → N/A (issues, not PRs)
3. Identify failure patterns with high false-confidence rate
4. Update agent prompt with refined guidance for those patterns
5. Expand allowlist for domains where confidence is consistently accurate

**Feedback hook implementation:** GitHub Actions workflow `.github/workflows/ci-samurai-telemetry.yml` triggered on PR events (closed, merged), writes telemetry to `telemetry/ci-samurai/pr-outcomes/YYYY-MM-DD.jsonl`.

## Output Templates

### PR Description (Test Infrastructure)

```markdown
## Test Infrastructure Fixes

### Summary
Fixed 9 test failures caused by missing `url_for_run` mocks after controller refactoring.

### Changes
- wepppy/weppcloud/controllers_js/__tests__/observed.test.js:55 – normalized url_for_run expectations
- wepppy/weppcloud/controllers_js/__tests__/rap_ts.test.js:41 – restored missing url_for_run mock
- wepppy/weppcloud/controllers_js/__tests__/climate.test.js:215 – updated status-stream expectation

### Root Cause
Recent controller changes centralized URL construction via `url_for_run()` helper, but test
mocks weren't updated. Tests failed at import time (ReferenceError) or during assertions.

### Testing
```bash
wctl run-npm test  # All 153 tests pass
```

### Edge Cases
- Verified mock works for both run-scoped and batch-scoped URLs
- Tested with runId containing special characters (dashes, underscores)

**Agent Confidence:** High (test-only changes, clear failure patterns)
```

### PR Description (Production Bug)

```markdown
## Fix: Climate Route Returns 500 on Missing PRISM Data

### Problem
Test suite: `tests/weppcloud/routes/test_climate.py::test_prism_endpoint`
Failure: Expected 200, got 500

Production impact: Users see error page when PRISM data unavailable for their watershed.

### Root Cause
`wepppy/weppcloud/routes/climate.py:142` throws unhandled `KeyError` when `prism_db` 
returns None for watersheds outside PRISM coverage area.

```python
# Before (line 142)
data = prism_db[watershed_id]['monthly']  # KeyError if watershed_id not in dict
```

### Solution
Added null check with descriptive error message:

```python
# After
if watershed_id not in prism_db:
    return jsonify({
        'error': 'PRISM data unavailable for this watershed',
        'suggestion': 'Try GridMET or Daymet climate sources'
    }), 404
data = prism_db[watershed_id]['monthly']
```

### Testing
1. Added regression test: `test_prism_unavailable_watershed()`
2. Verified existing tests still pass: `wctl run-pytest tests/weppcloud/routes/test_climate.py`
3. Manual verification: Loaded run with non-PRISM watershed, confirmed 404 with helpful message

### Edge Cases
- Empty `prism_db` (handled by `in` check)
- Partial data (only some watersheds covered): Each lookup checked independently
- Concurrent requests during db reload: Existing Redis lock prevents stale reads

**Agent Confidence:** High (straightforward null check, well-understood API contract)
```

### Issue Description (Unclear Diagnosis)

```markdown
## CI Samurai Investigation: Intermittent Failure in Watershed Delineation Tests

### Symptoms
Test: `tests/nodb/test_watershed.py::test_topaz_delineation`
Failure rate: 3/10 runs (intermittent)
Error: `AssertionError: Expected 47 subcatchments, got 45`

### Hypotheses Explored

**Hypothesis 1: Race condition in TOPAZ subprocess**
- Tested: Added explicit process.wait() before reading output files
- Result: Still fails intermittently (2/10 runs)
- Conclusion: Not sufficient, but might be contributing factor

**Hypothesis 2: NFS caching/stale reads**
- Tested: Added fsync() after TOPAZ writes, sleep(0.5) before read
- Result: No change in failure rate
- Conclusion: Unlikely to be filesystem issue

**Hypothesis 3: TOPAZ binary non-determinism**
- Tested: Ran TOPAZ 50x with identical inputs, compared outputs
- Result: Output always identical (47 subcatchments)
- Conclusion: TOPAZ itself is deterministic

### Why I'm Stuck
The intermittent nature suggests environmental factors (timing, resource contention?), but
I can't identify the trigger. TOPAZ binary is deterministic when run manually. Test isolation
doesn't help. No obvious race conditions in the test code itself.

### Suggested Next Steps
1. Add verbose logging around TOPAZ invocation (input file checksums, timing)
2. Check for memory pressure correlation (does it fail when other tests run in parallel?)
3. Bisect git history—when did this start failing?
4. Run under strace to see syscall patterns during failures

### Reproduction
```bash
# Fails ~30% of time
for i in {1..10}; do wctl run-pytest tests/nodb/test_watershed.py::test_topaz_delineation; done
```

### Relevant Code
- `wepppy/nodb/core/watershed.py:245` (TOPAZ invocation)
- `tests/nodb/test_watershed.py:89` (test setup)

**Agent Confidence:** Low (intermittent failure, can't reliably reproduce root cause)
```

## Deployment

### GitHub Actions Workflow

`.github/workflows/ci-samurai-nightly.yml`:

```yaml
name: CI Samurai Nightly

on:
  schedule:
    - cron: '0 11 * * *'  # 3am PST (11am UTC)
  workflow_dispatch:  # Allow manual trigger

jobs:
  ci-samurai:
    runs-on: self-hosted  # Proxmox VPS runner
    timeout-minutes: 180  # 3 hour max
    
    steps:
      - name: Create isolated workspace
        run: |
          export WORKSPACE=/tmp/ci-samurai-$(date +%Y%m%d-%H%M%S)
          mkdir -p $WORKSPACE
          echo "WORKSPACE=$WORKSPACE" >> $GITHUB_ENV
      
      - name: Clone repository
        run: |
          cd $WORKSPACE
          git clone https://github.com/rogerlew/wepppy.git .
          git checkout master
          git reset --hard origin/master
      
      - name: Verify Docker stack
        run: |
          cd $WORKSPACE
          wctl up -d --wait
          wctl run-pytest --version
          wctl run-npm --version
      
      - name: Run CI Samurai orchestrator
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CAO_ADMIN_TOKEN: ${{ secrets.CAO_ADMIN_TOKEN }}
          CI_SAMURAI_TELEMETRY_TOKEN: ${{ secrets.CI_SAMURAI_TELEMETRY_TOKEN }}
        run: |
          cd $WORKSPACE/services/cao/ci-samurai
          python orchestrator.py \
            --workspace $WORKSPACE \
            --output-dir $WORKSPACE/ci-samurai-output \
            --max-workers 5 \
            --confidence-threshold high
      
      - name: Upload telemetry
        if: always()
        run: |
          cd $WORKSPACE
          TELEMETRY_BRANCH=ci-samurai-telemetry
          mkdir -p telemetry/ci-samurai/runs/$(date +%Y-%m-%d)
          cp ci-samurai-output/* telemetry/ci-samurai/runs/$(date +%Y-%m-%d)/
          git init
          git config user.name "ci-samurai-bot"
          git config user.email "ci-samurai@wepppy.dev"
          git checkout -b $TELEMETRY_BRANCH
          git add telemetry/
          git commit -m "CI Samurai telemetry: $(date +%Y-%m-%d)"
          git remote add origin https://x-access-token:${CI_SAMURAI_TELEMETRY_TOKEN}@github.com/rogerlew/wepppy.git
          git push --force origin $TELEMETRY_BRANCH
      
      - name: Cleanup workspace
        if: always()
        run: |
          rm -rf $WORKSPACE
      
      - name: Notify team
        if: always()
        run: |
          # Post summary to Slack/email
          curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
            -H 'Content-Type: application/json' \
            -d @$WORKSPACE/ci-samurai-output/summary.json
```

> **Telemetry note:** The workflow pushes run artifacts to a dedicated `ci-samurai-telemetry` branch using a fine-scoped personal access token stored as `CI_SAMURAI_TELEMETRY_TOKEN`. This avoids protected-branch conflicts and keeps audit history separate from application code.

### Self-Hosted Runner Setup

**Advantages:**
- No GitHub Actions minute consumption (unlimited runtime)
- Access to full wepppy dev environment (Docker, wctl, Redis)
- Dedicated compute resources (no contention with other repos)
- No timeout constraints (can iterate on complex bugs)
- Direct access to local geodata/test fixtures (no download overhead)

**Setup on Proxmox VPS:**
```bash
# Install GitHub Actions runner
cd /opt
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure runner
./config.sh --url https://github.com/rogerlew/wepppy \
  --token <REGISTRATION_TOKEN> \
  --name proxmox-ci-samurai \
  --labels self-hosted,Linux,X64,ci-samurai

# Install as systemd service
sudo ./svc.sh install
sudo ./svc.sh start
```

## Metrics & Success Criteria

### Quality Metrics
- **Bug resolution rate:** % of test failures resolved without human intervention (target: ≥60%)
- **Fix quality:** % of PRs merged without modification (target: ≥90% for HIGH confidence)
- **False fix rate:** % of PRs that introduce regressions (target: <5%)
- **Escalation quality:** % of issues marked `needs-guidance` that lead to productive investigation (target: ≥80%)

### Efficiency Metrics
- **Time saved:** Morning triage + bug fixing hours reclaimed per week (target: ≥10 hours)
- **Confidence calibration accuracy:** Agent self-assessment matches review outcomes (target: ≥85% agreement)
- **Test health improvement:** Passing test percentage trend over time (target: steady improvement)

### Safety Metrics
- **Scope violations:** Attempts to modify denied paths (target: 0 per week after pilot)
- **Regression introduction:** New failures caused by agent PRs (target: <2 per month)
- **Review burden:** Time spent reviewing agent PRs vs. manual fixes (target: <50% of manual)

## Rollout Plan

### Phase 1: Pilot (Weeks 1-2)
- Run on controlled test subset: `tests/weppcloud/controllers_js/__tests__/` only
- Allowlist: Test files only, no production code
- Manual review of all outputs (PRs and issues)
- Measure: Fix quality, false positive rate, template adherence

### Phase 2: Calibration (Weeks 3-6)
- Expand to full frontend test suite + Python unit tests
- Allowlist: Test files + Python production (excluding denylist)
- Review first 20 PRs in detail, tune confidence thresholds
- Measure: Merge-without-mod rate per confidence level

### Phase 3: Production (Week 7+)
- Full test suite (pytest + npm)
- Production code edits allowed (with denylist)
- Automated regression detection active
- Monthly calibration reviews

### Phase 4: Expansion (Month 3+)
- Gradually expand allowlist based on telemetry
- Add integration test suite
- Explore smoke test failures
- Consider daytime runs for critical bugs

## Known Limitations

1. **Domain expertise gaps:** Agent lacks deep knowledge of:
   - WEPP model hydrology/erosion physics
   - Geospatial coordinate system transformations
   - FORTRAN/Rust interop edge cases
   → These will consistently escalate to issues

2. **Intermittent failures:** Agent struggles with <80% reproducible failures
   → Requires human investigation of environmental factors

3. **Architectural changes:** Cross-cutting refactors (NoDb base class, Flask app factory)
   → Too risky for autonomous fixing, will escalate

4. **Test coverage blind spots:** Can't fix logic bugs in untested code paths
   → Highlights need for better test coverage as secondary benefit

## Future Enhancements

- **Swarm coordination:** Multiple workers collaborate on related failures (e.g., all tests broken by single API change)
- **Git bisect integration:** Automatically identify regression-introducing commit for new failures
- **Performance regression detection:** Flag tests with >20% slowdown
- **Test coverage analysis:** Suggest new tests for uncovered code paths
- **Dependency update automation:** Detect outdated packages causing test failures

## Immediate Next Steps

1. Run GPT-5 comparison research on existing public CI-maintenance agents to benchmark playbooks, confidence heuristics, and telemetry strategies worth adopting.
2. Stand up a minimal supervisor prototype that enforces the hygiene loop and allowlist while delegating to mocked worker agents.
3. Validate GitHub permissions and PAT scope for the telemetry branch before the first pilot run.

## Benchmark-Informed Roadmap

### MVP Integrations

- **Compatibility telemetry:** Capture per-pattern success metrics (change type, files touched, confidence) so the supervisor can emulate Dependabot-style compatibility scores during the calibration phase.
- **Repairnator loop:** Treat reproduction → fix → full revalidation as a hard gate before a worker can submit a PR, ensuring every patch is backed by a clean rerun.
- **Dr.CI summary comment:** Have the supervisor post a concise comment on each PR summarizing failures addressed, validation commands, and links to logs to match the clarity bar set by PyTorch’s Dr.CI.
- **Flake quarantine:** Apply the single rerun + tagging workflow above and auto-file `ci-samurai-flake` issues once the recurrence threshold hits, so humans have a triage backlog.

### Nice-to-Have Enhancements

- **Speculative merge validation:** Borrow from Mergify/Bors by validating fixes on a merge-commit against latest `origin/master` for extra safety before PR creation.
- **Failure fingerprint clustering:** Use Sheriff-o-Matic-style stack-trace signatures to group related breakages and prioritize systemic issues.
- **Stability windows for risky domains:** Inspired by Renovate, require N consecutive green validations before allowing the agent to touch newly unlocked directories (e.g., WEPP integrations).
- **Automated owner suggestions:** Enrich PR comments with likely reviewers/owners based on failure history, mirroring Prow’s triage helpers.
## References

- Agent prompt: [`agent-prompt.md`](ci-samurai/agent-prompt.md)
- Benchmark research: [`benchmark-research.md`](ci-samurai/benchmark-research.md)
- CAO architecture: [`README.md`](README.md)
- wepppy coding conventions: [`../../AGENTS.md`](../../AGENTS.md)
- Test suite guidelines: [`../../tests/AGENTS.md`](../../tests/AGENTS.md)
