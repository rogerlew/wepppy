# WP12 final feature-branch scope audit

**Audit date**: 2026-08-31

**Canonical merge base**: `6af9ecdd63921189804c5e292114a97253914cbb`

**Initial audited feature candidate**: `30b30b3c6e2cf99aba47cf8ea3c2b8988f8dc381`

**Validated pre-merge candidate**: `039192492ffec38782893a603916a2e91918cfca`

**Initiative branch**: `feature/project-owned-config`

**Canonical branch**: `master`

**Promotion policy**: merge only at the roadmap promotion gate

## Result

The repeated amendment 4 and amendment 5 comparisons match their ratified
boundaries. No changed production or test path in either range is unexplained.
Changes after amendment 5 are also accepted, but they are not silently folded
into amendment 5: each group is classified below as a ratified WP12D
continuation, an accepted project-config integration correction, or separately
governed branch work explicitly requested and accepted by the operator.

This audit finds no behavioral scope requiring a new project-config contract
amendment. WP12 may carry the complete branch candidate after final validation
and review. The merge must preserve the commits and their independent package
provenance rather than representing every branch change as PC-24 work.

## Amendment 4 repetition

Command:

    git diff --name-only 596ff5758..588608f1a | sort

The repeated range is identical to the range named by ratified correction
`PC-24/WP12D-20260828-4`. Production/configuration consumers, paired tests,
generated RQ evidence, and package evidence map to the accepted WP12D boundary.
The repeated comparison retains the correction's three support entries:

1. `wepppy/nodb/locales/__init__.py` is export-only.
2. `wepppy/nodb/locales/capability_structures/README.md` and `catalog.json`
   are the append-only reader-floor authority and its maintenance contract.
3. `wepppy/microservices/rq_engine/auth.py` and
   `tests/microservices/test_rq_engine_auth.py` are the accepted signed numeric
   identity-handoff correction.

No new path appeared in the historical range. The authoritative correction
remains
`docs/work-packages/20260827_project_config_run_ui_authority/artifacts/20260828_scope_audit_correction.md`.

## Amendment 5 repetition

Command:

    git diff --name-only 0ad76c547..b772877c4 | sort

Every production path is in the exact source boundary documented under
`Exact source boundary` in
`artifacts/20260828_climate_landcover_contract_decision.md`. Every test path is
in that decision's direct regression list. Remaining paths are the exact
canonical contract, ADR, RQ/controller contract, project tracker, work-package
decision/review/evidence, and Forest-acceptance surfaces named by the same
decision and ExecPlan. No production or test path falls outside the ratified
amendment-5 list.

The range ends at `b772877c4`, the documentation commit that records the exact
Forest writer and rollback acceptance for candidate `09ad4fbde` and writer
checkpoint `1e30f7705`.

## Post-amendment disposition

The commits after `b772877c4` are accepted as follows.

### Ratified WP12D continuations

- `8e62aefba` through `5bb8676bb`: amendment 6 removes manual Review
  Selections and adds initial/change-driven validation. The operator ratified
  `PC-13/WP12D-20260828-6`; its contract, tests, controller source, template,
  README, and review paths match the exact boundary.
- `8a15b963c` through `75eb240c8`: amendment 7 makes the run page title the
  exact route run ID. The operator ratified `PC-13/WP12D-20260828-7`; its
  template, Project controller, tests, generated-source README, and review
  paths match the exact boundary.
- `3f0ad88bd`: the Australia land-cover default integration correction is
  documented in the WP12D ExecPlan/tracker and covered by rendered-control
  tests. It corrects presentation of already-ratified locale authority without
  changing the capability envelope.
- `62336c284` and `a3e49f016`: the capability-refresh modal/theme and valid
  owner-token integration corrections update the canonical contract and direct
  frontend/rendered-control tests. They preserve the existing authenticated
  owner/Admin/Root authorization boundary and were accepted through Forest
  end-user exercise.
- `2f5fc7504` and `30b30b3c6`: final Forest evidence and WP12C closure records;
  documentation only.

### Separately governed accepted branch work

- `a1db47377` and `7de00e8ce`: table-overflow accessibility package, including
  three-decimal report slope presentation. It has its own accepted contract,
  reviews, tests, package, and Forest user acceptance.
- `817bbc9ae`, `ac1bd5bab`, and `f236c60e3`: ESDAC rejection diagnostics and
  browser propagation, governed by the existing EU disturbed soil hardening
  package and direct unmocked/contract tests.
- `36bbdb60a`: session-cookie production activation evidence; documentation
  only in its existing package.
- `058d849ae`: CAP token-continuity hardening with its existing package,
  incident record, validation script, documentation, and canary evidence.
- `4b8952f42`: operator-requested removal of Google Analytics from the Portland
  page. The operator explicitly directed that this bounded one-template change
  not receive a work package.
- `2e34740c9`: generated code-quality observability reports; no runtime change.

These changes are not prerequisites invented by WP12. They were already
committed, pushed, individually tested or reviewed, and explicitly accepted on
the initiative branch. Carrying them preserves the reviewed linear candidate;
excluding them would require history rewriting or a new selectively assembled
release boundary and would reduce, rather than improve, correspondence with the
Forest-tested revision.

## Pre-merge condition

At audit start, `git diff --check origin/master...HEAD` identified six review
artifacts with one extra blank line at EOF. WP12 removes only those trailing
blank lines. The final candidate must rerun `git diff --check`, scoped docs
lint, and the complete automated gates after the WP12 audit commit. Any new
production/test path after this audit reopens the comparison before merge.

The validation pass added one path after the initial audit:
`wepppy/nodb/project_config_snapshot.pyi`. Its runtime module and
`resolve_preset_locale_projection` behavior were already inside amendment 5's
exact source boundary, but the public stub omitted that exported helper. Adding
the exact runtime signature is an additive type-surface conformance correction,
not a behavioral change. Direct snapshot/capability tests and runtime/stub
comparisons pass. The generated RQ catalog/JSON paths were already in the
accepted branch boundary; final validation refreshed only the unchanged
`upload_cli_rq` enqueue source line. No dependency edge changed.

The validated candidate therefore adds only scaffold/audit/review evidence,
the six content-neutral EOF corrections, the exact additive public stub, and
the generated source-line/observability refreshes described above. The repeated
scope result remains pass at `039192492ffec38782893a603916a2e91918cfca`.
