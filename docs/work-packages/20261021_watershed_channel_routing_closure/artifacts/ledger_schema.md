# Ledger and diagnostic acceptance design

Each record identifies case, binary SHA-256, input manifest, year/day, element,
boundary, interval, source artifact and observation phase. Volume columns are m3:
`inflow`, `baseflow`, `outflow`, `loss`, `storage_start`, `storage_end`,
`residual`. Unknown values use empty CSV fields with an explicit unresolved
disposition; they must not be coerced to zero.

Residual is inflow + baseflow - outflow - loss - (storage_end - storage_start).
Report signed total, total absolute residual, maximum absolute residual, worst
element/day and cumulative drift. Relative residual divides by the maximum of
absolute inflow plus baseflow, absolute outflow plus loss, and absolute storage
change; zero denominator with zero residual is zero, otherwise undefined.

Before grading native channel snapshots, use a conservative floating-point
screen of 16 single-precision epsilons times the sum of absolute terms, plus
the diagnostic decimal quantization bound. This is an arithmetic screening
tolerance, not a hydrologic acceptance threshold. Stored integer PASS values
have their declared scale and half-unit rounding bounds; never infer that scale
from display precision. Rounded WAT readback uses half the last printed unit
per term and per record, propagated through area multiplication. Accumulation
uses the sum of bounds, never cancellation of positive and negative errors.

No tolerance can validate missing records, duplicate transfers, nonfinite values,
unknown initial storage, or an incomplete configured period. These remain
unresolved regardless of residual size. Hydrograph integration needs actual
intervals and its own integration error budget before grading.

Offline controls must yield zero for an exact hand-computable balance, positive
residual for duplicated inflow or dropped outflow, the explicitly calculated
delta for a wrong area, and twice the original storage increase when its sign
is reversed. These controls never alter simulator inputs or state.
