# SUDI-02 independent contract correctness review

Reviewer: `/root/soil_format_contract_correctness`. Date: 2026-09-26 UTC.
Starting implementation: `64dc33a0d54c278b9a3de5ff4e196916792bdd12`.
Scope: proposed SUDI-02 admission/preservation contract, ADR-0075 amendment,
active soil-format ExecPlan, native reader and existing WSU/preparation paths.
This is a read-only pre-implementation review; only this review artifact changed.

## Findings and disposition

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| SFC-01 | Medium | Existing `WeppSoilUtil.modify_kslast` suppresses explicit overrides when the supplied 9002 label contains `developed`. This would violate independent uploaded-soil modifier behavior. | Resolved in contract: the preserving upload path must bypass this label policy; ordinary catalog behavior remains unchanged. Require a developed-label override regression. |
| SFC-02 | Medium | Existing `clip_soil_depth` can retain a boundary horizon and append the next horizon at the same depth, causing strict generated-file rejection for a valid exact-boundary choice. | Resolved in contract: preserving uploads stop at the existing horizon. Require exact-boundary generated-file validation while retaining ordinary behavior. |
| SFC-03 | Low | The first draft explicitly bounded CEC only for 7778/9002, leaving older-format CEC admission unclear. | Resolved: the amended all-version requirements explicitly state nonnegative CEC. |

## Native and preparation evidence

- `/workdir/wepp-forest/src/infile.for:1949` uses `nint(datver)`; 2006.2
  therefore uses the 2006 native layout. `input.for:479-495` reads nine header
  fields including `avke` for both versions. Rejecting eight-field 2006.2
  input avoids stealing the next record or silently inventing conductivity.
- `input.for:541-558` reads six layer values for 2006, eleven for 7778 and
  eighteen for 9002. `input.for:638-666` confirms version-specific restrictive
  records. The proposed widths preserve the native distinction.
- `wepppy/wepp/soils/utils/multi_ofe.py:53` copies complete records after the
  first three noncomment records. Repeating the same valid source preserves
  version and profile values without rewriting the stacker.
- WSU currently discards 2006.2 `avke`, ignores the seven 9002 hydraulic fields,
  and recalculates them during serialization. The explicit preserving mode
  avoids changing ordinary catalog/Disturbed serialization.
- `wepppy/nodb/core/wepp.py:_soil_has_symbolic_wepp_parameters` considers older
  formats' absent layer conductivity symbolic. The preserving path must bypass
  that conversion, while keeping legacy symbolic-template handling.
- Existing bulk-density derivation used for reports/management remains an
  independent legacy behavior; it cannot alter generated uploaded soil records.
- Native 9002 `ksatadj` behavior is input-authored model behavior. The exponential
  recovery expression in `infpar.for:636-638` belongs only to 9001, which remains
  unsupported; it is not a 9002 admission constraint.

## State and regression assessment

The plan separately names absent/empty sources, populated supported versions,
legacy 7778, reuse, failed replacement, missing accepted bytes, archive/restore,
and working/failed/completed observations. Existing error codes and publication
boundaries remain normative. New malformed formats must fail before publication;
valid sources must preserve source bytes and actual canonical version metadata.

Required final evidence is direct source publication/reload and consumed-file
inspection across 1, 2, 12 and 32 OFEs for all four formats, followed by native
`wepp_260803` execution. Nondefault `avke`, 9002 hydraulic sentinels, differing
base/appended water fractions, both adjustment flags, restrictive values,
saturation/depth/kslast modifiers, and ordinary non-preserving WSU regressions
must demonstrate semantics rather than file existence alone.

## Verdict

The contract design is approved. Include this review and the separate security
review in the standalone checkpoint ancestor before implementation.
No open high/medium design findings remain after the author amendments reviewed
above. Native round trips, compatibility, publication/error states and final
generated artifacts are implementation coverage obligations, not yet validated
outcomes. This review does not approve deployment or close the final review gate.
