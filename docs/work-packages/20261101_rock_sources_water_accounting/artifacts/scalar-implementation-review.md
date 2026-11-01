# Scalar implementation review

Disposition: **PASS for the declared 17 standalone fragment observations only**, before invocation. This review did not compile or execute a probe. It does not approve a native behavioral change, full-model trial or promotion.

Reviewed identities (SHA-256):

- `run_scalar_probes.py`: `591c6ed528bd9ebdc87edef6aa419f030bb64fb06af5ddb83896e9e1b18a4065`
- `scalar-declaration.md`: `f9c128e0ffd5781abd3a3db8411f5c8d75f0351962baddeb23a9d87d628f3ca2`
- `scalar-source-declaration.json`: `ce6af1ca0b956867575dc1ea4233b780b71c977f464106ee362c030907002406`

Independently read the declared slices and adjacent context under `/workdir/wepp-forest-release-20261009/src`; all three complete source hashes match the JSON declaration. SCON510–518, daily500–520/794–821, hourly623–643/899–931, hourly652 and768–769 contain complete selected statements or branches. The generator rejects undeclared ranges and checks source identities before and after execution. Selected native text is incorporated without rewriting statements. Public Python contains fixture setup, references and slice coordinates; copied native files and wrappers belong only in the private output directory.

All consumed variables have explicit types, bounded array dimensions and initialized operands. The hourly surface branch includes initialized `ui_scrunf`, `norun` and `ii`. Nine initialization fixtures use exactly representable binary fractions; their expected saturation, liquid stock and UL therefore require no hidden precision approximation. Six overflow references round each native arithmetic operation to float32, retain signed stock-plus-surface-flux residuals, distinguish the daily/hourly threshold and do not count FIN as water added by these fragments. Frozen water stays fixed; these checks do not exercise freeze/thaw dynamics or intervening full-routine processes.

The drainage fixtures evaluate the actual DRFC expression and ratio with a positive-denominator native control and a separately labeled synthetic zero denominator. Adjacent native context admits the equality case: the enclosing condition accepts ST>=DRFC, and the bottom layer sets the other branch condition. The wrapper does not execute that enclosing loop. The exact zero numerator/denominator and enabled invalid trap support interpretation of the expected SIGFPE; this remains a synthetic arithmetic-domain counterexample, not evidence of a historical full-model failure.

The compiler is explicitly `/usr/bin/gfortran`, PATH begins `/usr/bin:/bin`, and flags match the declaration: `-O0 -fcheck=all -ffpe-trap=invalid,zero,overflow -ffixed-line-length-none`. Fresh output is required, core dumps are disabled, compiler identity and commands are retained, and native source is not modified. The final receipt binds both declarations, runner, resolved source location, compiler identity, PATH and FC. Results must still be reviewed after execution; this preflight does not assert observed numerical success.

Two findings were closed before approval: comparisons now explicitly reject nonfinite actual/reference/residual values, and compile/execution results are persisted before numerical validation or failure. The narrow timeout handler retains partial output and a timeout receipt before re-raising. Expected SIGFPE evidence is preserved and distinguished from successful finite cases. Python AST parsing passed without invoking the runner.

No unresolved blocking findings. Preserve earlier frozen packets and review actual retained results before publishing conclusions.
