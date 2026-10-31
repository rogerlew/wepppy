# Legacy format bridge: rejected equivalence preflight

Seven full-period conversions completed and passed fresh physical audits. None
passed the declared exact output/state equivalence gate. No whole-role legacy
substitution was executed. This is a failed diagnostic representation, not a
newly established sediment or water-accounting defect.

## What matched and what differed

- Four materials (2711184, 1718510, 1856573, 53949) have identical initialized
  state observations and identical model outputs except the extended-format
  caution inserted in `H1.loss.dat`.
- Three materials (1718465, 2711250, 1718494) have one-to-two-float32-ULP changes
  in initialized surface conductivity and differences in several raw output
  files. Other recorded initialization fields match.
- Parsed annual sediment export is unchanged for all seven at LOSS reporting
  precision. That rounded equality is not exact model-output equivalence.

The verifier explicitly identifies the known caution block, but does not waive
it in the gate. It rehashes every input/output and recomputes native physical
audits. An unconsumed `reference.sol` copy is attached after execution solely to
satisfy the existing auditor's working-directory inventory contract; consumed
input manifests remain unchanged. See [verification](legacy-format-bridge-r3-verification.json).

## Source trace

`input.for:523` deliberately writes the nonstandard-format warning for versions
at or above 7777. A pure 98.4-to-9002 conversion therefore cannot preserve every
raw report byte under this gate.

Legacy `avke` is converted from mm/h and assigned directly to upper-layer `ssc`
in `tilage.for:584`. Extended-format horizon K traverses INPUT's harmonic remap
before TILAGE. INPUT's final conductivity assignment uses `slayth/ksinv(i)`;
`slayth` is carried from the completed remapping loop. With the 400-mm legacy
fill/buffer profile, the native-added 200 mm produces a three-layer profile;
float32 depth accumulation and the final-layer subtraction differ slightly from
the first-layer thickness. This source path explains why a mathematically equal
surface K need not preserve its exact floating-point state. The recorded
initialized differences are conductivity only; this is not a claim that these
small roundoff differences explain the broader Roads magnitude discrepancy.

The other tested legacy profiles and their initialized states are retained in
[the observation results](legacy-format-bridge-r3-results.json). Native version
branches also select conductivity floors and lateral-flow calculations; those
must not be ignored when claiming format equivalence outside this preflight.

## Disposition

Retain the strict failure and stop the bridge expansion and mixed-role panel.
Do not tune horizon boundaries/numeric encodings until raw outputs happen to
match, suppress model warnings, add a native adapter or weaken production soil
validation to make the conversion pass. The preflight's duplicate terminal
200-mm boundary and zero estimation sentinels are forensic inputs only.

Continue a narrower same-format generated-soil experiment instead. Its fill
adjustment and buffer-conductivity controls change explicit consumed fields
without copying any legacy material or claiming equivalent legacy hydraulic
states. That alternative is recorded in the active plan and ADR-0120.
