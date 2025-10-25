# [Prompt Title]

> **Purpose**: [One sentence describing what this prompt helps accomplish]  
> **Target**: [AI agent type, e.g., "GitHub Copilot", "Claude 3.5", "any agent"]  
> **Created**: YYYY-MM-DD  
> **Status**: Active | Completed (YYYY-MM-DD)

## Context

[Provide the background needed to understand this prompt. What's the larger initiative? What has been done already? What assumptions can the agent make?]

- Current state: [Where things stand now]
- Goal state: [Where we want to be after following this prompt]
- Related work: [Links to relevant code, docs, or other prompts]

## Prerequisites

Before using this prompt, ensure:
- [ ] [Prerequisite 1, e.g., "Tests are passing in baseline"]
- [ ] [Prerequisite 2, e.g., "Package.md is up to date"]
- [ ] [Prerequisite 3, e.g., "Agent has read specified reference docs"]

## Objective

[Clear, specific statement of what the agent should accomplish. Make this measurable and unambiguous.]

**Success looks like**: [Concrete description of the outcome]

## Reference Documents

Agent must read these before starting work:
- `path/to/file.md` – [Why this is relevant]
- `path/to/code.py` – [What to learn from this]
- [External link] – [What context this provides]

## Working Set

### Files to Read (Inputs)
[Explicit list of files the agent should examine for context]
- `path/to/input1.py` – [What information to extract]
- `path/to/input2.js` – [What patterns to observe]
- `path/to/input3.md` – [What specifications to follow]

### Files to Modify (Outputs)
[Explicit list of files the agent will change]
- `path/to/output1.py` – [What changes to make]
- `path/to/output2.js` – [What transformations to apply]
- `path/to/output3.md` – [What documentation to update]

### Files to Reference (Dependencies)
[Files the agent should be aware of but not necessarily read in full]
- `path/to/dependency1.py` – [How it relates]
- `path/to/dependency2.js` – [What to watch for]

### Files to Avoid (Exclusions)
[Files that might seem relevant but should NOT be modified in this task]
- `path/to/excluded1.py` – [Why not to touch this]
- `path/to/excluded2.js` – [What problem this would cause]

## Step-by-Step Instructions

[Numbered, sequential steps that leave no room for interpretation]

1. **[Step name]**: [Detailed instruction]
   - Substep if needed
   - Another substep
   - Example code or command if applicable

2. **[Next step]**: [Detailed instruction]
   ```python
   # Example code snippet showing correct implementation
   ```

3. **[Validation step]**: Run tests to verify
   ```bash
   wctl run-pytest tests/specific/area.py
   ```

[Continue with all steps...]

## Observable Outputs

[Show what correct implementation looks like with before/after examples]

### Before (Current State)
```python
# Example of code before changes
def old_function():
    return "old way"
```

### After (Target State)
```python
# Example of code after changes
def new_function():
    """Improved docstring."""
    return "new way"
```

## Anti-Patterns to Avoid

[Explicit examples of what NOT to do and why]

❌ **Don't do this**:
```python
# Bad example with explanation of why it's wrong
```

✅ **Do this instead**:
```python
# Good example with explanation of why it's correct
```

## Validation Gates

[Tests and checks that must pass before the work is complete]

### Automated Checks
```bash
# Linting
wctl run-npm lint

# Type checking
wctl run-stubtest module.name

# Unit tests
wctl run-pytest tests/target/area.py

# Integration tests
wctl run-pytest tests/integration/related_area.py
```

### Manual Verification
- [ ] [Manual check 1, e.g., "Verify UI renders correctly in browser"]
- [ ] [Manual check 2, e.g., "Confirm no console errors"]
- [ ] [Manual check 3, e.g., "Test edge case X manually"]

### Success Criteria
All of the following must be true:
- [ ] All tests passing (exit code 0)
- [ ] No new linting errors
- [ ] Documentation updated
- [ ] Changes follow existing code patterns
- [ ] Edge cases handled and tested

## Deliverables

[Concrete, checkable list of what will exist after completing this prompt]

1. [Deliverable 1, e.g., "Modified climate.js controller with new bootstrap pattern"]
2. [Deliverable 2, e.g., "Passing Jest tests for climate controller"]
3. [Deliverable 3, e.g., "Updated AGENTS.md with new workflow"]

## Handoff Format

After completing the work, report results in this structure:

**Completed**: YYYY-MM-DD

**Changes Made**:
- [Summary of change 1]
- [Summary of change 2]
- [Summary of change 3]

**Files Modified**:
- `path/to/file1.py`
- `path/to/file2.js`
- `path/to/file3.md`

**Test Results**:
```
[Paste test output showing all passing]
```

**Validation Status**:
- [x] Automated checks passed
- [x] Manual verification complete
- [x] Success criteria met

**Issues Encountered**:
- [Issue 1 and resolution]
- [Issue 2 and resolution]

**Suggestions for Improvement**:
[Any observations about the prompt, process, or codebase that could be improved]

## Notes

[Additional context, caveats, or tips for the agent]

---

## Outcome (Complete this when retiring the prompt)

**Completed**: YYYY-MM-DD  
**Agent**: [Which agent executed this]

**Result**: [Brief summary of what was accomplished]

**Deviations**: [Any changes from the original plan and why]

**Lessons Learned**: [What went well, what could be improved for future similar prompts]

**References**: [Links to commits, PRs, or issues related to this work]
