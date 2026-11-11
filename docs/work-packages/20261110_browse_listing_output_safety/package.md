# Browse listing output safety

**Status**: Open (2026-11-11 UTC); M0-M3 implemented and locally validated, M4 pending

**Timezone**: UTC

## Overview

Remediate security audit finding F3/SEC-03 by making filesystem-derived names
and symlink display values inert in WEPPcloud browse directory pages. The
current renderer interpolates these values into assembled HTML and then marks
the result trusted. It also reuses raw filename text in browse, download,
preview, schema, D-Tale, and diff URLs. A user who can introduce a project file
can therefore store HTML or an attribute-breaking value that executes in the
same origin when a collaborator or administrator opens the directory listing.

The repair is an output-boundary change, not a filename admission policy.
Authorized files with punctuation, whitespace, Unicode, percent signs, or path
separator lookalikes remain visible under their actual names. Display text is
HTML-escaped and each filesystem name is encoded as one URL path segment before
links are composed. Validation is intentionally limited to the renderer and
browse-route tests changed by the patch; the full repository suite is explicitly
not required for this package.

## Threat Model

- **Asset at risk**: same-origin browser authority, private run data, and any
  action available to a collaborator or administrator viewing the listing.
- **Attacker capability**: legitimate project-file write authority, including a
  Bootstrap Git push or another authorized artifact producer that can choose a
  filename or symlink target.
- **Trust boundary**: filesystem entry metadata crosses into HTML text and URL
  attributes rendered by the browse microservice.
- **High-value path**: store markup in a filename, wait for a higher-privilege
  user to browse the directory, and obtain same-origin script execution.
- **Assumptions**: existing run authorization and filesystem containment remain
  correct and unchanged; filenames are data, not HTML; URL encoding is applied
  exactly once to each name segment.

## Objectives

- Render filenames, directory names, symlink targets, and filesystem-derived
  breadcrumb labels only as text.
- Encode each filename or directory name as one URL path segment before building
  browse and action links.
- Keep query parameters encoded with the existing query encoder and prevent
  filename data from creating attributes, query parameters, or path structure.
- Replace or constrain the current broad `Markup()` trust boundary so only HTML
  produced by a renderer that escapes every untrusted field is marked safe.
- Preserve normal ASCII and Unicode listings, sorting, filtering, pagination,
  directory traversal, downloads, previews, D-Tale, schema, and diff actions.
- Cover the confirmed breadcrumb consumer of the same unsafe assembly pattern.
- Prove the repair with inert temporary filesystem entries and focused tests.

## Scope

### Included

- `wepppy/microservices/browse/listing.py`, especially `html_dir_list()` and all
  directory-row action URLs.
- `wepppy/microservices/browse/flow.py`, especially filesystem-derived
  breadcrumbs and the trusted-markup handoff to `browse/directory.htm`.
- `wepppy/microservices/browse/browse.py` only if its not-found breadcrumbs or
  equivalent shared path rendering require the same output-safety helper.
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm` if the chosen
  structured rendering boundary moves markup into Jinja.
- Focused tests in `tests/microservices/test_browse_routes.py` and, only if the
  implementation creates a separately testable renderer, one new adjacent unit
  test module.
- The canonical browse filesystem contract and directly affected browse docs.

### Explicitly Out of Scope

- Rejecting, renaming, normalizing, or deleting valid filesystem names.
- Changing Bootstrap path admission or Git history.
- Authentication, authorization, containment, symlink traversal policy, PII
  filtering, download contents, or file parsing behavior.
- JSON files APIs whose serializers already encode strings as JSON; their
  unchanged status must be verified by review rather than broad test expansion.
- A site-wide Content Security Policy. CSP is useful defense in depth but has a
  separate compatibility and rollout surface; it is not required to close F3.
- Audit findings F1, F2, or F4-F8, frontend refactors, new dependencies, or
  deployment topology changes.
- The full Python or frontend test suites.

## Complexity Budget

- **Existing mechanisms reused**: Jinja autoescaping, `markupsafe.escape`,
  `urllib.parse.quote`, `urlencode`, the current browse template, and route tests.
- **New mechanisms permitted**: one small renderer/helper boundary that
  distinguishes display text, URL path segments, and query values.
- **Simplest plausible change tested first**: explicit escaping plus per-segment
  encoding while retaining current layout and action behavior.
- **Real acceptance condition**: hostile filesystem strings produce no element,
  event-handler attribute, extra URL component, or route escape in response HTML.
- **Evidence required before escalation**: a focused failing regression showing
  the small renderer cannot safely preserve an existing browse action.
- **Explicitly prohibited expansion**: a new framework, sanitizer dependency,
  filename allowlist, URL service, or site-wide template rewrite.

## Generated Artifact Validation Gate

- **Applicable**: yes, narrowly, because the user-visible HTML is a generated
  artifact assembled from filesystem metadata.
- **Intent evidence**: the exact temporary filenames and symlink display values
  created by each regression.
- **Persisted-state evidence**: direct directory readback proves those exact
  entries exist and were not renamed or filtered.
- **Prepared-input evidence**: renderer inputs retain the original Unicode and
  punctuation strings.
- **Execution/output evidence**: route response HTML contains escaped text and
  correctly encoded links, with no injected element or attribute.
- **User-facing evidence**: ordinary links still resolve to the intended file or
  directory and existing actions remain available.
- **Direct unmocked boundary**: real entries and symlinks under `tmp_path`, served
  through the browse test application.
- **Actual-project/environment gate**: scoped wepp1-equivalent smoke only when a
  deployment is separately authorized; no payload is tested on production.
- **Highest completion claim currently supported**: diagnosed and scaffolded.

## Stakeholders

- **Primary**: WEPPcloud users, maintainers, and the wepp1 operator.
- **Reviewers**: browse correctness/UX, QA/code quality, and security.
- **Security reviewer**: required and independent of the implementation author.
- **Informed**: Bootstrap and artifact-producing maintainers; their filename
  behavior is preserved.

## Success Criteria

- [ ] File and directory labels encode `&`, `<`, `>`, double quote, and single
      quote as inert text in HTML output.
- [ ] Symlink display targets receive the same text-context escaping.
- [ ] Spaces, `#`, `?`, `%`, quotes, Unicode, and separator lookalikes are encoded
      as exactly one filename path segment in every generated link.
