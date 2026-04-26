# Peridot Documentation Repositioning and Adoption Visibility

**Status**: Done (2026-04-26)
**Timezone**: UTC

## Overview
Peridot is now a production-critical watershed abstraction engine in WEPPpy, but Peridot-repo documentation still reads like a local utility README rather than core platform documentation. This package repositions Peridot docs so users, operators, and developers can quickly understand why it matters, what contracts it guarantees, how it is validated, and how it fits into the broader WEPPpy replacement stack.

Current messaging risk is not only "under-advertising"; it is misclassification. The field still interprets Peridot as a modernized TOPAZ/TOP2WEPP replacement instead of a graph-first abstraction-layer shift. This package makes that distinction explicit and testable in documentation claims.

## Objectives
- Publish a clear Peridot value proposition at the top of the Peridot documentation set.
- Reframe Peridot as a category shift (implicit raster segmentation -> explicit graph abstraction), not as a drop-in modernization story.
- Add explicit contract documentation for watershed outputs and runtime flags, including skip/representative behavior.
- Add migration and operations guidance that makes replacement scope and limits unambiguous.
- Add benchmark methodology and evidence references so performance claims are auditable and reproducible.
- Resolve documentation mismatches between stated outputs and current behavior.

## Scope
This package focuses on documentation architecture, narrative positioning, and contract clarity for Peridot.

### Included
- Peridot `README.md` restructuring to foreground production relevance and WEPPpy integration role.
- Canonical TOPAZ/TOP2WEPP vs `weppcloud-wbt + peridot` paradigm comparison for mental-model reset.
- New Peridot docs for contract, benchmarking, migration, and operations runbook.
- Explicit documentation of current CLI/runtime behavior for `abstract_watershed`, `wbt_abstract_watershed`, and `sub_fields_abstraction`.
- Cross-repo reference alignment updates in WEPPpy docs where Peridot links/claims should point to new canonical Peridot docs.
- Validation notes and artifact capture for doc claim provenance (benchmark source, behavior source, contract source).

### Explicitly Out of Scope
- Peridot algorithm changes or runtime behavior changes (unless a doc bug reveals critical contract ambiguity requiring a separate implementation package).
- WEPPpy orchestration refactors.
- New benchmark generation code beyond lightweight reproducibility commands and evidence capture.
- Marketing website work outside repository docs.

## Stakeholders
- **Primary**: WEPPpy maintainers and operators who depend on Peridot as default abstraction engine.
- **Reviewers**: Peridot maintainers, WEPPpy topology maintainers, query/report consumers of watershed parquet outputs.
- **Security Reviewer**: Not required unless scope expands beyond documentation into runtime behavior changes.
- **Informed**: RQ-engine operators, i-CREWS documentation/procurement maintainers, onboarding contributors.

## Success Criteria
- [x] Peridot README includes a concise "why Peridot matters" section that explicitly states production role in WEPPpy.
- [x] Peridot README includes a concise "category shift, not modernization" statement plus a clear legacy-vs-current paradigm comparison.
- [x] A dedicated Peridot watershed output contract doc exists and is linked from README.
- [x] A dedicated Peridot migration guide exists describing replacement scope versus legacy prepwepp/topaz abstraction behavior.
- [x] A dedicated Peridot operations/troubleshooting doc exists with failure signatures, flags, and expected outputs.
- [x] Benchmark claims are backed by a reproducible method section and linked evidence source.
- [x] Documentation includes a minimal communication kit: one clean claim statement, one comparison-figure specification, and three core metrics definitions (scalability, topology flexibility/correctness, parallelization potential).
- [x] Known docs/runtime mismatches are corrected or explicitly documented as gaps with follow-up references.
- [x] WEPPpy docs that advertise Peridot point to canonical Peridot docs rather than scattered claims.
- [x] Work-package tracker and artifacts capture decisions, evidence, and closure outcomes.

## Dependencies

### Prerequisites
- Existing Peridot docs and code in `/home/workdir/peridot`.
- Existing WEPPpy Peridot integration surfaces in `/home/workdir/wepppy/wepppy/topo/peridot/` and `wepppy/nodb/core/watershed_mixins.py`.
- Existing WEPPpy work-package artifacts documenting recent Peridot contract evolution.

### Blocks
- Follow-on Peridot onboarding documentation improvements should consume this package's contract and operations docs.
- Any external communication that cites Peridot performance should wait for this package's benchmark-method section.

## Related Packages
- **Depends on**: Existing Peridot behavior/contract outputs from [20260321_peridot_watershed_parquet_manifest](../20260321_peridot_watershed_parquet_manifest/package.md).
- **Related**: [20260422_peridot_side_hillslope_length_capping](../20260422_peridot_side_hillslope_length_capping/package.md).
- **Related**: [20260403_roads_map_drilldown](../20260403_roads_map_drilldown/package.md) (shared watershed-output consumer context).
- **Follow-up**: Optional Peridot runtime error-contract hardening package if doc audit findings require behavior changes.

## Timeline Estimate
- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Low-Medium (risk is primarily contract misstatement, not runtime regression).

## Security Impact and Review Gate
- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: Scope is documentation-only with no new attack surface, auth, secrets, path-ingress, or queue behavior modifications.
- **Security review artifact**: `N/A`

## References
- `/home/workdir/peridot/README.md` - current primary Peridot documentation entrypoint.
- `/home/workdir/peridot/dev-notes.md` - implementation-oriented notes.
- `/home/workdir/peridot/sub_fields_abstraction.spec.md` - detailed sub-fields design/spec context.
- `/home/workdir/peridot/src/watershed_abstraction/watershed_manifest.rs` - watershed table schema declarations.
- `/home/workdir/peridot/src/bin/abstract_watershed.rs` - CLI entrypoint and current error propagation behavior.
- `/home/workdir/peridot/src/bin/wbt_abstract_watershed.rs` - WBT CLI entrypoint behavior.
- `/home/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py` - production callsite for Peridot abstraction.
- `/home/workdir/wepppy/wepppy/README.md` - current WEPPpy-level Peridot positioning statements.
- `/home/workdir/wepppy/docs/projects/i-crews/st_joe/procurement-request.md` - current cross-stack performance narrative.

## Deliverables
- Revised Peridot `README.md` with production positioning and canonical links.
- New Peridot docs:
  - `docs/contracts/watershed-output-contract.md`
  - `docs/benchmarks.md`
  - `docs/migration/prepwepp-to-peridot.md`
  - `docs/operations.md`
- Package artifact capturing GPT-5.5 directional messaging guidance and resulting claim constraints.
- Any required WEPPpy doc-link alignment updates.
- Work-package artifacts capturing claim provenance and validation notes.

## Follow-up Work
- Optional runtime package to align CLI error propagation with documented contract if behavior hardening is approved.
- Optional docs package for Peridot API-level generated docs (`cargo doc` onboarding and publishing policy).

## Closure Notes

**Closed**: 2026-04-26

**Summary**: Completed cross-repo documentation repositioning. Peridot README now leads with category-shift framing, legacy-vs-current comparison, replacement boundaries, canonical docs, and communication kit. New canonical Peridot docs define watershed outputs, benchmark discipline, prepwepp/TOPAZ migration, and operations validation. WEPPpy references now point to canonical Peridot docs and avoid unqualified speedup claims.

**Lessons Learned**: The main documentation defect was not only weak positioning; it was contract drift. The old Peridot README still advertised watershed CSV outputs that the current CLI path does not write. Capturing that mismatch in the output contract and operations runbook avoided a runtime change under a docs-only package.

**Archive Status**: Package closed in place; active ExecPlan retained with completed progress and revision notes.
