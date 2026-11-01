# Legacy global-record reader correction

Disposition: **APPROVED for read-only supplemental analysis with reader-v5.** This does not authorize another native invocation or modification of the executed reader, runner, freeze or original receipts. Final actual supplemental results remain subject to readback review.

The accepted high-case legacy BPO file contains `BP_IRS_ENTER` at year 7/day 343, OFE zero and index zero. The pinned source explicitly emits this global record in contin.for before calling IRS; OFE zero is intentional for that marker. Reader-v4 incorrectly applied the per-OFE restriction to every legacy record. This is a validation-domain error, not evidence of a native model failure.

The reader-v5 diff adds only the exact exception `tag == BP_IRS_ENTER and OFE == 0 and index == 0`. Year/day and finite-value checks still apply. Every new stage/call record remains restricted to OFEs one through three, and the allowed global record remains in the filtered legacy byte stream. Exact old-BPO parity therefore binds its content and position to the accepted comparator; the exception does not authorize arbitrary new global events.

Independently replayed the valid ordinary/global fixtures and all sixteen retained malformed fixtures. Wrong global index and a new FX tag with OFE zero reject, as do the prior fourteen malformed cases. An additional disposable control with the global record outside the selected dates also rejects. Arithmetic, state flags, support/order checks and all stock/flux equations are unchanged.

SHA-256 bindings:

- read_flux_v5.py: `c0793beae8ec7f3653544fb1d2c1d62fff77b50cfd068379d95e7a56c559480c`.
- check_flux_reader_v6.py: `48b2bf405da5db4ff369e7e7a018f5c26a98e7173eb7bb64d50b12a6b32f815e`.
- Retained control receipt: `65a5545384309157eb6cb7477d076a28064e698f9c5245c9efec4a9970bcc2e2`.

Preserve the original high-case failed validation receipt and re-read all three completed diagnostic logs into a fresh supplemental root. Bind original process/readback/log identities and supplemental sources before/after, retain ordinary-output/FH-trace/legacy-BPO parity, and do not relabel the executed reader as having accepted high. No model rerun is needed. Reviewer writers are clear after scoped documentation lint.
