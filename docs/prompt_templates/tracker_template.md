# Tracker – [Package Title]

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Started**: YYYY-MM-DD  
**Current phase**: [Discovery/Implementation/Testing/Documentation/Closing]  
**Last updated**: YYYY-MM-DD  
**Next milestone**: [Brief description of next major checkpoint]

## Task Board

### Ready / Backlog
- [ ] Task that's scoped but not started
- [ ] Another task ready to be picked up
- [ ] Third task waiting in the wings

### In Progress
- [ ] Task currently being worked on (should be limited to 1-2 active items)
- [ ] Another active task with clear owner/agent

### Blocked
- [ ] Task blocked by external dependency - [explain blocker]
- [ ] Task waiting on decision - [explain what's needed]

### Done
- [x] Completed task 1 (YYYY-MM-DD)
- [x] Completed task 2 (YYYY-MM-DD)
- [x] Completed task 3 (YYYY-MM-DD)

## Timeline

Key events and milestones for quick reference:

- **YYYY-MM-DD** – Package created, initial scoping completed
- **YYYY-MM-DD** – First major milestone achieved (e.g., "core implementation done")
- **YYYY-MM-DD** – Testing phase started
- **YYYY-MM-DD** – Package closed

## Decisions Log

Record significant decisions with context so future agents understand the rationale.

### YYYY-MM-DD: [Decision title]
**Context**: [What situation prompted this decision]

**Options considered**:
1. Option A - [pros/cons]
2. Option B - [pros/cons]
3. Option C - [pros/cons]

**Decision**: [What was chosen and why]

**Impact**: [What this means for the work package]

---

### YYYY-MM-DD: [Another decision]
[Same structure as above]

## Risks and Issues

Track potential problems and their mitigation strategies.

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| [Risk description] | High/Med/Low | High/Med/Low | [How we'll handle it] | Open/Mitigated/Closed |
| Example: Breaking changes to API | Medium | Low | Comprehensive test coverage + gradual rollout | Open |

## Verification Checklist

Pre-closure validation steps. Check these off as the package nears completion.

### Code Quality
- [ ] All tests passing (`wctl run-pytest tests --maxfail=1`)
- [ ] Frontend tests passing (`wctl run-npm test`)
- [ ] Linting clean (`wctl run-npm lint`)
- [ ] Type checking clean (`wctl run-stubtest <module>`)
- [ ] No new security vulnerabilities

### Documentation
- [ ] README.md updated for affected modules
- [ ] AGENTS.md updated if workflow changed
- [ ] Inline code comments for complex logic
- [ ] API documentation generated/updated
- [ ] Work package closure notes complete

### Testing
- [ ] Unit test coverage for new code
- [ ] Integration tests for cross-module changes
- [ ] Manual smoke testing performed
- [ ] Edge cases documented and tested
- [ ] Backward compatibility verified

### Deployment
- [ ] Tested in docker-compose.dev.yml environment
- [ ] Deployed to forest1 (test production) if applicable
- [ ] User acceptance testing complete if applicable
- [ ] Rollback plan documented if high-risk

## Progress Notes

Chronological log of work sessions for agent handoffs and historical context.

### YYYY-MM-DD: [Session title or focus area]
**Agent/Contributor**: [GitHub Copilot / Claude / Human name]

**Work completed**:
- Specific accomplishment 1
- Specific accomplishment 2
- Files modified: `path/to/file.py`, `path/to/another.js`

**Blockers encountered**:
- Issue 1 and how it was resolved (or current status)
- Issue 2 and how it was resolved (or current status)

**Next steps**:
- What the next agent should focus on
- Open questions that need answers
- Suggested approach for unfinished work

**Test results**: [Pass/Fail summary with key metrics]

---

### YYYY-MM-DD: [Another session]
[Same structure as above]

## Watch List

Items requiring ongoing attention but not blocking progress.

- **[Item to watch]**: [Why it matters and what we're monitoring]
- **[Another concern]**: [Context and monitoring approach]
- Example: "Performance of X endpoint - tracking p95 latency, target <200ms"

## Communication Log

Record key discussions, questions to humans, and external coordination.

### YYYY-MM-DD: [Topic]
**Participants**: [Who was involved]  
**Question/Topic**: [What was discussed]  
**Outcome**: [Decision, answer, or action items]

---

## Handoff Summary Template

[Use this section when explicitly handing off to another agent]

**From**: [Current agent]  
**To**: [Next agent or "any available agent"]  
**Date**: YYYY-MM-DD

**What's complete**:
- [Specific deliverable 1]
- [Specific deliverable 2]

**What's next**:
1. [First priority task]
2. [Second priority task]
3. [Third priority task]

**Context needed**:
- [Key background the next agent should know]
- [Links to important discussions or decisions]

**Open questions**:
- [Question 1 that needs human input]
- [Question 2 for the next agent to investigate]

**Files modified this session**:
- `path/to/file1.py`
- `path/to/file2.js`
- `path/to/file3.md`

**Tests to run**:
```bash
wctl run-pytest tests/specific/test_suite.py
wctl run-npm test
```
