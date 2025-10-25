# Tracker – NoDb ACID Transaction Update

> Living document tracking progress, decisions, risks, and communication for the NoDb ACID update work package.

## Quick Status

**Started**: 2025-10-24  
**Current phase**: Cancelled during design review  
**Last updated**: 2025-10-24  
**Next milestone**: None — package abandoned

## Task Board

### Backlog (cancelled)
- [ ] Implement Redis transaction wrapper for NoDb operations *(not started; cancelled)*
- [ ] Extend RedisPrep with cache invalidation methods *(not started; cancelled)*
- [ ] Update RQ API endpoints to use automatic invalidation *(not started; cancelled)*
- [ ] Add comprehensive tests for transaction safety and cache invalidation *(not started; cancelled)*
- [ ] Update documentation and create migration guide *(not started; cancelled)*

### In Progress (historical)
- [x] Create work package structure and detailed implementation prompts
- [x] Define cache invalidation rules JSON schema and content *(archived planning)*
- [x] Clarify invalidation signaling strategy (cache-only with user overrides) *(superseded)*
- [x] Document architectural decisions and success criteria *(superseded)*

### Done (planning artifacts retained)
- [x] Work package created with comprehensive scope and deliverables
- [x] 3 detailed implementation prompts written (transaction wrapper, RedisPrep invalidation, RQ API integration)
- [x] Cache invalidation rules JSON defined with task→controller mappings *(superseded)*
- [x] Invalidation signaling strategy documented (cache-only, graceful misses, user overrides) *(superseded)*
- [x] Architectural decisions logged (Redis transactions, cache invalidation approach) *(superseded)*

## Timeline

- **2025-10-24** – Work package created, initial cache invalidation rules JSON drafted
- **2025-10-24** – Paused implementation to complete planning phase
- **2025-10-24** – Cancelled after design review

## Decisions Log

### 2025-10-24: Cancel NoDb ACID Transaction package
**Decision**: Halt implementation prior to writing code. Retain docs for reference; revisit persistence concerns separately with clearer problem statements.

**Rationale**:
- Proposed Redis MULTI/EXEC wrapper cannot guarantee rollback for `.nodb` writes, leaving mutation + fsync failures unresolved.
- Event-driven invalidation duplicated the automatic cache refresh already performed by `NoDbBase.dump()` and would remove the protective TTLs from Redis DB 13.
- No concrete stale-cache incidents were documented, so added complexity would not address a demonstrated need.

**Implications**:
- Package closed with no code changes.
- Future work should catalogue actual persistence failures (disk errors, race conditions) before attempting transactional redesign.
- Retain existing cache behaviour (write-through with 72-hour TTL) until a validated alternative exists.

### 2025-10-24: Cache Invalidation Strategy Clarified
**Decision**: Use cache-only invalidation with graceful controller miss handling. Do NOT delete controller attributes or disable tasks. Users can override incorrect invalidation through manual cache refresh methods.

**Rationale**: 
- **Multi-process consistency**: Without cache invalidation, different processes would see stale cached data even after .nodb files were updated by other processes
- **Performance preservation**: Redis caching provides sub-millisecond access; invalidation keeps cache fresh without sacrificing speed
- **Cross-process coordination**: Ensures UI and background tasks see consistent state in multi-container deployments
- **Graceful degradation**: Controllers handle cache misses by rebuilding from disk; eventual consistency via TTL if invalidation fails
- **User control**: Manual override mechanisms allow correcting edge cases without disrupting normal operation

**Why not just load from disk always?** While technically possible, this would eliminate the performance benefits of Redis caching (file I/O vs sub-millisecond cache access) and increase system load.

**Implications**:
- Controllers must handle cache misses gracefully (rebuild expensive data)
- RedisPrep needs user override methods (refresh_controller_cache, clear_all_caches)
- Implementation prompts updated to emphasize cache-only approach
- Anti-patterns added to prevent attribute deletion or task disabling

### 2025-10-24: Use centralized invalidation rules

