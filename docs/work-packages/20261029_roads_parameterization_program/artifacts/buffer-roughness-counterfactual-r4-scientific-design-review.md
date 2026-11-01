# Independent scientific design review: buffer roughness persistence

Disposition: the single intervention is suitable for a bounded research test.
This is independent AI review, not institutional peer review. Exact implementation,
build, runtime, and outcome acceptance remain separate gates; no parameter or
release is accepted by this design review.

## Intervention and interpretation

Holding the buffer's captured, post-native-initialization random roughness is a
well-defined persistence counterfactual. It changes one assigned model state,
without fitting a new roughness value or changing the soil profile. The existing
forest-in-cropland management description motivates examining the conditioning
interaction. It neither validates 100 mm nor establishes that native decay is a
defect. The actual prepared profiles remain the legacy and U12 research profiles.

The proposed restore after all SOIL roughness writers and before INFPAR preserves
natural roughness-dependent infiltration/crusting, friction, critical shear,
interrill delivery, depression storage, and thermal/melt responses. In particular,
PARAM's interrill delivery response differs strongly between the configured and
floor roughness values. A sediment improvement cannot be attributed solely to
water storage. SNDRFT is a source reader whose call is inactive in this executable;
it must not be presented as an executed causal path.

## Density versus other endogenous states

The invariant is fixed density inputs and handling, with no direct assignment to
BD, BDCONS, POR, RH, or other model states. For this fixed-management,
nonirrigated, no-tillage panel, stronger exact density and porosity comparisons
are source-supported: SOIL density depends on initial soil/tillage operands,
day counts, and climate-derived cumulative precipitation. COCA is initialized
from soil properties; porosity follows density and that correction. Bind and
compare BDTLL, AO, BDCONS, COCA, day counts, and RFCUM, as well as BD/POR, so the
claim is checked rather than assumed. Management drift invalidates this domain.

Ridge height is different. Its native decay also depends on the residue-derived
CBR multiplier. The prepared buffer management has RHINIT = 0.1 m, so a floor
argument does not establish invariant RH. Changed hydrology can affect residues
and subsequently native RH, despite no direct RH intervention. Predeclare
RH/SMRM/CBR as observed endogenous responses, retain their history, and investigate
unexplained changes. Do not add a ridge-height clamp or retrospectively loosen an
exact-equality gate. The same principle applies to effective hydraulic and
sediment parameters derived from the changed state.

## Controls and falsifiability

The nine frozen pairs preserve both error directions, passing controls, and the
other road geometry. All 18 off lanes must reproduce all seven original ordinary
outputs exactly. The nine legacy and three generated underprediction lanes are
12 predicted null controls; their identity must be proved using unrounded native
pre-restore values at every call, followed by exact outputs and appropriate
consumer observations. An unexpectedly nonidentity null control is a failed
prediction requiring review, not a case to relabel after observing its result.

Use complete 16-year histories for all 36 runs. The four-run first-pair preflight,
strict physical and particle gates, source/input/output hashes, and explicit
branch availability are appropriate. Compare on minus off within each soil lane
first. Upstream road/fill state and output readback is required; an unexpected
change needs an owning-path explanation, since spatial position alone does not
prove isolation of every deferred routing output.

The original magnitude envelope and declared recovery/no-regression criterion
make this selected-panel diagnostic falsifiable. Retain worsened and null cases,
undefined zero-denominator ratios, and printing limits. Passing does not prove
annual causal shares, broad-matrix success, physical correctness of legacy soils,
or a universal forest roughness rule. Stop after this rule; alternative values or
additional state overrides require a new declaration.

## Remaining gate

The clarified plan now explicitly separates exact density/POR controls from
endogenous RH/residue responses and identifies SNDRFT as inactive. The actual
source map and implementation must preserve those distinctions. Review the exact
intervention patch and valid-state observation map separately before build/run. Full-period
state traces must cover the density drivers and residue/RH response above, and
null-control evidence must use the actual native values rather than rounded SOIL
output. No native simulation was executed for this design review.
