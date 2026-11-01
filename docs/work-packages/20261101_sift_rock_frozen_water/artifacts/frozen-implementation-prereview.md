# Frozen campaign implementation prereview

Disposition: **PASS before invocation**, limited to the declared 29 full unchanged FRWATC mapping fixtures. No compiler, native executable or campaign was invoked by this reviewer. This does not approve a capacity correction, frost-energy simulation or full hydrologic run.

Reviewed SHA-256 identities:

- `frozen-declaration.md`: `daf15df4f4287d022e010accd1119bccf6c75150b681312083407591f830f956`
- `frozen-cases.json`: `4addc896853fb75b5ef6f2ecd835cf880672e6770c2f344c94969e7581f0d580`
- `frozen_driver.for`: `63af4a402c6e351387da45d4ca6a6ba67655a6ee20aedb6dbab14516a1ded34e`
- `frozen-design-source-bindings.json`: `ea30c0e7c45d6e8f069501d2f09ada74547e061cd75b7a8ca44364bb9f0fae91`
- `run_frozen_campaign.py`: `fb1d05ebd14b0524204fe0da8bc53c6c7feef4534e3eb770185b690fcd0b25e3`

All 13 native source/include hashes and byte counts match the declared source root. The include closure is complete. The authored driver and unchanged routine use identical native COMMON declarations and dimensions; the routine has no external calls requiring substitution. All consumed external state is explicitly initialized, including active geometry, dry reference, liquid/adjusted ice, prior ST, frozen-zone liquid and fine-grid arrays. Unused consumed-array slots receive sentinels; the final driver checks the complete inactive support of those arrays. The `-finit-real=snan` flag is supplementary and is not relied upon to initialize COMMON state.

The 29 case IDs are unique. Input dimensions, positive thickness, frozen support bounds, nonnegative physical stocks and nominal initial capacity are coherent. The driver constructs coarse state from fine state independently of FRWATC before any call, then records the actual REAL ST increment separately from its requested decimal. Unsupported full-frost liquid fractions contribute zero physical liquid. Nominal pore fraction constructs UL only; the routine does not consume POR or CPM. Single coarse-layer support deliberately leaves cross-layer shortage behavior outside scope.

STATE emits exactly ten real values after its stage/count; FINE emits four after stage/index. Precision is sufficient to round-trip native REAL. Parsing enforces finite operands and derived stocks, ordered unique fine indices, unique stages, required stage sets and sentinel preservation. Physical stock diagnostics use double summation of emitted operands, with separate liquid, ice, coarse/fine, SOILW and geometry residuals. The 1 mm classification uses the native float32 threshold and emitted native-computed support. Direction1 SOILW can be stale; it is reported without imposing a false intermediate equality.

Normal closure and coordinate-pair gates match the declaration. Threshold fixtures retain their signed discrepancies and are not labeled conservation passes. Actual delta, mapping residuals and final-minus-requested stock remain distinct. No residual is reassigned to runoff, ET or a fabricated flux.

Compilation is pinned to `/usr/bin/gfortran`, the declared PATH prefix and flags. Source copies, the exact authored driver, separate objects, executable, compiler output, commands, per-case stdin and process evidence are retained privately. Source hashes are checked before copying and again after the campaign. Fresh output is mandatory; native source is not modified or published by the runner.

The initial implementation could abort on a successful-process parsing failure or a missing coordinate-pair result. That finding is closed: timeout, process and validation failures are retained per case, the remaining fixtures continue, failed pair dependencies receive explicit failures, and the final receipt precedes campaign failure exit. Compile/link failures retain their process evidence and stop because no valid executable exists.

Python AST parsing and parser-only controls passed: one valid synthetic snapshot plus rejection of duplicate STATE, duplicate FINE, NaN input, changed sentinel and overflowing derived stock. These checks did not invoke the native campaign. No unresolved blocking findings remain; actual retained results still require independent post-execution review.
