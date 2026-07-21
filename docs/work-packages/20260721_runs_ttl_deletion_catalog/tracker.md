# Tracker - Runs TTL Deletion Catalog

## Quick Status

**Timezone**: UTC  
**Started**: 2026-07-21 22:15 UTC  
**Current phase**: Complete
**Security impact**: high  
**Dedicated security review**: yes

## Task Board

### In Progress

- [x] Record the operator-approved contract decision and register REM-02.
- [x] Obtain post-fix confirmation from two independent read-only reviewers.
- [x] Implement the bounded route/template/Usersum/test changes.

### Done

- [x] Commit the accepted GOV-00A-M1B contract ancestor
  `d3380287ca706360879240c3d203c5e7cc2be9ef` before production implementation.
- [x] Complete final independent contract and security reviews with no unresolved
  high/medium findings.
- [x] Validate focused route/TTL/Usersum tests, frontend lint and tests,
  documentation lint, broad-exception enforcement, and diff hygiene.

## Source Matrix

| Surface | Owner / role | Intended change |
| --- | --- | --- |
| `wepppy/weppcloud/utils/run_ttl.py` | TTL metadata authority | Read `policy` and `expires_at`; no mutation or policy change. |
| `wepppy/weppcloud/routes/user.py` | Runs catalog payload | Add `ttl_deletion_at` to every selected row after existing user filtering; inactive/fallback states are `null`. |
| `wepppy/weppcloud/templates/user/runs2.html` | Runs table renderer | Render active expiry plus doc link, or last-modified fallback when disabled. |
| `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`, `nav_tree.yaml`, `usersum.py`, `weppcloud/run-ttl-deletion.md` | User documentation | Publish and resolve the dedicated policy guide. |
| Named catalog/template/Usersum test files in REM-02 register | Regression evidence | Exercise metadata, rendering, no-read ordering, and Usersum resolution. |

## Decision Log

- **2026-07-21 22:15 UTC — Column semantics**: The single existing
  Last Modified column becomes a lifecycle-status column. For a rolling policy,
  it shows the computed deletion time. For a disabled/excluded/non-expiring
  policy, it retains a clearly labeled last-modified fallback rather than
  inventing an expiration.
- **2026-07-21 22:15 UTC — Link target**: `Learn More` points to the canonical
  Usersum doc-id route, not a hard-coded source path, so Markdown rendering and
  access policy remain centralized.
- **2026-07-21 23:15 UTC — Reader fallback and sorting**: Preserve the existing
  `last_modified` header sort even though its label changes to TTL Deletion.
  Treat invalid UTF-8 as finite malformed TTL input in the read-only reader,
  rather than allowing a catalog request to fail.

## Dispatch Log

| Time (UTC) | Agent/role | Scope | Edit authority | Outcome |
| --- | --- | --- | --- | --- |
| 2026-07-21 22:15 | Primary Codex | Scope, baseline, contract draft | Documentation only | In progress |
| 2026-07-21 22:15 | `/root/rem02_contract_review` | First contract/authority review | Read-only | Rejected: 3 high, 3 medium, 2 low; corrections drafted |
| 2026-07-21 22:15 | `/root/rem02_security_qa_review` | First security/regression review | Read-only | Rejected: 1 high, 5 medium, 1 low; corrections drafted |
| 2026-07-21 22:45 | `/root/rem02_contract_review` | Post-fix contract confirmation | Read-only | Approved; no unresolved high/medium findings |
| 2026-07-21 22:45 | `/root/rem02_security_qa_review` | Post-fix security/regression confirmation | Read-only | Approved; no unresolved high/medium findings |
| 2026-07-21 23:15 | `/root/rem02_contract_review` | Final implementation contract review | Read-only | Approved for closure; no unresolved high/medium findings |
| 2026-07-21 23:15 | `/root/rem02_security_qa_review` | Final implementation security/regression review | Read-only | Approved for closure; no unresolved high/medium findings |

## Progress Notes

### 2026-07-21 22:15 UTC: Baseline and contract checkpoint drafted

The user explicitly authorized full work-package execution, including contract
work and reviews. Existing TTL state has `policy` and `expires_at`; the catalog
already reads each run's directory metadata only when Ron metadata is included.
No production implementation has been edited. The checkpoint and registration
must receive independent review and be committed as an ancestor before code work.

### 2026-07-21 22:35 UTC: First review disposition

Both reviewers correctly found that REM-01's GOV-00A-M1A milestone could not be
reused. The corrected checkpoint registers GOV-00A-M1B, names exact files,
requires a Jinja deployment-aware link, defines timestamp and
malformed-state fallback behavior, and adds owner-filtering/no-read evidence.
Post-fix confirmation is now required before the standalone ancestor commit.

### 2026-07-21 22:55 UTC: Contract ancestor accepted

Both independent reviewers approved the corrected checkpoint. The documentation-
only GOV-00A-M1B ancestor was committed at
`d3380287ca706360879240c3d203c5e7cc2be9ef`; implementation may now begin only
within REM-02's exact source boundary.

### 2026-07-21 23:15 UTC: Implementation and review closure

The catalog now adds a nullable, normalized `ttl_deletion_at` only after its
existing row authorization. The lifecycle column remains sortable by
`last_modified`, shows an active TTL expiry with a same-origin Usersum link,
and otherwise shows Last Modified. The dedicated guide is public to authenticated
Usersum users. Final reviewers required and confirmed UTF-8 malformed-payload
fallback/no-write behavior and executable DOM branch coverage. The generated
Usersum index was rebuilt for validation and intentionally left uncommitted.
