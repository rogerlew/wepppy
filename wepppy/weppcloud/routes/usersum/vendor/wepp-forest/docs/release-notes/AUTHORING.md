# Authoring Guide

## Audience and Purpose

Write a technical explanation that remains useful without access to the
restricted codebase. Begin in language a hydrologist or soil scientist can
read, then provide the equations, numerical details and implementation account
an engineer needs. Define terminology rather than assuming all readers share
one discipline. Detail belongs in the report or appendices, not solely behind
an inaccessible repository link.

Explain the current release coherently. Do not make readers reconstruct it
from a chronological debugging diary. Preserve investigative history elsewhere
and cite the evidence that supports each conclusion.

## Coverage and Traceability

1. State the released source identity, binary identities and document revision.
   Distinguish the source-change baseline, hydrological comparison baseline
   and previous published report; they need not be the same version.
2. Audit the shipped commit range and relevant dependency/parameter changes.
   Include carryover changes from unreleased, withdrawn or undocumented builds
   when they first reach the report's audience.
3. Assign stable change IDs in `change-register.csv`. Map each change to a
   report section, evidence and disposition. Include scientific, numerical,
   implementation, interface, parameter, stability, performance and workflow
   changes. Group minor changes only with a stated scope and rationale.
4. Mark abandoned experiments, superseded implementations and unchanged
   behavior explicitly. Never describe an experimental branch as shipped.
5. Reconcile the register with the final source range at publication. No blank
   disposition is acceptable. The internal register may include restricted
   provenance; the reader-facing change map must still explain every change.

Completeness means coverage of changes, not publication of the source tree.
An omitted raw listing is not an omitted technical explanation.

## What May Be Described or Shown

### Detailed Legacy Descriptions

**Detailed descriptions of legacy code are explicitly permitted and encouraged.**
Authors may describe legacy routines and variable roles, mathematical formulas,
eligibility tests, branching, loop ordering, indexing, data flow, state changes,
units, discretization, floors/caps, file contracts and downstream consumers.
Describe defects and interactions precisely, including why an old result was
wrong or why an approximation was retained. Names of routines or interfaces
can help readers connect the account across sections.

Use independently written prose, equations, diagrams, tables and explanatory
pseudocode. It is acceptable for these to be detailed enough for a technical
reader to understand the algorithm. Do not impose artificial vagueness or
withhold equations merely because the legacy implementation is unavailable.
Check third-party text, figures and confidential project data separately.

### Code We Author

**Publishing our original code stubs and implementation excerpts is explicitly
allowed and encouraged.** Include actual newly authored routines or concise
standalone excerpts when they clarify the change. Clearly label each as
shipped code, an equivalent explanatory stub, test/observer code or pseudocode.
Do not present a simplified illustration as the executed model.

For each listing record its author/contributor, origin, version/date, purpose,
production relationship and reviewed disclosure status. Explain its inputs,
units, state effects and omitted details. Provide a check or example when it
helps distinguish the intended behavior from a plausible misreading.

An agent-generated listing still needs provenance. Authorship of an edit does
not establish ownership of all surrounding legacy expressions. Renaming or
translating a routine does not by itself make it an independently authored
stub. Mixed-origin material must be separated or described rather than copied
until its publication basis is resolved.

### Material Not Authorized by This Workflow

Do not reproduce raw legacy routines, source-tree excerpts, patch hunks with
legacy context, complete modified legacy files or source attachments unless
the relevant material has specific documented authorization. A generic release
approval does not override the source-publication hold. Existing license
labels, clean-room notes and public URLs do not settle that hold by themselves.

This boundary concerns restricted source text and unreviewed assets. It does
**not** prohibit detailed legacy-code descriptions or our original code stubs.
Do not assert NSERL approval, coauthorship or endorsement without a record.

## Required Account for Each Change

### Scientific Intent

Describe the modeled process and practical problem. Separate a scientific
hypothesis, established implementation defect, parameter inconsistency and
reporting error. Identify intended conserved quantities and what the change
does not calculate. Explain why the selected approximation is defensible and
which simpler or more elaborate alternatives were rejected.

### Legacy and Revised Methods

Give the before/after equations and control flow in descriptive form. Define
every symbol, dimension, spatial basis and time origin. State the valid domain,
zero/negative handling, eligibility boundaries and limiting cases. Explain
numerical resolution, interpolation, clipping, endpoint treatment, normalization
and state persistence where relevant. Identify calculated quantities versus
assumed timing or shape. An effective duration is not necessarily source
support, travel time or a calculated hydrograph.

### Implementation and Coupling

Identify changed routines/components and their responsibilities. Describe
array indexing, invocation order, shared-state mutation, ownership and I/O
semantics when they matter. Explain the failure mechanism and why the repair
addresses it. Use permitted original listings where helpful; describe legacy
code in detail without embedding restricted source.

