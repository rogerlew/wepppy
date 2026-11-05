# Usersum ADR catalog contract decision

Date: 2026-11-05 UTC. Starting implementation revision: `e2436edb111d57eb9d2da771a9c44ecc658fa8b3`.
Classification: intended additive UI behavior, not a conformance repair.

## Operator direction and authority

Request: “I want to add an ADR listing to the usersum. it should detect and render
all ADRs automatically in reverse chronilogical order”. This authorizes preparing
the feature. An optional ordering question was presented. Subsequent independent review
proved numeric ordering differs from chronology; the revised contract follows
the original request with explicit Date fields descending and undated records
last. No operator approval of numeric ordering is claimed. The operator replied “yes” to the checkpoint commit and implementation request on
2026-11-05; both actions are authorized.

## Applicable contracts and exact delta

- `wepppy/weppcloud/routes/usersum/specification.md`: new **Automatic ADR catalog**
  section governs fixed-root discovery, sort, public listing/detail, freshness,
  strict-manifest independence, link rewriting, valid states and error behavior.
  The manifest-only nav statement gains an explicit dynamic-catalog exception.
- `docs/ui-docs/controller-contract.md`: preserve shared presentation conventions;
  reuse `usersum/layout.j2`, the Feature Catalog pattern and Markdown renderer.
- `docs/standards/user-facing-language-standard.md`: descriptive navigation,
  explicit date ordering, record-status context and empty-state explanation.
- `docs/standards/contract-first-change-standard.md`: independent reviews and
  ancestor checkpoint before implementation.
- `docs/standards/generated-artifact-validation-standard.md`: inspect resulting
  HTML and links from real source files; no run artifacts are mutated.

Only the Usersum domain specification requires a normative amendment. Shared
presentation, generic document-role rules, source-route strict mode, search,
CSRF and model behavior are unchanged. No parameterization ADR is required.

## Rationale and compatibility

A dynamic fixed-root listing avoids maintaining 138 manifest records or a stale
copy of the ADR README index. Dedicated ADR rendering preserves strict source
routing. Existing URLs and documents remain valid. Automatic search enrollment
is excluded because the requested page does not require a search-schema change.

## Security and valid states

Low-impact public file reading: constrain discovery/detail to matching direct
regular files, reject symlinks and path traversal, escape titles, and retain
existing Markdown rendering semantics. Do not interpret query parameters as
filesystem roots. Missing/empty directory is valid; bad encoding/read failures
are explicit errors; missing document is 404. No runtime state is written.
The normative state matrix is in the amended specification.

## Proposed regression evidence

Real temporary directories: missing, empty, mixed files, duplicate IDs, missing/invalid
H1/date/status, additions/edits/removals, unreadable/malformed data, symlinks and
traversal. Route readback: all real repository ADRs, complete Markdown rendering,
relative ADR links, raw/GitHub links, role combinations, strict-manifest on/off,
site prefixes, Help index/sidebar discoverability and non-ADR compatibility.
Run scoped Usersum tests, frontend lint/tests and the substantive-change pytest
gate. Review final implementation independently before completion.

## Review disposition

Two independent read-only reviews are recorded in this directory. Security
review passed; correctness found ordering ambiguity and link-contract issues.
Link rules are amended and independently confirmed. Ordering now follows the
original chronological requirement; both reviewers confirm approval with no
blocking findings. The operator authorized the checkpoint commit and implementation on 2026-11-05. See
`20261105_review_disposition.md`. No implementation edits.
