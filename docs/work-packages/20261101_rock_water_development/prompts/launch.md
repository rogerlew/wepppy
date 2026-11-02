# Execute the rock representation and native water development program

You are taking over in `/home/workdir/wepppy` (`/workdir/wepppy` is an alias).
The operator wants sustained autonomous investigation and development, not another
single-experiment handoff. Carry the work through source-owned diagnosis, justified
implementation, independent scientific and implementation review, regression
validation, adoption/release preparation, and durable documentation. Continue
across failed experiments and intermediate commits without asking “proceed?”

## Objective and completion boundary

Develop defensible volumetric and surface-rock support for WEPP generally, with
actual WEPPcloud builders and Roads as important consumers. Resolve the current
signed-water allocation blocker, determine whether the whole-soil retention
proposal is admissible, and carry the surface-rock work to an independently vetted
implementation or a concrete evidence-based disposition. Reconnect accepted work
to the existing Roads program without confusing general model correctness with
agreement against FSWEPP2.

A new trace, one diagnosed failure, a successful probe, an archived experiment,
or an interim commit is a milestone, not the endpoint of this assignment.
A failed candidate is a reason to diagnose, reject, revise or pursue a different
supported mechanism. It is not automatically a reason to return control.

The intended endpoint is a reviewed development outcome spanning the workstreams
below: proven defects repaired and tested, scientific proposals either admitted
with their actual consumer evidence or explicitly rejected, supported surface-rock
work implemented and validated where evidence permits, and a concrete adoption/
release package. Do not promise that a particular formula or surface mechanism
must succeed. If a genuine external-data or authority boundary remains, finish
all independent work first and present the specific remaining decision and ready
artifacts. Do not label the full Roads program complete unless its own acceptance
criteria are met.

## Authority, autonomy and existing gates

This is a broader development assignment than the preceding bounded experiments.
You may select and execute follow-up experiments, prepare new private fixtures,
add observation-only native instrumentation, develop scientifically justified
native behavioral ablations and rock-related preparation/consumer changes, reject
candidates, and implement and test supported fixes. Use the established ablation,
parameterization ADR, contract, independent review and release procedures.

A previous batch's twelve/24-process limit or “next bounded experiment” wording
limits that frozen batch, not this program. Preserve it unchanged; authorize each
new batch through a versioned declaration in the new living plan, with rationale,
controls, stopping conditions and expected decision. Routine batch selection,
reader corrections, source inspection, local builds, tests, documentation and
checkpoint commits do not require another operator approval.

Use local, isolated development and disposable project roots. Prepare validated
native release artifacts, provenance, matched binaries, compatibility/adoption
instructions and release documentation as applicable. Follow existing authorized
release/vendoring scope; distinguish release-ready from released, vendored,
registered, deployed and adopted. Do not invent permission to change existing
project defaults, publish externally or deploy. When a remaining release/adoption
step genuinely needs operator authorization, complete its concrete reviewable
package first and continue other authorized work before handoff.

Preserve the separate human gate for Roads configuration specification AND layout.
Prepare those review artifacts if the science supports them; do not implement the
configuration UI or its production persistence/application wiring before approval.
Do not silently introduce automatic migrations, replacement defaults, broad global
porosity multipliers, or arbitrary numerical tolerances.

Use independent scientific and implementation reviewers at consequential contract,
experiment, behavioral-change and release gates. Delegate review and read-only
investigation as useful; keep implementation ownership coherent. Review HOLD is
feedback to resolve autonomously, not a routine request for operator permission.
Use security/operations review when actual changes cross those boundaries. Do not
substitute repeated review paperwork for new evidence or implementation progress.

## Starting state: verify, do not reset

Latest completed checkpoints at handoff:

- WEPPpy `c6345fd58`: retention/configuration admission experiment.
- Native `c58ad035cd6cb38e74fc4dfe5ba4efa1ddc39a76` in
  `/workdir/wepp-forest-release-20261009`.
- Native canonical branch was `wepp_260430_negmeltfix_comparator`; resolve
  `origin/HEAD` and inspect current state instead of assuming a checkout name.
- Prior retention prototype: WEPPpy `0be460c15`, native `dbe53d54b`.

Never reset to these checkpoints, create/switch branches, or overwrite unrelated
work. Known unrelated dirty files are `wepppy/soils/ssurgo/ssurgo.md` and
`wepppy/weppcloud/routes/usersum/generated/docs_index.json`. Preserve other changes
you discover as well.

