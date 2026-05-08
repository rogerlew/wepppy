# [Package Title]

**Status**: Open (YYYY-MM-DD) | Closed (YYYY-MM-DD)
**Timezone**: UTC

## Overview
[2-3 sentences describing what this work package aims to accomplish and why it's needed. Focus on the problem being solved, not implementation details.]

## Objectives
[Bulleted list of specific, measurable goals. What will be different when this package is complete?]
- First objective
- Second objective
- Third objective

## Scope
[What's included in this work package. Be specific about deliverables, affected systems, and boundaries.]

### Included
- Specific feature or area A
- Specific feature or area B
- Documentation updates related to the work

### Explicitly Out of Scope
- Related work that's deferred to a later package
- Tempting extensions that would expand scope
- Other systems that won't be modified

## Implementation Fidelity and Evidence (Required for modernization/migrations)
[Use this section when work modernizes legacy behavior or migrates execution paths.]

- **Fidelity target**: `faithful extraction | scaffold/surrogate`
- **Authoritative source path(s)**: [Exact legacy modules/routines being preserved or replaced]
- **Cutover proof required**: [How you will prove production path is wired, not only implemented]
- **Acceptance evidence type**: `generated-output | fixture-only | both` (default `generated-output` for implementation closeout)

## Stakeholders
[Who cares about this work? Who needs to review or approve?]
- **Primary**: [Team or role that will use/maintain this]
- **Reviewers**: [Who needs to approve the work]
- **Security Reviewer**: [Required when security impact triage says dedicated review is needed]
- **Informed**: [Who should be kept in the loop]

## Success Criteria
[How will we know this package is complete? Make these testable and unambiguous.]
- [ ] Criterion 1 (e.g., "All 15 controllers migrated and passing tests")
- [ ] Criterion 2 (e.g., "Documentation updated and reviewed")
- [ ] Criterion 3 (e.g., "Performance benchmarks meet target (<100ms p95)")
- [ ] Criterion 4 (e.g., "Zero regressions in test suite")

## Dependencies
[What must be complete before this work can start? What will be blocked until this completes?]

### Prerequisites
- [Existing package or feature that must be in place]
- [Required infrastructure or tooling]

### Blocks
- [Future work that depends on this package]

## Related Packages
[Link to other work packages that are related but independent]
- **Depends on**: [Earlier package this builds upon]
- **Related**: [Parallel work in similar areas]
- **Follow-up**: [Planned future packages spawned from this work]

## Timeline Estimate
[Rough estimate for planning purposes - not a commitment]
- **Expected duration**: [e.g., "2-3 weeks", "4-6 sprints"]
- **Complexity**: [Low/Medium/High]
- **Risk level**: [Low/Medium/High]

## Security Impact and Review Gate
[Always complete security impact triage. Require a dedicated security review artifact when the package changes attack surface.]

- **Security impact triage**: `none | low | high`
- **Dedicated security review required**: `yes | no`
- **Triage rationale**: [Why the package is or is not security-sensitive]
- **Security review artifact**: `docs/work-packages/<package>/artifacts/<date>_security_review.md` (required when triage is `high`)

Use `docs/prompt_templates/security_review_template.md` for the security artifact format and by-surface checks.

## Hardening and Callus Softening (Required for incident/remediation packages)
[Complete this section when the package is primarily reliability hardening, defensive mitigation, or mitigation retirement.]

- **Failure signature(s)**: [Exact error text, route/job id patterns, impact scope]
- **Related prior hardening efforts**: [Links to prior packages/mini-packages/standards]
- **Health signals**: [What should improve if remediation is effective]
- **Danger signals**: [What indicates harmful complexity or ineffective hardening]
- **Observation window**: [e.g., 14-30 days]
- **Temporary calluses introduced**: [List + owner + sunset criteria]
- **Callus softening hypothesis (if applicable)**: [What can be reduced/removed, under what test/review gates]

## References
[Links to relevant documentation, designs, or context]
- `path/to/relevant/file.py` - [Brief description]
- `docs/dev-notes/relevant_topic.md` - [Brief description]
- External link - [Brief description]

## Deliverables
[Concrete artifacts that will exist when this is done. Fill this in at closure.]
- Link to key PRs or commits
- New/updated documentation
- Test coverage additions
- Performance improvements quantified

## Follow-up Work
[Issues or opportunities discovered during execution. Fill this in at closure.]
- Spin-off package for [related work]
- Technical debt to address in [area]
- Improvements suggested by [stakeholder]

## Closure Notes
[Add this section when closing the package]

**Closed**: YYYY-MM-DD

**Summary**: [1-2 paragraphs describing what was accomplished, any significant deviations from the plan, and overall outcome]

**Lessons Learned**: [What went well, what could be improved for future packages]

**Archive Status**: [Note what artifacts are retained and where]
