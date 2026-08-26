# SBS-A11Y-02 Revision 3 Independent Review

**Reviewer**: Codex  
**Date**: 2026-08-24  
**Lens**: Independent adversarial contract, producer, compatibility,
accessibility-evidence, governance, operations, and security review  
**Verdict**: REJECTED

## Findings

1. **High — Producer totality is defined over the color table, not over the
   raster value domain.**

   **Location**:
   `artifacts/2026-08-24_contract_decision.md:81-87`;
   `ADR-0045-sbs-class-coded-display-transport.md:54-58`;
   `prompts/active/sbs_class_transport_execplan.md:126-135`;
   DOM-23 field matrix, `BAER display raster encoding`; package success
   criteria, `package.md:100-104`.

   **What is wrong**: `get_sbs_color_table()` enumerates only
   `range(raster_ct.GetCount())`, but `self.counts` is independently derived from
   band values. A malformed or unusual paletted raster can therefore contain a
   value outside `0..GetCount()-1`. Writing one line for every palette index does
   not write a line for that observed value. `export_wgs_map()` preserves source
   values with nearest-neighbor resampling and also introduces destination
   NoData `255`. The `nv` line correctly handles band NoData `255`, but it does
   not handle an arbitrary observed non-NoData value outside the table count.
   With `-exact_color_entry`, that value becomes transparent RGBA
   `0,0,0,0`. The client then treats it as masked, directly contradicting the
   operator decision and clauses 5-6 that every non-NoData unknown is visible
   unassigned. The proposed opaque-RGB-subset assertion would pass while losing
   the pixel to transparency, so it does not prove the required invariant.

   The `ct is None` breaks path is otherwise total over observed `self.counts`.
   Its exact-mode behavior should remain unchanged because nearest-neighbor warp
   creates no new non-NoData values and `nv` covers destination NoData. The
   `Baer.write_color_table()` path is likewise total over the WGS raster's
   `self.classes`; adding exact mode should not change already-correct cases.

   **Fix**: Define producer totality over the union of source color-table
   indices and observed non-NoData raster values, with explicit precedence:
   source NoData -> transparent, recognized index -> class encoding, every
   other observed/index value -> sentinel. Add a generated-output assertion
   that every source-valid pixel remains opaque and becomes either a severity
   encoding or the sentinel, plus a fixture whose observed value exceeds the
   color-table count. Keep a separate assertion for destination NoData.

2. **High — Revision 3 still falsely says every historical artifact decodes
   correctly.**

   **Location**: contract decision `:156-159`, `:180-181`, `:193-204`;
   ADR-0045 `:34-39`, `:82-87`, `:102-105`, `:145-159`, `:191-193`;
   ExecPlan `:10-14`, `:42-45`, `:53-54`, `:86-93`, `:159-161`; package
   `:33-34`, `:63-64`, `:107-108`; child-package register SBS-A11Y-02 row.

   **What is wrong**: Git history disproves the equivalence between all legacy
   off-domain RGB and unassigned classification. In
   `126673850^:wepppy/nodb/mods/baer/baer.py:182-216`, the pre-2018 BAER writer
   emitted only four break entries while `class_map` classified every observed
   numeric value. For a 256-valued raster, values between breaks were valid
   classified numeric values, but default `gdaldem color-relief` rendered them
   as interpolated off-domain RGB. Revision 3 maps all such RGB to Unassigned.
   That is a conservative degradation which the operator may choose, but it is
   not “their true state,” “semantically correct,” or correct canonical class
   rendering. Generation-0 tests containing only the four endpoint colors
   cannot establish historical-run correctness.

   This also makes the no-regeneration position only partly coherent: current
   and generation-A/B assigned artifacts decode to class; newly validated
   color-table artifacts can become closed after finding 1 is fixed; but
   pre-2018 interpolated artifacts lose their historical severity display and
   are relabeled Unassigned until revalidation.

   **Fix**: State this compatibility loss explicitly and obtain operator
   approval for it, or define a distinct `legacy-undecodable` state instead of
   asserting it was unassigned. Remove claims that every historical run renders
   correctly. Add a real generation-0 fixture with values between the old
   breaks and test the ratified outcome. If exact historical severity recovery
   is required, the package needs artifact-specific classification metadata or
   regeneration; exact matching against twelve endpoints cannot recover it.

3. **Medium — The sentinel figures are reproducible from the scripts, but the
   CVD compositing model applies operations in the wrong order.**

   **Location**:
   `artifacts/2026-08-24_palette_baseline.py:14-20,29-34`;
   `artifacts/2026-08-24_sentinel_search.py:19-30`;
   `artifacts/2026-08-24_unassigned_sentinel_analysis.md:59-100`; contract
   decision `:226-229`; ExecPlan `:64-65,81-85`; tracker `:203-224`.

   **What is wrong**: Both scripts CVD-simulate the foreground and ground
   separately and then composite the simulated sRGB values. A user sees the
   browser-composited pixel, so the composited display RGB should be passed
   through the CVD simulation. The operations are not interchangeable here
   because `simulate()` performs transfer functions, clipping, and 8-bit
   rounding. Reversing the order to composite first and then simulate changes
   the alpha-0.3 baselines from the documented `5.04` standard / `3.48` shifted
   to approximately `5.32` / `2.83`, and changes `#7F00FF`'s worst separation
   from `10.39` to approximately `8.64`. The sentinel still exceeds the
   corrected intra-palette baseline, so this finding does not by itself overturn
   the color choice, but the claimed evidence and referred opacity metrics are
   inaccurate.

   The Machado severity-1.0 matrices, sRGB transfer functions, D65 Lab
   conversion, and CIEDE2000 implementation otherwise match their standard
   forms. The scripts also depend on being launched from their artifact
   directory; running them from the repository root fails to find
   `2026-08-24_cvd_lib.py`.

   **Fix**: Composite source RGB over the actual ground in the browser's blend
   space first, then CVD-simulate the resulting display RGB. Update the analysis,
   ADR/package figures, and referred DOM-04B finding. Resolve support-file paths
   relative to `__file__` so the recorded reproduction commands work from the
   repository root.

