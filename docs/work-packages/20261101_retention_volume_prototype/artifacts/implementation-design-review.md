# Volume prototype implementation design review

Disposition: **reuse the existing storage observer for a bounded initialization and complete-history comparison; execution approval pending concrete declaration, producer, reader and runner.** No new binary is presently indispensable for that scope. Full executed consumer-domain proof is a different requirement and is not provided by this observer.

## Reusable evidence

Independently verified all 978 files against the retained native-probe build receipt. Binary SHA-256 is `5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1`; build-receipt.json SHA-256 is `ab8c57fc6a1786864cc581907e40aaa11673fe15cc925cad44b04786cbe27036`. Reuse that exact binary and complete provenance, not a rebuild with merely similar sources. It is an accepted instrumented research binary, not proof that an arbitrary released binary has identical behavior.

SO_SCON_INPUT observes remapped native input retention, RFG, density and computational depth. PORE observes density, entrapped-air correction, CPM and estimated dry content. ROCK records retention and SM20C immediately after rock correction; DRY records the final combined guard result. UL and WB/WBH_UL establish SCON's limit and subsequent initialization assignment. These endpoints suffice to compare emitted candidate/control inputs against actual native initialized retention and capacity, including source-to-computational-layer depth mapping. They do not equate serialized horizons with computational layers.

The guard chain can be reconstructed from ROCK values with native binary32 rounding at each operation: SM20C ceiling, field-capacity adjustment and associated dry shift/floor, FC/POR ratio guard, then final floors. Compare reconstruction with DRY exactly. Label inferred branch choices as reconstructed, not directly logged. INPUT nonpositive values distinguish estimated-input branches, but intermediate estimated FC and logarithm operands before ROCK are not separately recorded. A construction or native failure before later tags remains an explicit incomplete case.

Existing WB_HK_FCUL/RATIO and WBH_HK_FCUL/RATIO observations can directly check actual initialization FC and UL operands. They require wepp_observe.on and are suppressed by wepp_observe_frost.on. Freeze both controls explicitly and retain the resulting log. storage_observe.on alone does not enable these records. The storage logger uses initialization sequence rather than a fabricated calendar clock; retain sequence, OFE, layer and phase identity, and do not infer a date from unrelated initial diagnostics.

## Concrete coverage limits

The native conductivity guard checks a positive ratio, not the stronger finite strict interval 0<FC/UL<1; ratio one still reaches a zero logarithm. Record domain flags without silently adding a new model guard. Initialization UL-DRFC can be reconstructed using actual final retention, air and thickness with binary32 operations, but it is not a directly observed executed drainage division.

The hourly lateral-flow division uses a local DRFC and branch conditions involving current storage, lower-layer saturation and the bottom-layer case. Existing selected-day BPO states do not identify every executed division or provide complete-history local operand/branch coverage. Frozen changes, later density/retention updates and daily/hourly paths prevent extrapolating initialization safety to every consumer. Tile drainage also uses an air-factor indexing convention distinct from the hourly local expression. Report static initialization margins and complete output effects separately from executed consumer-domain safety.

If full-history domain claims are required, first declare that exact gap; then add only guarded observations at the actual conductivity and drainage consumer sites, retaining valid local operands and branch identities. A source-free declaration, private patch audit, complete dependency/runtime freeze, finite panel and baseline-versus-observer parity gates must precede any such build. Do not rebuild merely to improve convenience.

## Prerequisites for the new runner and reader

Use actual candidate soil files from a separately declared prototype, preserving failed/incompatible rows and original source/prepared/emitted values. Freeze a finite paired inventory and all non-soil runtime inputs. Require zero-rock identity and explicit high-rock, missing/zero and guard-activation coverage where admitted. Do not mask an above-unity inverse with production fallback and then label the resulting file a successful inverse without disclosing that fallback. Any selected successful subset needs an explicit exclusion ledger.

The earlier read_sift_native.py is a provenance/calendar pattern, not a reusable retention validator unchanged: it assumes fixed SIFT mass per profile, ten computational layers per OFE, 1800 mm final depth and SAT=.75. SCON may raise SAT to its dry-water minimum for new retention; preserve actual native behavior instead of requiring .75 unconditionally. Replace hard-coded geometry with the new declared supported profile mapping, while keeping exact expected identities and duplicate rejection. Validate every required storage tag, global monotonic sequence, tag order, finite values and all declared OFEs/layers. The earlier reader does not itself enforce all those framing conditions.

Preserve the later narrow report-decoration correction: original read_sift_native.py falsely rejects legitimate loss-report stars. Accept only documented exact decorative lines; numeric overflow stars remain failures. Retain seven complete output files, exact full 16-year calendars, process return/completion evidence, stdout/stderr, timings, binary/runtime identities and before/after input/build inventories. Preserve per-case failures before aggregate failure and distinguish baseline/candidate output differences from observer parity; changed retention is expected to change some outputs.

No implementation, model run or old-package edit was performed. Execution remains unapproved until the new concrete files and frozen panel are independently reviewed.