The latest raw root is frozen:
`out/retention-frost-consumers-20261101/`.
Archive:
`/wc1/runs/ro/retention-frost-consumers-20261101/retention-frost-consumers-checkpoint.tar.gz`.
SHA256: `9da2823954f78e7e68bcea390e8ba33641b3e9793cb824006f5b0ab290cef467`.
It contains 3,048 verified files. Eight earlier raw roots, totaling 8,248 files,
were verified unchanged. Their receipts are linked from the latest package.

Keep every accepted raw root and closed historical package immutable. Use fresh
versioned roots and `python -B`; do not create caches in retained evidence. Keep
legacy native source, patches, full traces, objects and binaries private. Public
Git artifacts may contain original analysis/probe code, compact observations,
hashes, source references and prose under the established publication policy.

## Read first, then establish one program plan

Read root and applicable nested AGENTS.md, relevant skills, then progressively:

1. `docs/schemas/rock-fragment-representation-contract.md` and
   `docs/schemas/whole-soil-water-capacity-contract.md`.
2. `docs/work-packages/20261101_retention_frost_consumers/`: package, tracker,
   active plan, findings, summary, science/implementation outcome reviews,
   final packaging review and validation. Read the prepared observer code only
   after understanding why it was never executed.
3. `docs/work-packages/20261101_retention_volume_prototype/` and
   `docs/work-packages/20261101_whole_soil_retention_contract/`: findings and
   actual source/preparation/native-reader evidence.
4. `docs/work-packages/20261031_rock_representation/artifacts/development-roadmap.md`,
   the rock-source/SIFT/frozen-water packages it depends on, and the current
   RUSLE specification. Earlier work already repaired dimensional defects;
   do not rediscover or reimplement completed repairs.
5. `docs/work-packages/20261029_roads_parameterization_program/`: current plan,
   tracker, acceptance, autonomy, latest candidate ledger and current findings.
6. Native AGENTS.md, `docs/ablation/protocol.md`, current native accounting
   work-package/incident and relevant science contracts; inspect canonical
   release/build/vendoring procedures before proposing release mechanics.
7. WEPPpy ExecPlan template, artifact observability/preservation standards,
   contract-first standard, parameterization ADR standard and work-package process.

Create a new overarching work package with one living ExecPlan and tracker for
this assignment. Identify it explicitly before edits. Promote durable decisions
into authoritative contracts/ADRs; do not turn closed packages into living policy.
Record current evidence, unresolved questions, milestone acceptance, compatibility
plan, experiment budget rationale and actual adoption authority. Update the
project board and link prior checkpoints without rewriting their history.

Maintain one accumulating decision/candidate ledger. Use subdirectories and
versioned batch receipts instead of opening a new top-level package for each tiny
experiment. Checkpoint commits are encouraged, but continue executing afterward.

## Prerequisite: frost policy, lineage and legacy calibration compatibility

Investigate this early, before interpreting retention experiments or adopting a
new general rock/water formulation. The operator reports that original eRMiT and
WEPP:Roads were calibrated with wepp_2010 and frost.txt present, and questions
whether disabling frost for nonagricultural land use was ever fully justified.
Treat that historical calibration context as an important lead to verify against
actual archived binaries, input bundles, documentation and executable behavior.
Do not treat the presence of frost.txt alone as proof of active frost routines.

Initial local source/history findings (verify exact lineage before relying on them):

- Native commit189e32e8a44dd1de53654426e86b4b284834f45b, dated2022-07-19,
  explicitly describes switching off frost for forest hillslopes while retaining
  agricultural frost. It added a ksatadj(iplane)==0 gate around frostN.
- Commita3a57cb32 subsequently replaced that gate with KSFLAG; inspect the full
  changes and rationale rather than attributing its semantics to the first commit.
- Current infile.for forces KSFLAG=0 when lanuse(1)!=1; winter.for requires
  KSFLAG==1 for frostN. Header values alone therefore do not prove activation.
- frost.txt is parsed independently for winter/thermal/frozen-conductivity
  parameters. Reading its values does not establish that downstream frost calls
  execute. Native land-use codes need not match a user-facing forest/road label;
  inspect actual management decks and mixed-OFE behavior.

Deliver a source/history-backed explanation of when, why and for which paths frost
was disabled, separating documented rationale from inference and unanswered
questions. Follow the connection to forest Ksat adjustments and soil formats,
including later changes. Assess whether the historical choice was a scientifically
supported calibration policy, a numerical workaround, a transitional design, or
something not established by retained evidence. Do not infer motivation from a
commit title alone or blame an individual for an unresolved model interaction.

