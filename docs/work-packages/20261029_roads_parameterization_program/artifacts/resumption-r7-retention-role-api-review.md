# Revision-7 retention role API review

Date: 2026-11-03 UTC. Independent review by `mipa_contract_scope`.
Scope: read-only code, lookup and retained input inspection. No acquisition,
source generation, treatment build, native execution or production edit.

## Verdict

**The frozen U12 role conditioning is expressible through the existing admitted
APIs without an extension.** Its road erosion overrides and upper-200-mm K cap
can be composed into the existing Disturbed worker's replacement dictionary,
before the worker writes its treatment companion. Then use the admitted stack
and unclipped staging. The old bridge's direct rewrite must not be reused.

This resolves the API uncertainty in the
[feasibility review](resumption-r7-retention-feasibility-review.md). Fresh bounded
source acquisition would not be wasted on an identified role API incompatibility.
Acquisition association, paired artifact verification and native evidence remain
required; code inspection does not claim that a fresh build has passed.

## Why the composition is exact

In [builder_bridge.py](builder_bridge.py), `roles()` first applies the bare lookup
to all upper-200-mm road/fill rows. `inject()` subsequently copies the matched
legacy road's `ki`, `kr` and `shcrit`, sets road `ksatadj=0`, and applies
`min(conditioned_K, legacy_avke)` to the road's upper rows. The relevant bare
lookup `avke` values are literal positive scalars, so conditioned upper K is
already the same scalar in every affected row. Consequently:

```text
road upper K = min(bare lookup avke, matched frozen legacy road avke)
fill upper K = bare lookup avke
buffer upper K = forest lookup avke
```

`WeppSoilUtil.to_over9000()` already applies literal `avke` replacements only
through 200 mm and preserves deeper K. It already accepts `ki`, `kr`, `shcrit`,
`ksatadj`, `ksatfac`, `ksatrec`, `luse` and `stext`. Therefore one worker treatment
per role produces the same numeric transformation as the two old operations.
This is composition of frozen inputs, not a new multiplier or newly fitted cap.

Read-only verification covered all 840 development tasks in the current panel
declaration and 480 unique matched legacy soil **inputs**. It found zero
mismatches across 2520 role headers, 4680 upper rows and 6840 deeper role rows.
It also checked equal depth, density, FC, WP and RFG across the three frozen roles.
No legacy or modern outcome file was read for this check.

| Material | Generated texture | Bare upper K, mm/h | Forest upper K, mm/h |
| --- | --- | ---: | ---: |
| 1718465 | sand loam | 10 | 60 |
| 1718494 | loam | 10 | 50 |
| 1718510 | clay loam | 6 | 35 |
| 1856573 | loam | 10 | 50 |
| 2711184 | loam | 10 | 50 |
| 2711250 | silt loam | 6 | 40 |
| 53949 | loam | 10 | 50 |

For B3, the supported road replacements are `avke=8.1`, `ki=2000000`,
`kr=0.0003`, `shcrit=2`, `ksatadj=0`, with existing bare `ksatfac=100` and
`ksatrec=0.3`. The frozen global `ksflag` is 0. These values are read from bound
inputs, not recommendations to hard-code them for other cases.

## Exact supported sequence

1. After the separate acquisition/source gate, build the paired default and
   explicit-policy 7778 source files with the existing builder. Each arm uses
   its own fresh caller-owned root. Put that arm's source files, role treatments
   and MOFE stack together in `root/soils/`. The current producer-boundary
   validators default their parent authority to the input directory; splitting
   source and role parents into unrelated sibling directories would fail it.
2. Copy the bound existing bare and forest lookup dictionaries. For the road,
   copy bare and replace only `ki`, `kr`, `shcrit`, `ksatadj` and `avke` as above.
   Preserve the lookup's blank density and set recomputation false. Retain the
   lookup hash, matched legacy input hash, role order and composed dictionaries
   in the experiment declaration. Never edit the global lookup or stored project
   settings to implement the comparison.
