# Scientific review of the revision-4 observer

Status: revised observation map accepted for the bounded prebuild gate, subject
to independent implementation review and the declared runtime/parity checks.
Independent AI scientific review; this is not institutional peer review, model
validation or parameter promotion. The nine-pair selection review is unchanged.
The companion acceptance receipt binds the exact private map and patch hashes.

## Hydrologic interpretation

The native GRNA storage calculation uses the first two computational layers,
not the entire soil profile. For a contributor, the represented capacity is
the sum of positive differences between available upper storage after ice
exclusion and the saved liquid stock. Connected contributors are weighted by
their lengths and divided by the effective length. The associated percolation
coefficient is similarly a length-weighted combination of each contributor's
minimum conductivity. It is not the minimum conductivity across the entire
connected hillslope.

The exact consumed saved stock must be recorded: current upstream liquid stock
can already have changed in water balance. Neither total porosity minus a
published daily soil-water total nor a later layer snapshot reconstructs this
operation. Retain raw available-liquid stock, available upper storage, ice,
wilting content, layer thickness and actual contributor lengths. Available
liquid above wilting is not total soil water.

Keep GRNA's event-time coordinates and hourly allocation-bin indices separate.
Hourly allocated infiltration, incoming surface return, incoming/outgoing
lateral water and subsequent surface return have distinct ownership and area
bases. Use the native depth/length factors before converting them to volumes.
The late CONTIN water-balance path must remain distinguishable from water
balance within IRS and from the erosion setup decision.

Frost depth, thaw depth, frozen thickness and ice can identify the represented
frozen-state branch. Layer temperature is explicitly unavailable; these traces
cannot establish a thermodynamic explanation. The revised map supplements
interval-end GRNA samples with all constructed cumulative grid points and the
guarded produced excess grid. These are still not a final routed hydrograph;
a hypothesis needing missing routing-time information requires an extension.

## Sediment interpretation

The map must distinguish an incoming normalized load from an outgoing sampled
load. Native upstream sediment discharge per unit field width, its incoming
class fractions, receiving transport-capacity normalization, rill width and
spacing, and effective runoff duration are separate operands. Record the
upstream SLOSS handoff and receiving ROUTE entry independently. The solver's
incoming rate multiplied by the receiving effective duration need not equal
the published upstream event mass when durations differ; preserve that
comparison without forcing equality or changing a tolerance.

Effective interrill delivery includes its rill/spacing basis. The normalized
interrill parameter additionally has duration correction and snow, melt and
runoff-support gates; the uncorrected dimensional detachment operand alone is
not the applied event source. Applied shear, critical shear, capacity operands,
settling properties and class normalizations must retain their actual scales.

SLOSS grid differences are signed **net** exchange over each grid cell. Positive
and negative cell sums do not resolve simultaneous erosion and deposition
within a cell. ROUTE regime endpoints can support more detailed signed
integration only after matching executed subintervals, transition coordinates,
the interrill term and native dimensional factors. EROD's stored derivative is
not necessarily a freshly computed endpoint derivative; its crossing coordinate
is meaningful only under the corresponding returned crossing flag. Neither
these observations nor terminal class fractions identify tagged sediment origin.

## Soil conditioning and validity

Published SOIL roughness differences are useful descriptive context. The
observed consolidation condition and its current operands are needed to
establish whether the roughness-decay branch executes. Complete soil profiles
also change many other hydraulic and erodibility inputs; a correlation between
roughness and the selected discrepancy groups does not isolate roughness.

Every field needs a valid-state guard or explicit retained-state interpretation.
In particular, no-excess GRNA returns do not freshly assign every persistent
output operand. Unconditional day/OFE owning markers and entered/skipped branch
status must distinguish a valid dry path from missing coverage. Never infer
zero class loads from missing routing observations or print inactive locals as
if they were valid measurements.

## Release of this observation gate

Before build, bind the corrected map, complete private observer patch, actual
source/include/object bytes, compiler settings and fixed seed declaration, with
independent implementation review. The first full-period pair is the preflight.
All 18 lanes then require exact equality of all seven ordinary native outputs
against their own accepted R4 records, unchanged inputs, normal completion and
valid trace coverage. Strict particle flags remain visible. A failed observer
attempt must be retained and cannot support scientific interpretation.

No production source, model arithmetic, parameter, acceptance threshold or seed
change is authorized by this review. The observed results may support a bounded
causal hypothesis or a separately reproduced defect; they do not authorize
parameter fitting.

The final map closes the review requests for consumed saved-state operands and
contributor lengths, actual hourly surface/lateral source and outgoing terms,
forcing/interception, incoming-flow field identity, interrill-duration gates
and persistent no-excess output semantics. No scientific map blocker remains.
The raw traces and their derived integration have not yet been validated;
scientific interpretation is explicitly pending the preflight and full panel.