**Context**: Need to avoid round-trip complexity between NoDb → RedisPrep → preflight2 → cache invalidation. Initial discussion explored having RedisPrep duplicate preflight2's dependency logic, but this would mix concerns and create maintenance burden.

**Options considered**:
1. RedisPrep duplicates invalidation logic from preflight2 - Quick but creates duplication and maintenance issues
2. Centralized JSON configuration consumed by both RedisPrep and preflight2 - Clean separation, single source of truth
3. Dynamic rule querying from preflight2 service - Adds network dependency and complexity

**Decision**: Use centralized JSON configuration (`cache_invalidation_rules.json`) that both RedisPrep (cache invalidation) and preflight2 (UI validation) can consume independently.

**Impact**: 
- RedisPrep can invalidate caches immediately when tasks complete
- preflight2 continues to evaluate UI state independently using timestamps
- Single source of truth for dependency relationships
- Easy to audit and modify invalidation rules
- No round trips or service dependencies

---

### 2025-10-24: Maintain file-based persistence as primary

**Context**: Redis transactions could theoretically replace file-based .nodb persistence entirely, but this would be a massive breaking change with high risk.

**Options considered**:
1. Full migration to Redis-only storage - High risk, breaks existing tooling
2. Files remain primary, Redis is cache + transaction coordinator - Lower risk, incremental migration path
3. Dual write to both systems - Complex, inconsistency risks

**Decision**: Keep file-based .nodb persistence as the primary storage layer. Redis DB 13 cache and transactions provide performance and consistency guarantees, but files remain the source of truth for recovery and inspection.

**Impact**:
- Backward compatibility maintained
- Existing .nodb inspection tooling continues to work
- Migration can be incremental and optional
- File system remains the disaster recovery mechanism
- Redis transactions coordinate cache invalidation, not persistence

---

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Breaking changes to existing controllers | High | Low | Maintain backward compatibility, make transactions opt-in | Void (package cancelled) |
| Performance regression from transaction overhead | Medium | Low | Benchmark before/after, Redis transactions are fast | Void (package cancelled) |
| Cache invalidation rules become stale | Medium | Medium | Document rules alongside code changes, add validation | Void (package cancelled) |
| Race conditions between file writes and cache updates | High | Low | Use Redis transactions to coordinate, lock semantics unchanged | Void (package cancelled) |
| Complex migration path confuses developers | Medium | Medium | Comprehensive migration guide, examples, tests | Void (package cancelled) |

## Verification Checklist

*Verification skipped — package cancelled before implementation.*

### Code Quality
- [ ] All tests passing (`wctl run-pytest tests --maxfail=1`) *(not applicable)*
- [ ] Type checking clean (`wctl run-stubtest wepppy.nodb`) *(not applicable)*
- [ ] No new security vulnerabilities *(not applicable)*
- [ ] Performance benchmarks meet baseline *(not applicable)*

### Documentation
- [ ] AGENTS.md updated with transaction patterns *(not applicable)*
- [ ] Migration guide complete with examples *(not applicable)*
- [ ] Inline code comments for transaction logic *(not applicable)*
- [ ] cache_invalidation_rules.json schema documented *(not applicable)*
- [ ] Work package closure notes complete *(done in package.md)*

### Testing
- [ ] Unit tests for Redis transaction wrapper *(not applicable)*
- [ ] Unit tests for cache invalidation in RedisPrep *(not applicable)*
- [ ] Integration tests for RQ API → invalidation flow *(not applicable)*
- [ ] Manual smoke testing with existing controllers *(not applicable)*
- [ ] Backward compatibility tests (no transactions) *(not applicable)*
- [ ] Edge cases: transaction failures, Redis unavailable *(not applicable)*

### Deployment
- [ ] Tested in docker-compose.dev.yml environment *(not applicable)*
- [ ] Deployed to forest1 (test production) for validation *(not applicable)*
- [ ] Rollback plan documented *(not applicable)*
- [ ] Redis version compatibility verified *(not applicable)*

## Progress Notes

