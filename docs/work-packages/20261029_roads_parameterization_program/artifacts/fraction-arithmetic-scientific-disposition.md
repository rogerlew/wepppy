# Residual fraction flags: independent numerical disposition

**Disposition:** the two retained U11/U12 flags are explained by observed binary32
arithmetic, with exact replay and operation-derived bounds. Neither demonstrates
an unresolved sediment-source or accounting defect. Preserve both failed strict
printing predicates in the audit; this certificate is a separate scientific
explanation, not a tolerance change or an assertion that the audit is all green.
Release promotion remains conditional on every other frozen gate and independent
review. This review does not authorize promotion.

No native behavior, particle fractions, audit tolerance, or parameterization was
changed for this investigation. Fraction renormalization is not recommended.

## Findings

| Retained event | Actual REAL fraction excess | Implied excess mass | Existing class/bulk mass print bound |
| --- | ---: | ---: | ---: |
| Denver / 1718465 / outunrut / gravel / none / buffer_cap, year 8 day 228 | 4.9099326134e-6 | 8.4697038831e-5 kg | 0.0221085761906 kg |
| Site / 2711250 / outunrut / paved / low / erosion_road_cap, 2003 day 29 | 2.7270575177e-8 | 8.5216569158e-15 kg | 0.0215526147083 kg |

Widths were read independently from both original `record.json` files:
43.105229381131934 m in each case. Mass above means
`SLOSS avsole × width × (sum(native fractions) − 1)`, not the difference between
separately rounded PASS and ELEMENT numbers. Both existing class/bulk mass checks
pass without any additional allowance.

Denver's printed fractions sum to 1.000017; their printing-only bound is 0.000016.
OFE 2 and OFE 3 each execute 101 ordinary RUNGE steps with zero rill source:
100 publication-grid steps and a tiny boundary remainder. Their observed widths
sum exactly to one. Repeated REAL load additions fall below the exact
constant-source solution by 3.5390257835e-8 and 3.1804665923e-7, respectively.
ENRICH reconstructs rill load from the bulk residual and clamps these small
negative residuals to zero. Its positive interrill terms consequently produce a
fraction sum slightly above one. The upstream fraction excess is carried into the
next OFE. All 202 load updates and all observed ENRICH output fractions replay
bit-for-bit from the traced native inputs. This is REAL accumulation followed by
the existing mix arithmetic and final formatting, not printing alone.

The site's printed sum is 1.000005010000286038; its printing-only bound is
0.0000050050000000015. Five positive class loads have exact sum
0.010488080132179946; their sequential REAL sum is 0.010488079860806465.
Dividing each class by this native sum reproduces every output fraction exactly.
The final source-free `fraction × load / load` mix leaves these fractions
unchanged. This is ordinary finite-precision normalization and formatting.

## Bounds and their scope

Let `u = 2^-24` and `gamma(n) = n*u/(1-n*u)`. All observed arithmetic is finite,
positive where required, and within the normal binary32 range. The executable
certificate uses exact rational arithmetic on recovered binary32 inputs for
error-versus-bound comparisons.

For each zero-rill RUNGE step, the four stage increments are the same rounded
`theta*dx`. Factors of two are exact; the product, three positive sums, and
division give an increment bound of `gamma(5)*abs(theta*dx)`. Add half an ULP of
the stored new load for the final addition. The existing Euler lower bound has a
smaller bound, so selection of the larger load preserves this bound. Summing
these per-step bounds gives 1.8872946679e-7 for OFE 2 and 3.7795105826e-7 for
OFE 3; both actual deficits lie within the bounds. The certificate checks each
step, consecutive load continuity, constant theta, zero rill coefficient, and
the complete unit interval.

Each positive ENRICH weighted sum/division is bounded conservatively by
`gamma(6)` times its exact weighted result. The certificate includes the actual
incoming, soil, and interrill fraction sums, the observed load deficit, and the
clamped rill contribution; it does not assume the input fraction sums are exactly
one. Every output matches the native expression and satisfies this bound.

For the site's five-term positive normalization, sequential summation has bound
`gamma(4)` and each division has relative bound `u`. Therefore the fraction-sum
error is bounded by `(gamma(4)+u)/(1-gamma(4)) = 2.9802335177e-7`.
The observed 2.7270575177e-8 excess satisfies this source-derived bound. No bound
was selected by fitting the observed residual or by changing the frozen audit.

These are certificates for the retained source states and outputs, not a
universal error budget for every EROD or ENRICH call. In particular they do not
excuse nonzero-rill integration failures, missing interval support, mass defects
larger than demonstrated arithmetic error, or future unmatched flags.

## Exact-candidate applicability and provenance

The U11 observers reproduce all ordinary outputs for both full 16-year cases.
Their original receipts, source hashes, binaries, raw traces, source records,
and original temporary scripts are retained at:

`out/roads-parameterization-program-20261031/fraction-arithmetic-observe-u11/`

`retention-manifest.json` hashes the retained original evidence and the frozen
base object/source inventory. The arithmetic and class-normalization observers
are separate retained runs; `reproduction-replay/` verifies the explicit-path
replay script against the retained binary. Exact original flag rows and PASS/
ELEMENT hashes are in `frozen-audit-flags.json`.

For U12 binary
`2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`:

- Denver has identical inputs and all ordinary output hashes across the full
  simulation. Its strict flag is unchanged.
- Site has an identical whole PASS file, but other outputs change on other days.
  The retained observer was rebuilt with frozen U12 PARAM and run for all 16
  years. It matches every U12 ordinary output hash, and every target-day PM
  observation, including class loads, class sum, mix, and SLOSS, matches U11.
  Its strict flag is unchanged. Whole-case U11-to-U12 parity is not claimed.

Machine-readable evidence:

- [Arithmetic certificate](fraction-arithmetic-u11-certificate.json)
- [Exact U12 applicability](fraction-arithmetic-u12-applicability.json)
- [Certificate checker](certify_fraction_arithmetic_u11.py)
- [Observation builder](observe_fraction_arithmetic_u11.py)
- [Full-period replay](replay_fraction_arithmetic_u11.py)
- [Candidate applicability checker](check_fraction_certificate_applicability.py)

## Reproduction and recommendation

From the repository root, regenerate the certificate using explicit paths:

```bash
python docs/work-packages/20261029_roads_parameterization_program/artifacts/certify_fraction_arithmetic_u11.py \
  --root out/roads-parameterization-program-20261031/fraction-arithmetic-observe-u11 \
  --output /tmp/fraction-certificate.json
```

The observation builder requires `--base-src`, `--candidate-root`, and a fresh
`--output-root`. Add `--classes --case site_fraction` for the normalization probe.
For the exact U12 applicability run, supply frozen U11 observer base
`particle-capacity-observe-u11/build/src`, U12 candidate
`param-sign-u12-combined`, and `--param-source` pointing to that candidate's
`build/src/param.for`. All these directories are under the program output root.
The builder adds observations only, preserves the build flags and portable math
wrappers, and requires full-period ordinary-output parity before success.

Retain the strict flags alongside this numerical explanation. They no longer
represent unexplained accounting failures for the specifically verified U12
binary. A constant-source EROD integration anchored across grids could reduce
Denver's accumulation error, but these measurements do not require it as a
physical correction. If pursued, predeclare a separate precision ablation with
shared transition/root and full-matrix gates; do not bundle it with the PARAM
repair or change ENRICH to hide the producer residual. A later binary requires
an applicability check or a fresh exact-parity observation before reusing this
certificate.