Trace consequences across domains: runoff and returned water, erosion
hydraulics, detachment/deposition, sediment transport, channel sources/routing,
baseflow, snow/soil water, nutrient calculations, reports and interchange.
List affected and demonstrably unchanged consumers. Mark genuinely unrelated
domains not applicable with a reason; do not claim parity where it was not
tested. Explain operational changes even when scientific equations are unchanged.

### Evidence and Practical Consequences

State build/configuration identities, forcing, geometry, duration, initial
conditions and data provenance. Distinguish generated outputs, static fixtures,
synthetic probes, observations and hypotheses. Preserve same-build hill/pass
and watershed provenance and observer-neutrality checks where applicable.

Show both targeted cases and ordinary controls. Assess total and annual
volumes, daily flow, event delivery, peaks, timing, small events, dry periods,
numerical stability and erosion/sediment consequences as relevant. Keep
hillslope-derived yield, channel volume ledgers and sampled routed integrals
distinct. Explain integration convention, printed precision and discrepancy
signs; do not equate one matching quantity with closure of another.

Use NSE, KGE, R2 and other fit measures as descriptions, not universal gates.
State the actual acceptance standard and decision owner. Explain materiality
through magnitude, frequency, affected conditions and practical consequences.
Do not invent tight tolerances, move thresholds to manufacture a pass or let
aggregate agreement conceal a serious event-level departure. Report failed
attempts and remaining uncertainties that change interpretation. Successful
execution is not observational validation.

### Compatibility and Use

Describe output/schema, reader, parameter-default and workflow implications.
State whether existing inputs or PASS files must be regenerated. Explain
binary pairing, version selection, migration, rollback and known limitations.
Separate release authorization, PDF publication, binary vendoring and deployment.

## Citations, Figures and Accessibility

- Include the author, affiliation, contact email and AI authoring disclosure
  on the first page. The template defaults to Roger Lew, University of Idaho,
  `rogerlew@uidaho.edu`; verify these fields for each report. Describe the AI
  assistance actually used, rather than claiming unperformed review. Keep the
  PDF author metadata aligned with the named human author(s), and distinguish
  AI assistance from independent review and publication approval.
- Cite primary scientific/technical sources for adopted methods. Separate
  published science from project-specific assumptions and engineering choices.
  Verify each citation; do not turn a template placeholder into a bibliography.
- Cite reproducible evidence with release/build identifiers, dataset version,
  configuration and hashes where useful. Explain the result in the document
  even if raw inputs cannot be distributed. Private studies are not required
  public release gates.
- Label every axis, unit, legend, baseline and aggregation window. Distinguish
  instantaneous/model maxima from sampled maxima and daily means. Disclose
  clipping, one-sided events, ties and rounding. Include adverse examples.
- Prefer readable vector plots or adequate-resolution raster figures; inspect
  the rendered page. Use captions and text descriptions, not color alone.
  Keep text selectable and headings/bookmarks useful. Do not claim accessible
  PDF certification without the corresponding review.
- Review plot labels, metadata, screenshots, attachments and links for source
  leakage, private paths, credentials and confidential project information.

## Review and Publication

Use the internal `publication-review.md` checklist. Scientific review checks
the process account and interpretation; numerical/software review checks the
actual implementation and coverage; disclosure review checks source/code/asset
provenance. Record reviewer names, dates, scope and the release owner's decision.
One role is not automatically a substitute for the others.

The template is visibly draft and contains authoring prompts. Fill or remove
all prompts, placeholder references and unsupported claims before approval.
Removing the draft label is an editorial step, not evidence of authorization.
Compile twice with shell escape disabled. Inspect the log, extracted text,
figures, tables, equations, links, bookmarks, metadata and attachments. Automated
scans help but do not certify that restricted material is absent.

Emit LF line endings for generated report metadata and text, including manually
authored registers. Python CSV writers must set `lineterminator="\n"` explicitly;
the default CRLF output can differ from the repository's Git-clean bytes.
Before hashing a source freeze, stage every new generated text artifact through
a private Git index using the repository's clean filters and require its blob
bytes to equal the working file. Normalize first, then hash; do not repair an
issued PDF or manifest silently to accommodate a metadata-only correction.

Freeze the approved TeX, figures and bibliography with a document revision.
Record their hashes internally and the approved PDF hash in the public
manifest. Review the manifest itself for disclosure. It must identify the
actual release and approval, not imply access to a private code repository.
Vendor only the approved PDF and public manifest to WEPPpy; compare hashes
after copying and test the download/navigation path. Preserve previous PDF
revisions and document corrections; never silently overwrite an issued report.

The scaffold does not authorize a PDF upload, source publication, repository
visibility change or production deployment. Those are explicit handoff actions.
