# C01 indirect closure security disposition

**Concur with justified-unresolved disposition, explicitly unfixed.** The
remaining native indirect-dependency failure is a pre-existing correctness
limitation, not an accepted-risk exception for a newly introduced security
finding. This classification adds no inferred human approval requirement.
It does not certify the limitation as safe, resolve the retained counterexamples
or waive the package's other implementation/runtime/security gates.

The package expressly permits justified unresolved inventory entries. Its earlier
blanket confirmed-failure closeout wording therefore needs an explicit narrow
qualification for this recorded case; the active plan now names that C01
qualification. Preserve it in the tracker, final inventory and user handoff.
The RAP README accurately states that indirect changes can evade finalization,
while main-file hashes and existing strict publication checks remain in place.

The scope distinction is supported by actual consumers. RAP's owned median
reader consumes key/parameter arrays and NoData; an external mask affecting a
different raster consumer is not automatically a demonstrated RAP dependency.
The retained nested-VRT, Zarr chunk/link and ZIP-external-child cases nevertheless
prove omitted native input bytes can change RAP results. PRISM's captured source
is CLI text, while its retrieved rasters are private per-build intermediates;
the evidence does not justify routing that text through a raster observer or
claiming a separately demonstrated concurrent intermediate writer.

The complete small RAP probe records40 signed files/80 uncached signatures,
234 real native calls,0.0533s finalizer hashing,0.0765s complete validation,
3.9679s actual lock residence and22.0901s analysis. It publishes1,638 rows with
prior numerical parity and confirms named inputs/modules unchanged. These are
actual copied-workflow/lock measurements, not whole native access tracing or a
generic closure proof. No additional runtime was run for this review.

Deferral preserves existing formats, strict finalizers, uncached transaction
hashes and native authority. A cache observer's initially-unverified bypass is
not a publication proof; an equal unverified sentinel must not be used to claim
the result is current. A longer NoDb lock cannot serialize arbitrary file
writers. Generic eager GDAL inventory was already shown to add remote reads
before reporting dependencies; importing that mechanism here would expand
authority without fixing all supported layouts. No such change is authorized.

A future repair needs a bounded RAP reader/publication contract checkpoint:
define actual native dependency membership and coherent read-set binding,
preserve currently accepted local VRT/directory/archive-child inputs, state the
unverified case honestly, and review any additional remote/native discovery
authority before implementation. Retain the current counterexamples and require
whole-set uncached-hash/lock/native parity measurements. A new scanner, format
ban, snapshot protocol or lock topology requires its own evidence and authority;
none is implied by this disposition.

Reviewed SHA-256 values:

```text
derived_indirect_closure_correctness_disposition.md 18c3153439efb5596d4d6061d21e44a19f490065249204dcb37d245f3a1e55dd
rap/README.md a0c3f2730f9b1d6506ce9242836583b64c7160507ecfb072e638a123464a1df6
derived_rap_complete_set_probe.json 7fa1724effc7959abee7903dbeac077e9634957749a8baf6ac8c872d56f5f590
```
