# Corrected flux-observer execution prereview

Disposition: **APPROVED for corrected freeze `b64ef3722da2e5909858a4c48e3bce895564739940fb56b3ec910ff7b542478e`.** Approval covers the fresh campaign-v2 private build and the same three declared complete histories. No build or model invocation was performed by this reviewer.

The first approved build failed at link time because the inserted hourly caller record referenced ET, which is a local array in EVAP/EVAPPM and is not declared in WATBAL_HOURLY. Fortran treated the caller expression as an external function `et_`. The earlier source review missed that scope error. Actual build stdout/stderr hashes match the retained failed build receipt, SHA-256 `9f8262a872bdb7e05388d9daf15db3e8c46552d073b3011dd8221d873a64217e`; return code is two and no history process was invoked. The executed freeze/approval, prepared-v2, first build and original contract/declaration snapshots remain retained. Both document snapshots match their executed-v1 hashes.

Prepared-v3 replaces only the invalid caller ET observation with an explicitly reserved zero slot. Internal REQUEST/RETURN records still observe the actual ET-local array. Reader-v4 compares the four shared return fields EP/ES/ERES/RESINT and requires caller slot five to equal zero; it does not invent a caller-owned ET value. A disposable pure-reader check confirms nonzero internal ET remains valid while nonzero reserved caller data rejects. No native mathematical assignment or control flow changes.

Independently audited every identifier used in all 83 inserted logging lines against actual declarations and recursively included native declarations. Every remaining operand is explicitly declared. Hourly EP/ES/ERES/RESINT/PLAINT/PINTLV/ST come from cwater; DDRAIN/DRAINQ/IDRAIN/UNSDEP from ccdrain; IPLANE/IFLGET from cstruc; RTD from ccrpout; II/WATBL/TILEDRAINAGE are existing hourly locals. ET and XX occur only inside their declaring ET routines. No implicit external-function operand remains. All original lines are preserved, insertions fit column 72, and the previously reviewed initialized-read guards remain intact.

Independently verified all 1,080 current freeze bindings, including the complete base build, three prepared sources, runtime/tools, exact inputs/comparators and updated reader/runner. The corrected runner uses campaign-v2 and prepared-v3; existing process retention, canonical runtime matching, seven-output/full-FH-trace/filtered-old-BPO parity and stop-on-failure behavior remain unchanged. Replayed the valid 144-hour/six-day-group fixture and all fourteen malformed fixtures with reader-v4: all expected outcomes hold. Physical residuals and flags remain separate from observer acceptance.

Final SHA-256 bindings:

- Prepared hourly source: `b9405810a972dfbaefdd2996aec0c02612fd99dcd9a70e516edaf9dba62ad611`.
- run_flux_v2.py: `83994e666a15dcf9edfc7f6a66a3faa77417e8f57e5ba706da8024ecb1eed60e`.
- read_flux_v4.py: `475ea461e1767f6cdc79a6cbdf9bcb440b9ca6d34d7ab8dffa8815a4ca911fa1`.
- check_flux_reader_v5.py: `9ccf2bb029dfc2fa165dfeb080a561cbf15a389365145e858d9759b6d62dc3f9`.
- Retained v5 control receipt: `da2513d3a4bab73433cbba6fb50d4a5f693ca4644e31e9ea9cca04c85d81b439`.

No implementation blocker remains for this corrected exact freeze. Actual build/runtime and three-history outcomes still require post-execution review. Earlier prereview artifacts are preserved rather than rewritten. Reviewer writers are clear after scoped documentation lint.