Reproduce representative legacy eRMiT/WEPP:Roads behavior using verified2010
artifacts where available, and map it to current agricultural/range/forest,
Disturbed and Roads execution. Observe effective flags after native overrides,
actual frost calls, frozen stocks, infiltration/conductivity effects and water
accounting. Separate frost-file presence/contents, frost execution and conductivity
adjustments in declared controlled ablations; isolate these mechanisms in private
source experiments when existing flags couple them. Do not change land use merely
to activate frost or claim a pure frost contrast from the existing KSFLAG panel.

Use this evidence to decide whether retaining the policy, decoupling controls,
restoring frost on particular paths, or repairing frost/thermal accounting is
justified. Any behavioral candidate must pass independent review, representative
cold/warm and freeze/thaw controls, numerical/accounting checks and the relevant
legacy/general/Disturbed/Roads regressions before adoption. Legacy calibration
compatibility is evidence to evaluate, not proof that an old model is physically
correct. Restoring frost globally without this validation is not the objective.

This prerequisite is part of the same autonomous program: continue from historical
findings into controlled experiments and supported development. Do not end the
assignment after locating a commit. Source/history work can run alongside the
failed-event accounting diagnosis, but resolve activation semantics before making
frost-dependent retention or release claims. Extend the living plan and durable
contracts with the resulting policy and compatibility decision.

## Workstream A: resolve signed-input ownership and native accounting

The latest experiment crossed three source horizons, baseline/candidate retention
and KSFLAG0/1: twelve native processes, eleven complete 16-year histories and one
failure. Zero-rock output pairs are exact under both settings. All accepted
histories contain 17,532 OFE/day rows.

The failure is source horizon84543461, candidate retention, KSFLAG1, simulation
year9/day355/OFE3/hour1. Native emits HOURLY_WATER_UNMET and STOP1; stdout prints
hrfin=-2.42531928e-12m and available=0. Source assigns hrfin=xfin before comparing
-dble(xfin) against sum(max(0,ST)). This is a rounded diagnostic, not exact retained
upstream operands. The failed ordinary output has 9,830 rows. Last complete coarse
snapshot has zero ST, FRZW and frozen thickness; approximately43.1953mm of
integrated dry-reference liquid remains. That is not allocatable relative ST.

Start by retargeting existing BP_WBH_SOURCE/ALLOC/BEFORE at the failed event in a
fresh declaration. Determine whether existing payloads establish FIN, returnbase,
returnrouted, fractions, area scaling, upstream contributions and exact operation
order. Add observations only for missing producer/consumer links. Preserve the
expected failure and verify comparable prefixes for observation-only changes.

Then continue beyond tracing: determine the violated contract or unresolved
physical assumption, construct meaningful controls, and test the smallest
source-supported repair where justified. Distinguish precision/cancellation,
return-flow timing, unavailable relative storage and invalid input/physics.
A tiny number alone never justifies dropping a residual, spending dry-reference
water or adding a floor. Do not demand a behavioral fix if the candidate input
must instead be rejected, but carry the resulting decision into the retention
workstream. Assess every confirmed consumer of a repaired shared assumption.

## Workstream B: decide and implement admissible volumetric-rock support

Reconcile whole-soil versus fine-earth retention, density basis, fragment mass/
volume conversion, native CPM, entrapped air, source/native caps, actual layer
support and dry-reference coordinates. The current native reader adds200mm to
final source depth before its1800mm cap and resamples in binary32. Use actual
consumed thickness and density, not nominal emitted values.

The previous volume inverse produced42 eligible preparation cases and twelve
complete prototype histories, but those histories skipped frost. The newer
KSFLAG1 panel establishes actual frost execution, not complete physical admission.
KSFLAG also changes rangeland conductivity; do not assign its effects solely to
frost. Do not assume nonporous-fragment dilution is universal field truth.

Complete executed consumer-domain and accepted-flux evidence needed for a decision,
including positive HK/log domains, both lower-layer ST/UL consumers, lateral
( ST-DRFC )/( UL-DRFC ), capacity changes, frozen references and accepted sinks.
The prepared new observer was never built or invoked. Its controls are useful,
but its runner is an unapproved draft. Review/revise it against actual current
source and bindings before use. Existing flux readers omit input/percolation
closure; close that omission where required instead of widening the claim.

Test meaningful zero/high-rock, cap/boundary, density, dry/saturated, zero-input,
freeze/thaw and actual crop/range/Disturbed/SoilGrids/SSURGO/SIFT paths as applicable.
Separate mechanism lanes; do not combine retention, porosity and surface armor
into a single candidate. Preserve water displaced by any capacity change as an
owned flux. Keep source exclusions and missing-data semantics visible.

