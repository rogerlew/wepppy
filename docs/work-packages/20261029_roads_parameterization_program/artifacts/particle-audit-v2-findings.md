# Versioned particle audit repair and complete readback

`audit_particle_closure_v2.py` corrects ELEMENT field parsing without changing
EVENT selection, units, declared width, terminal OFE or Decimal rounding bounds.
The original `audit_particle_closure.py` and all prior model records, declarations,
verifications and acceptance artifacts remain unchanged. No native/production
source or parameter is modified.

## Results

| Declared panel | Cases | EVENT records | Mass flags | Strict fraction flags | Unavailable Sm fields |
| --- | --- | --- | --- | --- | --- |
| Legacy r3 | 116 | 5,887 | 0 | 0 | 0 |
| Legacy r4 | 116 | 5,887 | 0 | 0 | 0 |
| Hydraulic factorial r4 | 928 | 47,993 | 0 | 3 | 16,428 |
| Accepted U12 Roads | 840 | 117,145 | 0 | 1 | 74,267 |
| Accepted U12 downstream | 348 | 18,620 | 0 | 1 | 6,074 |

All 2,348 selected case records were audited; none has invalid structure or
unavailable required particle fields. These panels overlap: the five retained
fraction flags are case-event observations, not five independent new native
failures. Factorial and U12 strict flags exactly match their historical particle
audits. The separate newly observed factorial fraction event remains flagged.
Neither numerical tolerances nor fraction acceptance was relaxed.

Both legacy generations' 91 apparent class/bulk failures disappear after reading
SedLeave at its actual fixed-width boundary. The old parser interpreted QRain
as sediment when adjacent duration/enrichment fields filled their widths.
The complete earlier forensic disposition remains in
`review-legacy-particle-disposition.md`.

The first v2 full run also exposed native `*******` values in unrelated Sm
fields. The canonical Rust reader treats all-star diagnostics as unavailable.
The predeclared `particle-audit-v2-scope.md` distinguishes structural validity,
numeric availability and particle-required values. V2 preserves every such
marker in a separate diagnostic report; it never guesses a number, treats it
as zero or labels it unexplained particle mass loss. All unavailable diagnostics
in this readback are Sm. Complete numeric availability is not claimed.

## Reproduction and immutable evidence

From the WEPPpy repository, run the bounded regression with standard Python:

```bash
python3 docs/work-packages/20261029_roads_parameterization_program/artifacts/check_particle_audit_v2.py --output /tmp/particle-audit-v2-regression.json
```

Twenty declared controls pass: native adjacent-field reconstruction, ordinary
field parity, exact original Decimal bounds, retained strict fraction/mass
failures, malformed/duplicate rejection and explicitly reported unavailable Sm.
The canonical public width table is verified against
`/workdir/wepppyo3/wepp_interchange/src/hill_element.rs`.

For all five panels, choose a new, nonexistent output directory:

```bash
python3 docs/work-packages/20261029_roads_parameterization_program/artifacts/reverify_particle_audit_v2.py --raw-root /workdir/wepppy/out/roads-parameterization-program-20261031 --output-dir /tmp/particle-audit-v2-fresh --workers 4
```

The runner declares the current audit, fixture and panel hashes before executing;
it does not resume or rewrite prior declarations. It freshly verifies PASS and
ELEMENT hashes and preserves record-bound native input hashes; it does not
claim to rerun the model or rehash every unrelated native input. It rechecks
all frozen records/declarations/verifications at completion. Run 3 verified
3,425 files unchanged across its execution. First setup and stopped run 2 remain
retained separately.

`particle-audit-v2-reverification.json` is the compact public receipt, including
all panel outcomes, strict flag details, original/new script hashes, per-panel
full receipt paths/hashes and regression/disclosure provenance. Full records
and input/output provenance reside in
`out/roads-parameterization-program-20261031/particle-audit-v2-readback-run3/`.
Original audit SHA-256 is
`f8c3c21b00d90f507106c6b5c813d646fbf7e7a6fcb978223efb9c4189412302`;
v2 is `5b65979bffa56d11c9d7738504e090cd0f5080989bf136a0f4537131e4b73435`.

After run 3 completed, disclosure review removed an unnecessary literal private
native format descriptor from the public regression fixture, replacing it with
a source-location reference and the canonical public widths. The original
fixture remains byte-exact in private retention. `particle-audit-v2-disclosure.json`
maps its historical hash/path to `private_original`; earlier receipts remain
unchanged. All numeric outputs and expectations are identical. The additive
`particle-audit-v2-regression-public.json` reruns all twenty controls against the
sanitized fixture. Fresh reruns declare its current hash; historical verification
must use the explicit private-original mapping instead of expecting old bytes
at the sanitized public path.

A prospective malformed PASS Decimal token fails closed but raises
`InvalidOperation`, rather than the runner's per-record `ValueError` collection;
such a future malformed panel aborts and cannot pass. None of the declared
records encountered that condition. No broad exception handling was added to
conceal it.

This repair clears the false legacy mass findings on this declared particle
criterion only. Remaining strict fraction findings, magnitude objectives and
parameter/UI promotion retain their existing review boundaries.
