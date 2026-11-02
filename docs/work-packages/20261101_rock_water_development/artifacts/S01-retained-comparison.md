# S01 retained comparison and interim recommendation

The optional inverse does **not reliably recover exact source whole-soil FC/WP**
through arbitrary heterogeneous native profiles. Retained observations demonstrate
noncommuting layer mixing and density clipping. It does improve algebraic recovery
in the three observed profiles below. That finding does not establish universal
numerical validity, field accuracy or calibration improvement.

Recommendation at this checkpoint: **retain optional-only status and preserve the
current default**. Do not propose default adoption from these results. S01 remains
open for actual heterogeneous-OFE, boundary, fallback and later-tillage evidence.
See [static analysis](S01-static-analysis.md) and [coverage gaps](S01-evidence-gap-matrix.md).

## Integrated native readback

The new read-only integration joins all90 retained initialized layers in six P03
observed histories to source targets and actual computational thickness. There are
18 OFE profiles; the three OFEs within each history repeat the material. Values
below show OFE1, in mm over actual approximately800mm support, not the700mm emitted
clip. FC/WP integrals describe retention coordinates, not realized water stocks.
Residual is native retention integral minus overlap-weighted source integral.

| Profile | Default FC residual | Optional FC residual | Default WP residual | Optional WP residual | Initial absolute liquid, default / optional |
| --- | ---: | ---: | ---: | ---: | ---: |
| H11 | +2.379572 | +0.126978 | +1.341264 | +0.071994 | 147.090726 /147.090726 |
| H28 | +28.752347 | −0.327424 | +12.834194 | −0.267869 | 236.626770 /236.626778 |
| H40 | +15.141917 | −0.072800 | +6.372217 | −0.046391 | 387.245819 /387.245812 |

For H28, relative ST changes from168.352574 to181.454647mm while its dry-reference
contribution changes from68.274196 to55.172130mm. Absolute initial liquid changes
by only0.00000745mm. Thus increased relative ST is not increased initial water.
The readback preserves native FC-above-dry and UL separately from the absolute
retention integrals. Initial-liquid equality is specific to these retained inputs;
it is not imposed as a universal invariant when saturation/retention guards change.

Actual frozen liquid and ice require respectively
`ST + dry*(h-frozen_depth)` and `FRZW + dry*frozen_depth`. This integration adds
no new frozen-state observation or complete daily/hourly water budget. It retains
the existing per-history domain and accepted-root summaries without expanding
their scope. H40 has87,660 observed layer root debits across17,532 OFE-days;
nonlinear proposals and selected hourly contexts are not independently solved
whole-history closure. Existing ET and routed-output differences remain consequences,
not evidence that closer FC/WP is a better calibrated model.

Private root `out/rock-water-development-20261101/supplementary-ssurgo-compensation-integration-v1`
contains the original reader, all90 layer joins,18 integrated profiles, nine paired
differences and input/output hashes. Receipt SHA256:
`50d82c8e1af7084d7d42049dd54be4b63468798e9ea3076c0c2ce8d5b7e8f0c4`.
No native model, builder or production mutation was invoked.

## Boundary diagnostic is not native coverage

A separately declared14-case synthetic arithmetic diagnostic calls the existing
optional `retention.decision` and compares the two existing preparations with the
documented native CPM expression after INPUT density/rock bounds. It covers zero,
48%,49.99/50/50.01%,84.99/85/85.01% rock and0.79/0.80/0.81 plus1.99/2.00/2.01g/cm³
density. Above85% remains excluded and unchanged by the optional policy. No third
production formula, fallback substitution or eligibility relaxation is introduced.

These are explicitly synthetic, pre-guard calculations: no Horizon construction,
Rosetta prediction, actual soil serialization, native binary or dynamic history
was run. They do not close the corresponding native coverage gaps. Missing/mixed
retention branches still require actual builder and native identity evidence.
Private root `supplementary-ssurgo-compensation-boundary-v1` retains declaration,
helper, inputs and results; receipt SHA256:
`4dfe4a613bc8cc03b5c8068653171dd1bed0948848da1dfc4bb259f6a7cfb615`.

## Exact source references

Native references below are relative to the compiled d2e14d96 source bound in the
static report, not the separate modified `/workdir/wepp-forest` checkout.

| Stage | Source reference |
| --- | --- |
| Original density, Rosetta choice, independent FC/WP branch/final pair fallback | `wepppy/soils/ssurgo/ssurgo.py:499–609` |
| Rock preparation and optional eligibility/application | `ssurgo.py:636–663,1061`; `wepppy/soils/ssurgo/retention.py:38–83` |
| Serialization and split-row identity | `ssurgo.py:1531–1633`; `retention.py:95–140` |
| Treatment/stack/stage | `retention.py:199–346`; `wepppy/wepp/soils/utils/multi_ofe.py:57–94`; `wepppy/nodb/core/wepp.py:633–680` |
| Native support, bounds, units, separate overlap averages | `src/input.for:565–632,700–943` |
| Initial tillage mixing before CPM | `src/input.for:956–962`; `src/tilage.for:210–258,519–674` |
| Initial density estimate, CPM, retention guards and initial storage | `src/scon.for:182–345,510–518` |
| Later density/POR evolution without CPM recomputation | `src/soil.for:270–302,398–403,464–505,579–584,698–735` |
| Initialization-only FC/HK and downstream domains | `src/watbal.for:253–309`; `src/watbal_hourly.for:263–316,654–770`; `src/purk.for:155–158`; `src/perc.for:135–150`; `src/drain.for:122–123,289–291` |
| Accepted uptake, evaporation and dry-reference water | `src/swu.for:169–177`; `src/evappm.for:332–404`; `src/watbal_hourly.for:1079–1080,1148–1149` |

## Remaining execution and compatibility

The parent test owner confirmed isolated preparation does not overlap broad-v2.
The suite was still running at this checkpoint; its inputs and evidence were not
modified. Delegated experiment preparation/review stopped on the agents' usage
limit. The program requires independent review of consequential preparations and
actual findings; no new native build or history has bypassed that requirement.

Private `supplementary-ssurgo-compensation-design-v2/design.json` binds six actual
two-policy soil origins and H11 nonsoil inputs. Its proposed four histories use
unchanged three-OFE geometry and H11/H28/H40 materials on successive OFEs, each
policy plain/observed. Three OFEs avoid altering the retained geometry merely to
obtain two different materials. The observer must distinguish initialized FC/HK
owner from actual first consumer, including executed PERC power-branch operands.
Design SHA256 is `c21a706f1cc6b3103442300259c91257328360e7e687619ac1853a0fcab28c57`.
This is a design, not an execution declaration: generated input hashes, observer
build/review, resource coordination and approval remain outstanding. An incomplete
v1 design with an inherited-case lookup error is preserved separately.

Supported scheduled tillage, actual mixed/Rosetta branches and upper-cap/boundary
native observations remain unresolved. Do not interpret successful repeated-profile
P03 histories as heterogeneous FC/HK ownership evidence. No repair of that native
ownership issue is authorized by this supplement.

Existing projects and uploaded soils remain byte-for-byte outside this investigation.
Default rebuilds retain the existing mass-complement preparation. An explicit opted-in
rebuild can change soil FC/WP and downstream outputs; retain its policy marker,
source acquisition association and full companion lineage. Regenerate dependent
hillslope/PASS/watershed artifacts consistently rather than mixing results from
different soil policies. No silent migration, automatic rebuild, native formula
change or deployment follows. Any later default proposal needs its own evidence-
backed ADR/adoption decision and compatibility policy.