If evidence admits a preparation or native correction, implement it with contract,
ADR, actual builder/serialized-file/native-consumer validation and regression
coverage. If the inverse fails, document why and investigate the next supported
representation instead of polishing an unadmitted candidate into a release.
Do not stop after a scalar or initialization-only success.

## Workstream C: complete the surface-rock support investigation/development

Run useful independent surface work while native campaigns execute. Resume
source acquisition with bounded retries and record failures; do not let an
unavailable endpoint block unrelated work. Retain particle-size thresholds,
material/wood exclusions, source date, role, component/support weights, nulls,
measured zero and uncertainty. Resolve overlapping size classes before aggregation.

Keep profile mass, profile volume, total-area surface cover, exposed rock within
bare area and fraction of bare distinct. SoilGrids/SSURGO proxies are not measured
engineered road armor. Address RAP/SBS overlap and existing cover protection without
double-counting. Never switch landuse or change profile RFG to simulate surface rock.

Map native consumers before introducing a persistent rock representation. Keep rock
outside biomass/decomposition. Separate interrill shielding, rill friction and
infiltration hypotheses and their evidence. Area accounting alone does not validate
a residue-calibrated mechanical response. Build a minimal isolated implementation
where supported, with exact zero-rock controls and actual branch/operand evidence.
Do not invent dynamic burial/exposure rates without support.

Carry supported source/provenance and consumer changes into real generated
artifacts and representative project execution. If mechanical parameter evidence
is insufficient, finish the useful representation/acquisition/compatibility work
and state precisely which mechanism remains unadmitted; continue other streams.

## Workstream D: integration, regressions and release/adoption outcome

Integrate only independently admitted changes. Validate actual production builders,
NoDb/RQ paths where affected, emitted WEPP files and full configured native outputs.
Disposable full-project and general Disturbed/watershed validation are required
where those consumers change; a hand-built three-OFE fixture is insufficient.
Keep earlier passing and opposite-response controls, zero-rock identity and
source-specific compatibility. Test the actual matched binaries under canonical
compiler/toolchain/runtime identities and release gates. Run tests appropriate to
production changes, including the repository's required broad checks.

Reconnect changes to the original Roads development panel and original thresholds.
Meaningful reference loads above1kg/year use0.1–10times reference; small loads use
max(1,10*reference)kg/year. Overall95% and major-stratum90% requirements remain
unchanged. Historical full-matrix baseline was713/766 meaningful and31/74 small
passes; verify current ledger. Agreement is not physical validation or field
calibration. Do not consume withheld materials1718472,53975,1718476,665770,2711196,
658566 or use withheld outcomes for development. No per-case/climate fitting.

For admitted native changes, prepare the release through established matched-build,
regression, provenance, changelog and release-note procedures. Document explicit
rebuild/adoption behavior and existing-project compatibility. Carry out steps
already within existing release authority; stage any genuinely unapproved
publication/default/deployment action for the final concrete decision. Do not
silently substitute a research observer for the production binary.

## Execution discipline and stopping rules

- Establish hypotheses and invariant/control gates before observing each new batch.
  Keep finite batches and explicit failure stops; a stop ends that batch, then
  diagnose and version the next justified experiment autonomously.
- Preserve original failed readers/processes and accepted evidence. Do not rewrite
  declared tolerances or inputs to relabel a failure. Avoid model reruns when a
  corrected reader can resolve an artifact interpretation issue.
- Work from actual artifacts, exact clocks, native precision and source ownership.
  Model completion, plausible annual totals and a successful footer are insufficient.
- Review scientific validity separately from implementation/parity. No behavioral
  candidate is promoted on instrumentation parity or sediment reduction alone.
- Pin native build PATH and compiler/linker as specified by native governance.
  Keep full build/input/runtime identities and per-invocation receipts.
- Archive only after writers clear; verify all members and complete inventories.
  Verify staged/committed bytes, including LF-normalized native CSV metadata.
- Keep concise progress updates and living-plan state so compaction or a fresh
  continuation does not reset the investigation. Do not require human attention
  for routine implementation choices or experiment transitions.

Return control only when the integrated development/release-preparation outcome
is complete, a real external/authority decision prevents all meaningful further
progress, or the operator explicitly stops work. Exhausting one planned batch,
finding another defect, an AI review HOLD, a failed candidate or reaching a commit
is not such a boundary. If one workstream is blocked, continue independent ones.

Final handoff: concrete findings and implemented behavior; accepted/rejected
mechanisms; completed scientific, artifact, regression and release gates; exact
commits/binary/archive identities; actual release/adoption/deployment status; and
only the remaining decisions that genuinely require the operator. Link the durable
contract sections documenting behavior and rationale. Be candid about scientific
gaps, and make any necessary approval the final step on a finished review package.