4. **High — The required cross-owner authority and checkpoint are not yet
   established, while the contract decision overstates registration.**

   **Location**: contract decision `:12-17`; child-package register preamble
   `:125-155` and SBS-A11Y-02 row; tracker `:21-25`; ExecPlan `:30-31,119-124`;
   contract-first standard, Required Pre-Implementation Checkpoint requirements
   1-6 and Bounded Cross-Owner Remediation requirements 1-6.

   **What is wrong**: The SBS-A11Y-02 row exists, but no separately closable
   GOV-00A remediation milestone authorizes it in the register preamble. The
   tracker correctly lists that milestone as open. The exact revision-3 delta
   also still awaits explicit operator approval, two revision-3 independent
   reviews and disposition, and a standalone ancestor commit whose revision is
   recorded. Revision-1 reviews and the revision-2 review cannot satisfy review
   of the materially different server-plus-client revision 3. Thus checkpoint
   requirements 1, 2, and 4 are substantially present; 3, 5, and 6 remain open,
   as does the bounded-remediation registration prerequisite. Calling
   SBS-A11Y-02 a registered bounded remediation in the contract decision is
   premature.

   **Fix**: After resolving findings 1-3, add and independently ratify the
   required GOV-00A milestone, record explicit operator approval of the exact
   revision-3 matrix, obtain the required two revision-3 reviews and disposition
   (including post-fix confirmation where required), then commit the complete
   checkpoint as a standalone ancestor and record its hash before implementation.

5. **Medium — The tracker remains internally revision-2 and contradicts every
   revision-3 authority.**

   **Location**: tracker `:10-15`, `:21`, `:39-40`, `:50-55`, `:72-78`,
   `:229-246`, `:257-261`, `:282-303`.

   **What is wrong**: The quick status says the actual delta is client-only;
   backlog asks for approval of the revision-2 delta; the live critical producer
   risk is still “unresolved” and the new producer fix is still merely
   “referred”; unknown opaque pixels are still specified as transparent; the
   verification list omits generation 0 and requires off-domain transparency;
   and progress repeats the disproved two-generation enumeration. These are not
   harmless history entries: several sit in current status, risk, and
   verification sections and conflict with the ADR, contract decision, package,
   matrices, UI contracts, and register.

   **Fix**: Rewrite the current-status, backlog, risk, and verification sections
   for revision 3. Preserve superseded history only when visibly labeled as
   disproved/superseded. Track the legacy generation-0 limitation from finding 2
   and the observed-value totality gap from finding 1 as open blockers.

## Verification Performed

- Read the complete revision-3 contract decision, ADR-0045, sentinel analysis,
  revision-2 disposition, ExecPlan, package, tracker, both amended field-matrix
  rows, both amended UI-contract sections, the child-register row and its
  governance preamble, and the contract-first checkpoint standard.
- Read current `get_sbs_color_table`, constructor NoData/class discovery,
  `_write_color_table`, `export_wgs_map`, `export_rgb_map`,
  `Baer.write_color_table`, and both `gdaldem` invocations.
- Exercised installed GDAL in `/vsimem` with values `0,1,2,255`, exact and
  interpolated modes, and `nv 1 2 3 4`. Exact mode produced respectively
  `[255,0,0,255]`, `[0,0,0,0]`, `[0,0,255,255]`, and `[1,2,3,4]`. This proves
  that `nv` is honored in exact mode and a missing non-NoData entry becomes
  transparent, not opaque black.
- Verified generation 0 with `git show 126673850^`, generation A with
  `git show 126673850`, and generation B with `git show 531d06d35b74c44f11c0f9c49d336b31be03682e`.
  The twelve RGB triples in revision 3 match those sources. All twelve are
  mutually distinct; none collides across generations or with sentinel
  `127,0,255`.
- Searched `sbs_color_map.json`, `_DEFAULT_COLOR_TO_SEVERITY`, BAER/Disturbed
  source, and client source for `127,0,255`/`#7F00FF`. The sentinel is absent
  from ingestion recognition and does not collide with a severity color.
  Display PNG generation is downstream of classification; `sbs_4class.tif`,
  coverage, landuse, and soils read classified/source data rather than the
  display PNG. If a display raster were manually re-ingested, the sentinel would
  remain unrecognized/unassigned rather than feed back as a severity.
- Re-ran `2026-08-24_palette_baseline.py` and
  `2026-08-24_sentinel_search.py` from the artifact directory. The documented
  `5.04`, `3.48`, and `10.39` values reproduce exactly under the scripts' model.
  Independently reran the same matrices and CIEDE2000 code with display
  compositing before CVD simulation, producing the corrected figures in finding
  3. No test suite or build was run.
- Rechecked revision-2 findings 3-7. Revision 3 now handles provenance, proposes
  generated-output rather than constant-scraping evidence, admits server source
  and runtime-output changes, specifies count/reset/legend/parity interfaces,
  and narrows the revision-1 obviation claims in its primary contract. Findings
  2 and 5 above identify the remaining historical-parity and cross-document
  overstatement defects.

**VERDICT: REJECTED — producer totality still permits unknown valid pixels to
become masked, historical interpolated classifications are incorrectly called
unassigned/correctly decoded, and the required cross-owner checkpoint authority
is not yet complete.**