3. Invoke the ordinary installed `_build_disturbed_mofe_soil` once per role,
   each directly from the corresponding source file, with fresh destinations.
   Do not feed the road worker an already converted treatment: the admitted
   source boundary requires source-v3, 7778 and one OFE. The task shape is:

   ```python
   task = dict(
       source_soil_path=str(source),
       output_path=str(role_path),
       disturbed_mukey=declared_role_key,
       replacements=role_replacements,
       sol_ver=9002,
       h0_max_om=None,
       recompute_wp_fc_using_rosetta_on_bd_override=False,
   )
   _build_disturbed_mofe_soil(task)
   ```

   The real worker runs `check_treatment_task`, conversion, exclusive publication
   and `finish_treatment_task`. The latter rejects any change to source depth,
   density, FC, WP or RFG and binds the actual changed K rows in treatment-v3.
   Source generation already supplies the 200 mm split; no new geometric repair
   is necessary. Do not bypass the worker or manually issue a companion after
   editing a published file.
4. Stack the declared role paths with
   `SoilMultipleOfeSynth(ordered_role_paths).write(stack_path, ksflag=frozen_ksflag)`.
   For this frozen panel the order is road/fill/buffer. Bind each case's actual
   order rather than borrowing a different production geometry's order. The
   optional arm must contain only marked treatment-v3 inputs; the ordinary
   default arm remains unmarked and follows its existing writer behavior.
5. Call the ordinary `prep_soil` on that stack, not on individual treatments:

   ```python
   prep_soil((
       declared_case_key, str(stack_path), str(final_path),
       None, None, 0.75, False, 700, False, None,
   ))
   ```

   These are the frozen bridge's settings: no restrictive-conductivity override,
   saturation 0.75, no clipping and no minimum-depth extension. The 700 argument
   is inactive when clipping is false. Applying saturation once after stacking
   commutes with the earlier per-role saturation operation. This preserves the
   1718494 990–1600 mm changed row. The admitted stage accepts unclipped stacks.
6. Recursively validate the final optional artifact using
   `load_source_companion(final_path, provenance_root=root)`, then independently
   compare actual source, treatment, stack and staged rows. Default outputs do
   not receive fabricated opt-in companions: the paired experiment receipt binds
   their hashes and readbacks separately. Preserve all other frozen native
   inputs and record source-vintage drift before any model call.

Actual worker imports must be normal installed imports. All optional targets
must be fresh; source/parent references remain hash-bound, confined and free of
symlink traversal. No post-treatment or post-stack mutation is part of this path.

## Limits and authority

The exact scalar composition depends on the verified literal bare lookup and
frozen U12 semantics. If a future lookup instead applies a multiplier or yields
different upper-row K values, a single literal cannot generally express a
per-row cap. Stop and identify that actual failure before proposing an extension.
Likewise, density changes, FC/WP repair, row removal, mixed-policy stacking and
unrepresented geometry changes remain outside this admission.

No production API extension, parameterization ADR amendment or new default
authorization is needed for the demonstrated sequence. Record its bounded use
in the experiment protocol under the existing Roads autonomy before execution.
A future new transformation would need a contract-first proposal, rationale and
independent source-to-final companion/unchanged-state review; any new formula,
threshold or heuristic also needs the parameterization ADR process. The read-only
task provides no authority to make those changes or to deploy anything.

## Evidence binding

Panel declaration:
`/wc1/runs/ro/roads-parameterization-program-20261103/panel840-v1/declaration.json`,
SHA256 `68fa8f4507821db21e104a625da0f6ba6401136bc6408594c4051344a51f6b04`.
Lookup SHA256:
`bf4b38fbcb16643345b29e24a1ace6afd8409695cf0b27dbbb707e4707620a67`.
B3 matched legacy `runs/p1.sol` SHA256:
`00f24b95df6d590d2c1ca96820208019a9953b1470415f274e2cf970d7b3a1f5`.

The code review covers `check_treatment_task` / `finish_treatment_task` /
`prepare_stack` / `prepare_stage` in `wepppy/soils/ssurgo/retention.py`,
`_build_disturbed_mofe_soil` in `wepppy/nodb/mods/disturbed/disturbed.py`,
`to_over9000` in `wepppy/wepp/soils/utils/wepp_soil_util.py`,
`SoilMultipleOfeSynth.write` in `wepppy/wepp/soils/utils/multi_ofe.py`, and
`prep_soil` in `wepppy/nodb/core/wepp.py`. Existing tests cover actual worker
propagation, density rejection, stack/stage lineage, freshness, confinement and
installed spawn behavior; this review inspected them but did not run tests.
