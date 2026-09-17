# Generated Artifact Validation Standard

## Purpose

This standard governs validation and completion claims for workflows that create,
transform, copy, prepare, execute from, summarize, or publish generated artifacts.
Examples include model inputs, rasters, management and soil files, archives,
exports, reports, compiled assets, and scientific results.

The core rule is:

> Persisted state records intent. Job success records orchestration. The artifact
> consumed by the next stage is the executable truth.

A change is not validated merely because a request succeeded, a controller saved
the expected value, a queue job completed, a broad test suite passed, or a file
exists. Validation must read back the generated artifact at the boundary that can
produce the reported failure and establish its relevant semantics.

This standard complements the
[artifact observability standard](artifact-observability-standard.md).
Observability governs whether project records are visible, retained, and
archivable. This standard governs whether those records prove the claimed
behavior.

## When This Standard Applies

Apply it when any of the following is true:

- production code changes an artifact-producing or artifact-consuming workflow;
- an incident concerns stale, missing, malformed, equivalent, or scientifically
  incorrect generated output;
- a workflow crosses a process, container, host, mount, queue, serializer, cache,
  or deployment boundary;
- the user requests validation on an actual project or named environment; or
- an agent is preparing to call an artifact-related defect fixed or resolved.

For a documentation-only or source-only change that cannot affect generated
artifacts, record that this standard is not applicable. Do not fabricate an
artifact test merely to satisfy a checklist.

## Define Acceptance From the Reported Outcome

Before implementation, restate the user-visible failure and define evidence that
would falsify and confirm the proposed correction. Acceptance must name:

- the operation a user or downstream system performs;
- the persisted state expected after that operation;
- every generated artifact that carries the changed meaning downstream;
- the final consumer of those artifacts;
- the semantic values to parse or compare, not only file paths;
- the environment and representative project/data required; and
- the allowed and prohibited completion claims at each milestone.

Start from the original symptom, not the first exception discovered. Fixing one
exception does not close a broader artifact mismatch unless the full reported
workflow is read back and passes.

## Evidence Chain

Inventory every applicable stage. Mark a stage not applicable only with a reason.

| Stage | Required evidence | Evidence that is insufficient alone |
| --- | --- | --- |
| User/request intent | Exact selection, payload, configuration, or scenario | Agent recollection or an inferred default |
| Persisted state | Reloaded durable state under the normal reader | In-memory mutation before persistence |
| Generated intermediate | Content manifest plus semantic parse | File existence, size, or modification time |
| Prepared/executable input | Readback from the exact path the consumer opens | Upstream source file or controller summary |
| Execution | Exact revision/identity, job tree, terminal state, and fresh output | Parent job success or health check only |
| User-facing result | Report/export rebuilt from the verified fresh output | Cached report or stale download |

The evidence chain need not be implemented as new infrastructure. Reuse existing
project browsers, parsers, archive tools, job inspection, and deployment checks.
Retain concise hashes, parsed values, job IDs, revisions, timestamps, and paths in
the package evidence.

## Content and Semantic Readback

Artifact validation requires both identity and meaning where practical:

1. Build a stable content manifest using paths relative to the artifact root and
   cryptographic hashes. Absolute source paths must not create false differences.
2. Parse the fields that carry the changed behavior using the same format contract
   as the downstream consumer.
3. Compare the generated intermediate with the prepared/executable copy or
   transformation that the next stage actually opens.
4. Confirm outputs are fresh for the verified inputs and execution revision.

Modification times, counts, filenames, and aggregate hashes are useful provenance
signals, but they cannot explain semantics by themselves. A representative sample
is acceptable only when the selection method and coverage risk are stated. Check
all artifacts when the failure can occur independently in any member and the cost
is reasonable.

## Comparative and Scientific Workflows

For baselines, scenarios, counterfactuals, migrations, and before/after studies:

- state which inputs must differ, which may remain equal, and why;
- prove intended differences with semantic parsing before interpreting outputs;
- prove intended equivalence with content and semantic comparison, not assumption;
- do not force model outputs to differ when verified effective inputs can
  legitimately produce equal results; and