- [ ] Browse, download, raster info, annotated preview, D-Tale, schema, CSV, and
      diff URLs remain inside their intended route and preserve query parameters.
- [ ] Breadcrumbs for stored directory names cannot create markup or attributes.
- [ ] No untrusted filesystem value crosses a broad safe-markup boundary without
      context-appropriate escaping.
- [ ] Ordinary ASCII and Unicode names remain visible and navigable; no filename
      allowlist or silent filtering is introduced.
- [ ] Focused browse renderer/route tests, scoped docs lint, and independent
      correctness, QA, and security reviews pass.
- [ ] No full-suite result is required or presented as package evidence.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes, in the contract decision artifact.

## Dependencies

### Prerequisites

- Amend the browse filesystem contract with the output-encoding rule.
- Complete the failure-class inventory and independent contract/security review
  before production implementation.

### Blocks

- Closure of security audit finding F3/SEC-03.

## Related Packages

- **Related**:
  [Pickle artifact restriction](../20261110_pickle_artifact_restriction/package.md)
  changes parser capability, not browse HTML encoding.
- **Canonical contract**:
  [Browse filesystem contract](../../schemas/browse-filesystem-contract.md).

## Timeline Estimate

- **Expected duration**: 1-3 focused implementation/review days.
- **Complexity**: low-to-moderate, with several action-link variants sharing one
  rendering boundary.
- **Risk level**: high security impact and moderate compatibility sensitivity.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: this package changes the rendering of attacker-controlled
  filesystem metadata on an authenticated same-origin page.
- **CWE/OWASP mapping**: CWE-79; OWASP Top 10 2021 A03 Injection.
- **Security review artifact**:
  [artifacts/20261110_security_review.md](artifacts/20261110_security_review.md).

## Hardening and Callus Softening

- **Failure signature**: filesystem-derived text appears unescaped in trusted
  browse HTML or raw in a URL attribute.
- **Failure-class boundary**: directory rows, their action links, symlink display
  text, and filesystem-derived breadcrumbs.
- **Health signals**: inert hostile-string corpus, valid link resolution, and no
  raw filesystem value in an HTML or URL context.
- **Danger signals**: double encoding, broken Unicode navigation, lost query
  parameters, action disappearance, raw `safe`/`Markup` use around assembled
  untrusted values, or filename filtering.
- **Observation model**: stateless recurrence trigger. Any new browse renderer
  that interpolates filesystem metadata without contextual encoding reopens the
  finding.
- **Temporary calluses introduced**: none.

## Validation Scope Decision

The operator explicitly requested tests scoped to the patches. Required
validation is therefore limited to:

- `tests/microservices/test_browse_routes.py`, selecting the new output-safety
  tests and existing directory/action controls affected by the patch;
- one adjacent renderer unit module only if the implementation creates it;
- scoped documentation lint and source review of changed trusted-markup sites.

Use `wctl run-pytest` for those exact paths or node IDs. Do not run the full
Python suite. Frontend npm gates are not required unless implementation expands
into frontend source; that expansion must first be recorded in the plan and
tracker.

## References

- `wepppy/microservices/browse/listing.py:763-955`
- `wepppy/microservices/browse/flow.py:410-457,515-594`
- `wepppy/microservices/browse/browse.py:783-834`
- `wepppy/weppcloud/routes/browse/templates/browse/directory.htm`
- `tests/microservices/test_browse_routes.py`
- [Active ExecPlan](prompts/active/implementation_execplan.md)
- [Contract decision](artifacts/20261110_contract_decision.md)
- [Failure-class matrix](artifacts/20261110_failure_class_matrix.md)
- [Correctness review](artifacts/20261110_correctness_review.md)

## Deliverables

- Canonical browse output-encoding contract amendment.
- Minimal renderer/template change with focused regression coverage.
- Failure-class, validation, correctness/UX, QA, and security evidence.
- Scoped wepp1 rollout and rollback evidence only when separately authorized.

## Follow-up Work

Evaluate a site-wide CSP in report-only mode under a separate work package. CSP
must remain defense in depth and must not substitute for contextual output
encoding.