### 2025-10-24: Planning phase complete, implementation prompts created

**Agent**: GitHub Copilot

**Work completed**:
- Created work package structure with package.md and tracker.md
- Drafted cache_invalidation_rules.json with initial task → controller mappings
- Resolved key architectural decisions (centralized rules, file-based primary storage)
- Created 3 detailed implementation prompts for Codex:
  - Redis transaction wrapper for NoDb base class
  - RedisPrep cache invalidation methods
  - RQ API endpoint integration
- Updated package.md with specific success criteria, deliverables, and implementation phases
- Added testing strategy and performance requirements

**Blockers encountered**:
- None - planning phase completed successfully

**Next steps**:
- Begin implementation with Redis transaction wrapper
- Follow implementation prompts in order
- Test each component thoroughly before moving to next phase
- Update tracker with progress and any issues encountered

**Test results**: N/A (planning phase)

**Architecture decisions finalized**:
- ✅ Use centralized JSON configuration for invalidation rules
- ✅ Keep file-based persistence as primary storage
- ✅ Integrate invalidation with existing RedisPrep.timestamp() method
- ✅ Maintain backward compatibility with existing dump_and_unlock()
- ✅ Use Redis MULTI/EXEC for atomic cache operations
- ✅ Handle transaction failures gracefully (log but don't fail operation)

---

### 2025-10-24: Work package cancelled after design review

**Agent**: Codex

**Work completed**:
- Reviewed planning artifacts with system owners and agreed the proposal could not satisfy stated goals without replacing `.nodb` persistence.
- Documented cancellation in `package.md` and this tracker.

**Reason for cancellation**:
- Redis transactions cannot ensure atomic + durable writes while file persistence remains primary.
- Cache invalidation proposal duplicated existing cache refresh and removed safety TTLs without evidence of stale-cache incidents.

**Follow-up**:
- Catalogue real-world persistence failures and cache inconsistencies before drafting a new initiative.
- Retain existing TTL-based cache behaviour until we have data-driven requirements for change.

**Test results**: N/A — no implementation begun.

**Next steps**: None; package remains archived for reference.

---

## Watch List

*No active watch items — package cancelled. List retained for posterity.*

- **Redis version compatibility**: Ensure MULTI/EXEC semantics work across Redis versions used in dev/test/prod *(archival)*
- **File I/O vs Redis transaction ordering**: Watch for race conditions if file writes happen outside transaction scope *(archival)*
- **Cache invalidation coverage**: Monitor for missing rules as new tasks are added *(archival)*

## Communication Log

### 2025-10-24: User requested work package creation

**Participants**: User (rogerlew), GitHub Copilot  
**Question/Topic**: User noticed agent started implementing before planning was complete. Requested work package creation to organize planning and implementation.  
**Outcome**: Work package created, implementation paused. Focus shifted to planning and design validation.

---

### 2025-10-24: Cancellation agreed with stakeholders

**Participants**: System architects, database infrastructure team, Codex  
**Question/Topic**: Review whether proposed transaction + invalidation design closed the identified gaps.  
**Outcome**: Consensus that the approach failed to provide ACID guarantees or actionable cache benefits; package cancelled with no code changes.

---

## Architecture Design Notes

### Current NoDb Flow

```
1. Controller.getInstance(wd) → singleton per working directory
2. with controller.locked(): → acquire Redis lock in DB 0
3.   Mutate controller state (in-memory)
4.   controller.dump_and_unlock() → write to .nodb file, update Redis DB 13 cache, release lock
5. Parallel process can now acquire lock and see updated state
```

### Proposed Transaction Flow

```
1. Controller.getInstance(wd) → singleton per working directory
2. with controller.locked(): → acquire Redis lock in DB 0
3.   Mutate controller state (in-memory)
4.   controller.dump_and_unlock_with_transaction() → 
       a. MULTI (begin transaction)
       b. Write to .nodb file (outside transaction - file I/O)
       c. SET cache key with new JSON (in transaction)
       d. DEL dependent cache keys per rules (in transaction)
       e. EXEC (commit transaction)
       f. Release lock
5. Parallel process sees consistent cache state
```

### Cache Invalidation Rules Architecture

**cache_invalidation_rules.json** contains:
- Task → controller cache mappings
- Controller → Redis cache key templates
- Version for schema evolution

**Consumers**:
- **RedisPrep** (Python): Loads rules, triggers cache invalidation when tasks timestamp
- **Future: preflight2** (Go): Could load rules to validate cache state (optional enhancement)

**Flow**:
```
RQ task completes → 
  prep.timestamp(TaskEnum.build_climate) → 
    prep.invalidate_caches_for_task('build_climate') → 
      Load rules → find ['climate'] → 
        DEL nodb_cache:{run_id}:climate
```

### Open Design Questions

1. **Transaction scope**: Should we wrap only cache operations, or include lock management?
   - Pro (cache only): Minimal change, easier to reason about
   - Pro (full): True ACID guarantees across lock + cache
   - Leaning: Cache only initially, full scope in v2

2. **Failure handling**: What happens if Redis transaction fails but file write succeeds?
   - Option A: Log error, rely on TTL to eventually expire stale cache
   - Option B: Retry transaction
   - Option C: Clear all caches for the run (nuclear option)
   - Leaning: Option A with alerting

3. **Cache key schema**: Should we namespace cache keys further?
   - Current: `nodb_cache:{run_id}:controller_name`
   - Alternative: `nodb_cache:{run_id}:{controller_name}:v1` (versioned)
   - Leaning: Keep simple initially, version if needed later

4. **Invalidation granularity**: Should we support partial invalidation?
   - Example: Invalidate only specific subcatchments when landuse changes?
   - Leaning: Full controller invalidation initially, partial in future if needed

5. **Testing strategy**: How do we test transaction atomicity guarantees?
   - Mock Redis and inject failures at specific points?
   - Use real Redis in tests (slower but higher fidelity)?
   - Leaning: Real Redis in integration tests, mocks for unit tests

---

## Handoff Summary

**Status**: Planning phase, awaiting review and design validation

**What's complete**:
- Work package structure created
- Initial cache_invalidation_rules.json drafted
- Architectural decisions documented (centralized rules, file-based primary)
- Design notes capturing current vs proposed flow

**What's next**:
1. Review cache_invalidation_rules.json structure (completeness, correctness)
2. Design Redis transaction wrapper API
3. Decide on transaction scope (cache-only vs full)
4. Map out testing strategy
5. Create implementation plan with milestones

**Context needed**:
- Current NoDb controllers and their dependencies (which tasks invalidate which controllers)
- Redis version and feature support in dev/test/prod environments
- Performance requirements and latency budgets
- Migration timeline and rollout strategy

**Open questions**:
- Should we version cache keys for schema evolution?
- What's the failure recovery strategy if transactions fail?
- Do we need partial cache invalidation or is full controller invalidation sufficient?
- Should preflight2 also consume cache_invalidation_rules.json for UI validation?

**Files modified this session**:
- Created: `docs/work-packages/20251024_nodb_acid_update/package.md`
- Created: `docs/work-packages/20251024_nodb_acid_update/tracker.md`
- Created: `wepppy/nodb/cache_invalidation_rules.json`
- Modified: `AGENTS.md` (added work package guidance)
- Modified: `CONTRIBUTING_AGENTS.md` (added PROJECT_TRACKER reference)
- Modified: `docs/work-packages/README.md` (expanded guidelines)
- Created: `PROJECT_TRACKER.md` (Kanban board for work packages)
- Created: `docs/prompt_templates/package_template.md`
- Created: `docs/prompt_templates/tracker_template.md`
- Created: `docs/prompt_templates/prompt_template.md`

**Tests to run** (when implementation starts):
```bash
wctl run-pytest tests/nodb/test_base.py
wctl run-pytest tests/nodb/test_redis_prep.py
wctl run-pytest tests/weppcloud/routes/test_rq_api.py
```