- do not accept equal outputs as scientific evidence when the intended input
  difference never reached the executable artifacts.

The objective is faithful propagation of approved intent, not a predetermined
numerical result.

## Direct Boundary and Test-Double Rules

At least one direct, unmocked regression must exercise each changed writer,
serializer, copy/prepare step, or other boundary capable of producing the reported
failure. The test must read back the produced artifact.

Mocks and test doubles may isolate unrelated expensive or external work, but they
must not replace the failing boundary. When a double represents an artifact
producer or consumer, add contract evidence showing its value namespace, shape,
units, defaults, and failure behavior match the real implementation. A test that
repeats the implementation's mistaken assumption is not regression evidence.

Use an actual project in a production-equivalent environment when the failure is
data-dependent, environment-dependent, crosses deployed identities or mounts, was
previously missed by fixture validation, or the user explicitly requests it. Use
the supported clone or archive/restore workflow and record provenance; do not use
ad hoc file copying that bypasses normal initialization.

Production-equivalent evidence must record the exact source revision and relevant
container/process identity. Evidence from a different revision cannot release the
candidate.

## Failure, Retry, and Freshness

Exercise failure at the real writer or consumer boundary when the change affects
partial-state behavior. A failed operation must not publish completion or make
stale output appear current. Retain useful partial artifacts and diagnostics under
the normal project authorization and archive path.

Verify the supported retry or rebuild path from durable intent. Do not repair the
test by editing derived files or controller state directly unless direct repair is
the explicitly approved user workflow.

## Completion Vocabulary

Use status language that names the achieved boundary:

| Status | Meaning |
| --- | --- |
| Diagnosed | Failure mechanism identified with retained evidence |
| Implemented | Source change exists; validation may still be pending |
| Locally validated | Focused tests and local generated-artifact readback pass |
| Environment validated | Exact candidate passes required actual-project or production-equivalent checks |
| Deployed | Exact validated revision is running in the named environment |
| Recovered or repaired | Named affected resources were rebuilt and verified |
| Incident resolved | Required deployment and affected-resource recovery are complete, with no open acceptance gap |

Avoid an unqualified claim that a workflow or incident is fixed. If deployment or
recovery is outside scope, say exactly that: for example, "implemented and locally
validated; not deployed; affected runs remain unrepaired." A package may close a
code-delivery scope while the incident remains unresolved, but its handoff and
tracker must state the remaining owner and gate.

## Review and Release Gate

For applicable changes, package authors and correctness reviewers must verify:

- acceptance traces back to the user's reported outcome;
- every applicable evidence-chain stage has direct evidence or an explicit reason
  it is not applicable;
- mocks do not replace the boundary that failed;
- generated content is parsed, not inferred from metadata or job success;
- the exact candidate revision is used in environment validation;
- failure, retry, freshness, and partial-state behavior are explicit;
- comparisons distinguish intended input semantics from expected output values;
- status language does not exceed the evidence; and
- deployment and affected-resource recovery are separately accounted for.

A broad green suite is supporting evidence, not a substitute for a missing direct
artifact check. Missing generated-output evidence blocks the applicable validation
or release claim.

## Recurrence

The first recurrence after a claimed correction invalidates the completeness of
that claim. Open a new incident record, reassess the full evidence chain, and
inspect the actual generated and consumed artifacts before adding another patch.
Do not amend a closed work package to hide the recurrence.

## Blocked Validation and Exceptions

If the required environment, project, consumer, or artifact is unavailable,
record the exact blocker, owner, and remaining test. Report the change as
unverified at that boundary. Time pressure, a passing job, or operator acceptance
of a limited rollout does not convert missing evidence into validation.

An operator may explicitly narrow the delivery scope or accept a known residual
risk. That decision must name the omitted evidence and affected resources, but it
does not authorize the stronger status "incident resolved."

## References

- `docs/standards/artifact-observability-standard.md`
- `docs/standards/hardening-lifecycle-standard.md`
- `docs/standards/contract-first-change-standard.md`
- `docs/prompt_templates/correctness_review_template.md`
- `docs/work-packages/20260917_mofe_scenario_artifact_integrity/` - motivating
  incident provenance; not normative authority
