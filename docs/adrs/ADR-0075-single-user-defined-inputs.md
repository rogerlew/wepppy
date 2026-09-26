# ADR-0075: Builder opt-in single management and soil sources

## Status

Accepted product direction, 2026-09-25; independent contract reviews approved; conformance pending.

## Decision and rationale

An unchecked-by-default Builder option enables independent Single User-Defined
landuse/soil modes and excludes Disturbed, SBS, their dependent workflows and
buffer OFEs for the whole project. See the normative
[single-input contract](../schemas/single-user-defined-inputs-contract.md).
This is the explicit opt-in exception to [ADR-0064](ADR-0064-builder-disturbed-default.md).
Unchecked and existing projects retain ADR-0064 and legacy behavior.

The uploaded one-OFE management/soil is replicated across all hillslopes and OFEs;
compatible modifiers still affect generated copies. Supported initial source
versions are management98.4 and soil7778 for Builder default `wepp_260803`, subject to strict structural and
semantic validation. No empirical parameter values, formulas or lookup tables
change. The scientific difference is deliberate absence of disturbance transforms
and buffer geometry in newly opted-in projects, even with ordinary dataset modes.

## Provenance

Venue: repository development conversation, 2026-09-25, America/Los_Angeles.
Participants: project operator and Codex. Decision owner: project operator.
Implementer: Codex. The operator requested independent uploads, all-hillslope/all-OFE
replication, compatible modifiers, Builder checkbox and dependent-feature removal;
then explicitly instructed “disable the buffer ofe when this feature is enabled”
and “commit everything in the worktree and then execute the work package”.
Engineering bounds and lifecycle are documented in the reviewed contract.

## Alternatives and compatibility

Per-domain disturbance switches and class inheritance selectors introduce
conflicting soil/landuse contracts; the Builder creation policy avoids those.
Restricting to legacy 0.cfg would omit the requested Builder workflow. Buffer
management override contradicts a uniform uploaded source; the operator chose
removal of buffer geometry. Existing projects are neither converted nor repaired.
Sources survive rebuilds; explicit compatible modifiers preserve prior precedence.

## Evidence, risks and rollback

[Execution package](../work-packages/20260925_single_user_defined_landuse_soils/package.md)
records dependency tracing, independent reviews and future generated-input evidence.
Conformance remains pending. Risk includes parser permissiveness, feature bypasses,
and non-disturbed multi-OFE assembly; direct boundary/generated-input tests are
required. Revert new creation exposure if acceptance fails; preserve archives and
use compatible code to process already opted-in projects rather than converting
saved modes or enabling Disturbed silently. No deployment is authorized here.

Security review of pinned source `f24c957e3633898e0fd4cbbea5ae08c781f29dba`
showed that the native reader ignores modern2016.3 fields which Python preserves.
Therefore initial support deliberately rejects2016.3 rather than silently losing
scientific intent. Native event and OFE limits, rather than Python parse success,
bound admitted and generated input.

## SUDI-02 soil-format amendment

The operator subsequently requested 2006, 2006.2, and 9002 soil support and
approved implementation ("make it so"). These supplement 7778. Preserve explicit
conductivity and hydraulic values through generated single/multiple-OFE files;
use native version-specific calculations without converting older inputs or
recomputing 9002 values with Rosetta. The native reader requires nine-field
headers for both 2006 versions. Uploaded 9002 adjustment settings remain supplied
model inputs; disabling WEPPcloud Disturbed does not erase native file settings.
No shared catalog parameterization, numerical defaults, or formulas change.
The SUDI-02 canonical contract defines the validation bounds and acceptance.
