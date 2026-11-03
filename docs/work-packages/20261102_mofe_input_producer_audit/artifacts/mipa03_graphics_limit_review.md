# MIPA-03 inherited graphics field limit review

Reviewer: `mipa03_contract_correctness`, 2026-11-03 UTC.
Disposition: **confirmed inherited serialization limitation; preserve format**.
This is not final release approval. The all-file application audit and remaining
gates retain their independent evidence requirements.

## Source and direct formatter evidence

The complete `src/bigout.for` and `src/bighdr.for` are identical after CRLF
normalization across bound reference `2e5928702edd5526a119216bd6be5997729ec72e`,
selected revision-6 boundary `4f0728984`, and current selected source. Normalized
SHA-256 identities are:

- BIGOUT: `82e0a9d85ca31c63b759020e416ed1039f85448d7a66ad9cdefc2a2b6d0e041a`.
- BIGHDR: `4c181f017aee91593b4f7b20000fde33751271b9a42872e1402401731113763b`.

BIGOUT line 201 assigns `treal(83)=daydis(iplane)`; line 254 uses format 1000,
`i6,83(1x,f10.5),7(1x,i2),13(1x,f10.5)`. BIGHDR names this value “Days since
last disturbance.” It is REAL-array element 83, zero-based whitespace field 83,
and **physical whitespace field 84** because the elapsed-day integer precedes it.

A privately compiled probe uses the actual extracted format line and verifies
its source values are finite. It prints 9999 as `9999.00000`, and both 10000 and
13000 as `**********`, with 104 fields in every row. Evidence is retained at
`/tmp/mipa03-grph-format-_tcjwo7i/`. This demonstrates width overflow rather
than proving or implying NaN/Inf in model state.

## Configured artifact spot-check

The prepared application contains 72 graphics files totaling 3,257,191,456 bytes.
The additional graphics output explains 576 files (eight per hill), compared
with the earlier seven-output inventory. Counts alone do not validate contents.

Independently read `H1.grph.dat` from the supported acceptance fork at
`/wc1/runs/mi/mipa-rap-20261103/wepp/output/`. Its SHA-256 matches the execution
receipt: `6ab806099cd3aeb44c7067e6befe85dfda5094708394b5fc356aadc56a1a8060`.
All rows have 104 fields. There are 25,568 daily records and two min/max summary
records. The only star field is physical field 84: 6,230 daily instances and
one maximum-summary instance. Every other numeric field in this file is finite.
The first star appears at file line 19,460, elapsed simulation day 9670; the
preceding record prints daydis 9999. An initial disturbance age can make the
field overflow before 10,000 simulated days, so disclosure must refer to the
daydis value, not solely simulation duration.

This spot-check does not replace the parent's all-72 graphics and water audit.
Repository searches found no production `.grph` reader in WEPPpy/WEPP runner;
the identified test checks file existence. That does not rule out external
graphics consumers or make the lost diagnostic values usable.

## Acceptance and disclosure

The handoff explicitly requires preserving output formats and permits naming
genuine remaining limitations at completion. The affected field and formatter
predate this work. Its loss is not a specialized soil/RAP consumer regression,
and it does not itself invalidate finite water artifacts, installed interchange,
or HillslopeWatbalReport readback. Those claims still require their own evidence.

If the all-file audit confines stars to this known field and confirms relevant
model/consumer outputs, the bounded specialized consumer delivery may complete
with this residual recorded. Do not claim all 576 outputs are fully numeric or
that the graphics diagnostic is repaired. Do not silently exclude graphics from
the artifact inventory, normalize stars into numbers, clamp state, disable the
saved graphics option, or change F10.5 within this preservation task.

Suggested disclosure: “Canonical preparation produced eight outputs per hill,
including graphics. The inherited graphics format cannot represent the ‘Days
since last disturbance’ value at 10,000 days or above and prints asterisks in
that field. This diagnostic limitation is unchanged; finite water outputs and
the installed interchange/report path were validated separately.” Replace or
augment counts with the completed all-file audit before publication.
