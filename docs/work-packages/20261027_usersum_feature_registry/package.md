# Public Usersum feature registry

**Status**: Open, contract checkpoint prepared (2026-10-27)
**Timezone**: UTC

## Overview

Publish the complete registered feature and interface catalog in Usersum,
including each entry's maturity classification. The operator explicitly
requested public access because registry information is open source.

## Scope and Objectives

Add one server-rendered Jinja route at `/usersum/features/`, using the existing
Usersum shell and validated feature/config loaders. Add a discovery link on the
Usersum index, outside curated document sections, and update the user guide and
authoring documentation. Include Internal and embargoed metadata. Preserve all
execution, resource, launch, and document permissions.

## Complexity Budget

Reuse Flask, Jinja, Usersum shell, and registry runtime. Permit one route, one
template, index link, focused tests, and documentation. No new dependencies,
services, queues, stores, account lookups, or generated catalog copies. First
acceptance is anonymous HTTP rendering with all real registry ids and accurate
maturity/access descriptions. Retain evidence before proposing any expansion.

## Security Impact and Review Gate

Impact: low; additive anonymous read-only metadata route. Dedicated security
review required because a public route is added. Registry data is explicitly
public; account membership and protected resource access are out of scope.
Contract reviews must verify escaping, fixed data sources, and noninterference.

## Success Criteria

Anonymous and authenticated readers see the same complete catalog regardless
of role filters. Roads displays Experimental and PowerUser; group-only rows
must not imply a role alone grants access. Config rows reflect runtime maturity
overrides. The index link works behind `/weppcloud`. Real loader/template HTTP
readback and focused tests pass; broad and frontend gates are recorded with
any limitations. Independent correctness/security reviews close findings.

## Evidence and Parameterization

No model artifacts, parameterization, data schemas, or project state change;
no parameterization ADR is required. Generated output evidence is the rendered
HTML, checked against actual validated registry entries. Deployment is separate.

## Dependencies and Deliverables

The existing Usersum and feature registry specifications are amended first.
Follow [the active plan](prompts/active/implementation_execplan.md) and
[tracker](tracker.md). The standalone contract ancestor requires explicit commit
authority, which has not yet been granted in this conversation.
