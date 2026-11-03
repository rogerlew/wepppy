# Revision 7 copied-project preparation and execution design QA

Reviewer: `mipa_qa`, 2026-11-03 UTC. Read-only implementation and input review;
no native invocation, original-output interpretation or source mutation by QA.

## Disposition and exact scope

**PASS for the bounded baseline invocation declared by v3 below.** Complete
configured preparation, companion settings, emitted OFE references, input
calendars, execution identity and exclusion of withheld materials are verified.
Native consumption, output validity and installed-reader acceptance remain
pending. This review does not accept the later four-design Roads workflow,
parameter defaults, withheld validation, browser/RQ rollout or the human UI gate.

The disposable project is
`/wc1/runs/ro/roads-parameterization-program-20261103/current-project-v1/baseline`.
Source material files were retained from `/wc1/runs/cl/clogging-starch`; this is
complete current model-input preparation, not a new soil-database acquisition.
The retained-material preparation lane is separate from exact-input r4/r7 replay.

| Reviewed artifact | SHA256 |
| --- | --- |
| `current_r7_project.py` | `aaea2b1ff60d48ab5174a8f66629eee61e441a109e0e04cb8a1d3bcfb254e2ae` |
| `execute_current_r7_project.py` | `0d0a2804e5f4346513228aa09d0cf6f4a6ef15130bbfff9c6e61954468b8ac5c` |
| `resumption-r7-current-project-protocol.md` | `e8bf40b928042b3890597e8abc212087be64a3fda1f3e518c965cc1f3fbf2d16` |
| `preparation-declaration.json` | `b2c6b9810718497c6d8b21323ee06f0d94bcb40b2e72a53903c32e9b682a569e` |
| `prepared.json` | `c375c6292de693e46680ec0af526a4821ca51d0d5c0a33fffd650551de4aa7a2` |
| `baseline-execution-declaration-v3.json` | `d5178b116fae71c4c4e15f07febc1c96f52f2b78c500affa1b8885b8c6b0e0fa` |

V1 and v2 declarations remain unexecuted predecessors. V2 adds the canonical
hillslope interchange boundary needed before watershed postprocessing. V3 also
binds copied NoDb settings, effective flags and owned configuration files.
The additive revisions retain identical prepared model inputs.

## Independent input and configuration readback

QA rehashed all **344** declared model inputs, **12** copied NoDb files and
**1,153** dependencies, including installed Rust readers, owned Python/config
files and the exact matched binaries. Prepared hill inputs remain the original
334 entries: 66 hills × five files plus four shared runtime companions. Watershed
preparation adds ten files without changing those 334. Original source inventory
contains **3,374** bound entries and remains unchanged before and after review.
At readback all output directories were empty and no execution-start receipt
existed. The declaration binds UID 1000/GID 993 and four workers.

Selected watershed binary SHA256:
`4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825`;
selected hillslope binary SHA256:
`210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`.
The selected `wepp_261029` pair matches the declared revision 7 release.

Effective UI, groundwater, PMET, snow, multiple-OFE and watershed flags are true;
frost and deletion after interchange are false. Serialized NoDb settings agree
with the preparation receipt and actual files. `wepp_ui.txt` exists; no frost
companion is present. Groundwater values are 200 mm storage, 0.04/day baseflow,
zero deep seepage and 1 ha threshold. Snow settings are -2 C rain/snow threshold,
100 kg/m³ new-snow density and 250 kg/m³ settling density. Actual companion bytes
match those settings; enabled context was not inferred from flags alone.

All 66 management and soil files parse. Their **193 OFE** counts also match their
slope files. All **3,088** serialized management-year crop references resolve to
the three emitted PMET table keys with coefficients `(0.95, 0.8)`. This project
therefore checks identity/reference propagation but does not discriminate
coefficient ownership between different pairs. Every climate has exactly
**5,844 unique daily dates, 2000-01-01 through 2015-12-31**, and every hill run
requests 16 years. Each declared output path resolves within the disposable
project. `pw0.run` references exactly the 66 newly planned hill PASS files.

QA independently reconstructed each emitted soil OFE from its copied retained
source template, applying only the declared initial saturation (0.75), lower
boundary conductivity (0.01), and 700-mm depth clipping in memory. All **193**
full parsed OFE dictionaries match, including material fields. This supplements
comment-line provenance with actual emitted-field equality. No file was written
by this reconstruction.

## Withheld split protection

The six reserved IDs in frozen `design-v2.json` are 1718472, 1718476, 2711196,
53975, 658566 and 665770. None is assigned to an active baseline hill, appears
in the compiled 193 OFE lineages, or appears in the prepared watershed soil.
The compiled material counts are:

| Retained source material | Compiled OFEs |
| --- | ---: |
| 2711184 | 49 |
| 67225 | 72 |
| 67141 | 3 |
| 2711195 | 15 |
| 2711253 | 3 |
| 2711198 | 51 |

The dormant 2711196 SoilSummary has zero area and zero percent coverage. Its
presence in copied metadata does not mean that material reaches native inputs.
QA inspected metadata and generated inputs only for this split check; withheld
native outcomes were not read or used for candidate selection. Later Roads
contexts require their own emitted-material split check before invocation.

## Implementation quality and remaining evidence gates

Preparation rebases nested serialized source paths before NoDb deserialization,
then preserves copied old runs/outputs outside the new run directories. Complete
`prep_hillslopes` is followed by complete watershed preparation. The executor
checks exact declarations, settings, dependencies and binaries before using the
canonical controller methods. It creates a single-use start receipt, rebuilds
hillslopes, invokes the canonical hillslope interchange with raw PASS retention,
then runs the watershed and its normal postprocessing. The interchange arguments
match the RQ stage's continuous-climate watershed boundary. It does not splice
old PASS data into the fresh run.

No blocking quality finding remains for this experiment. The scripts are bounded
experiment tools with hard-coded counts and immutable predecessor hashes; this
is suitable for the declared project, not a reusable execution service. They use
Python assertions as gates and must run without optimization. Their source and
settings inventory intentionally favors reproducibility over a minimal dependency
set. These are explicit local constraints, not reasons to widen production code.

After execution, require actual native identity/consumption markers, complete
calendars and output families, artifact-based physical diagnostics, new PASS and
watershed routing provenance, installed interchange/report readback, input/source
integrity and retained failure accounting. The completion receipt correctly labels
independent artifact readback as pending. The separate Roads lifecycle must still
retain both the full-upload unrutted negative geometry case and the explicitly
OSUNUM6-excluded positive control. No full-workflow result is claimed here.
