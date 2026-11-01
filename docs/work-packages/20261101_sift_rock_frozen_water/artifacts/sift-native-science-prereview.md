# Independent scientific prereview: SIFT native readback

Disposition: approved for the declared three fresh complete native histories,
subject to independent implementation acceptance of the runner. This is emitted-
input/native-consumer validation, not validation of retention physics, deployed
BC data or improved sediment predictions.

Read the declaration, complete read_sift_native.py and actual producer receipt.
Verified both retained JSON and emitted soil hashes for each fixture and
independently recomputed the volume/density inverse and one-decimal mass values.
The zero/20/80volume-percent matrix emits0/33.8/89.1mass percent. Expected native
85mass-percent capping in the high case is correctly distinct from the emitted
value. Actual native density, rather than source1.3g/cm3, must govern the CPM
reconstruction; the reader uses the observed native value and float32 order.
The zero control and high-cap case are meaningful propagation controls.

The explicit SAT0.75 convention is separately tested through initialized ST,
dry reference, POR, CPM and DG; it is not assumed from a successful parser.
The2e-6 reconstructed saturation bound and1e-6mass-fraction bound are readback
precision checks rather than empirical fit tolerances. Existing dry-floor
adjustment can in general alter SAT; any fixture failure must be retained and
explained, not overridden to force agreement. No such change is authorized.

Three OFEs and all16years, initialized layer inventory, seven ordinary outputs,
finite/overflow checks, complete daily keys and the existing1.8m native depth
cap are appropriate bounded acceptance. Contextual original climate/management
must remain identified; repeating a generated OFE soil block is a declared
fixture construction, not a reconstruction of a BC field profile. No exact
inverse-volume recovery is required after formatting, cap or density evolution.
No whole-model water closure follows from output finiteness or complete keys.

## Reviewed bindings

- `sift-native-declaration.md` SHA256 `9facfba161d6d9876d54d2b5f655a8e190503b0563384481ee3f3173cb01e08d`.
- `read_sift_native.py` SHA256 `12dcf8a5b31e51ea02ad857b7ca23cf57cc2111e0827bd29a3608f49c343295a`.
- Actual producer receipt `out/sift-rock-frozen-water-20261101/sift-artifacts-v1/receipt.json` SHA256 `959205335ff495408141f38bd6ba800064d589643f03482e24df65ee8224892e`.

## Final runner guard and provenance amendment

Reviewed and accepted the added positive finite SAT denominator guard, exact
three-fixture inventory, JSON/soil preservation and producer-source bindings.
These strengthen the declared readback without changing its physical hypotheses,
input matrix or acceptance tolerances. Scientific invocation approval extends
to this amended runner, subject to implementation acceptance.

- `read_sift_native.py` SHA256 `bf0e15c6a1c04b01d91bfd677e89a8464fefd55cd509bd84464af52a2280de83`.
- `sift-native-declaration.md` SHA256 `9facfba161d6d9876d54d2b5f655a8e190503b0563384481ee3f3173cb01e08d`.

## Read-only report-token correction prereview

Approved read_sift_outputs_v2.py for fresh analysis of the retained three
completed histories, without native rerun. Actual H1.loss.dat lines use ** as
summary-line decoration and *** in the exact CAUTION heading. The reader's
context precheck restricts these exceptions to the known loss-report lines and
retains overflow rejection elsewhere, including additional star fields inside
a summary line. All original CPM/SAT/calendar/depth arithmetic remains bound
to the original reader hash. Original failed verifier receipts stay unchanged.
This is a verifier false-positive correction, not a relaxed physical acceptance
tolerance or suppression of a native failure.

Reviewed correction SHA256 bindings:

- `read_sift_outputs_v2.py`: `7321e9137ed3c5b4e4b60f0666646c09829775930cc1d4226018cbe210d336fb`.
- `read_sift_native.py`: `bf0e15c6a1c04b01d91bfd677e89a8464fefd55cd509bd84464af52a2280de83`.
