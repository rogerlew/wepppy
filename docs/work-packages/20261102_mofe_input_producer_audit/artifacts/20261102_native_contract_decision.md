# MIPA-02: native coefficient repair and undeployed release revision

## Authorization and source boundary

Operator instruction on 2026-11-02: “i think we need a contract first fix for the
implementation then resolve any producer/consumer discrepancies. wepp_261029 still
hasn't been deployed so we should revise that release and release note”. This
ratifies the bounded intent below and extends the active package's existing commit
authority. Deployment is separate.

WEPPpy starts at `d75456643`; native default-branch checkout
`/workdir/wepp-forest-release-20261009` starts at `56e4fc293` (release-5 executable
source `d2e14d96a`). Remote-default and checked-out branches both resolve to
`wepp_260430_negmeltfix_comparator`. Existing unrelated dirty/untracked files stay
untouched. No branch switch is needed.

## Normative delta and discrepancy disposition

Canonical authority is `docs/schemas/native-mofe-coefficient-contract.md`, the
amended MOFE identity and whole-soil contracts, and native
`docs/contracts/mofe-coefficient-ownership.md`. Native/source and binary lifecycle
AGENTS remain applicable. NATIVE-03 is an implementation defect: change COMMON
FC/HK storage and every active reader/writer to `(layer,OFE)`. Scope is cwater.inc,
watbal.for, watbal_hourly.for, purk.for, perc.for and drain.for, their source specs,
regression/observation helpers and matched release metadata. NATIVE-01/02 are
selected-source discrepancies requiring verification: current release already
sizes PMET to ntype and has no kernelized adapters. Do not copy obsolete defects
into this release or rewrite working PMET logic without new evidence.

Preserve formulas, thresholds, defaults, initialization timing, fallback and all
output formats. A separate ADR records ownership's numerical consequences without
claiming parameter retuning. Additional producer changes require a demonstrated
selected-consumer discrepancy and a checkpoint amendment before behavioral edits.

## Compatibility, security and regression

The COMMON ABI changes internally: clean full rebuild and matching hill/watershed
pair are mandatory. Existing persisted projects and historical outputs stay fixed.
New numerical histories can change; quantify them rather than requiring false
heterogeneous parity. Single-OFE and repeated-material controls should remain
identical unless a separately explained ownership difference exists. No new file,
network, authentication or privilege interface is introduced by the native fix.
Release publication exposes only reviewed PDF and source-free manifest; preserve
historical reports and baseline pair. Review file staging/provenance and exact
application workflow under existing identities.

Required evidence: failing-before/passing-after distinct materials and unequal
layers; both retention policies; daily/hourly ownership; executed PURK and PERC
sub-0.95 branch; drain/lateral operands; observational neutrality; PMET named and
fallback capacity at role bounds, mapped indices and transition; explicit soil/cover support matrix and separate capable-consumer 9005 gate; output/report readback; native mandatory gates; exact final
Linux pair and sidecars; independent correctness, QA and release-disclosure review.
Use committed inputs/generators for mandatory gates. Actual project forks supplement
them. Scheduled tillage, missing-density and guard cases get explicit dispositions.

## Checkpoint status

Canonical amendments pass two independent read-only reviews after disposition
of the 9005/cover and PMET malformed-state findings. Standalone ancestor commits
are the next gate. Implementation must not precede those commits.

## Review discovery: 9005 is a separate consumer boundary

Independent correctness review confirms selected261029 misreads the extended
9005 header and takes two restrictive-layer reads; its conductivity lower-limit
branch applies only to9003. The amended contract does not promise compatibility.
SOIL-02 and COVER-01 native acceptance remain HOLD pending a bound capable consumer or a
separately reviewed reader/behavior amendment. Operator preference was requested
asynchronously while FC/HK work proceeds independently.

Retained baseline pair and both sidecar sets:
`/wc1/holdouts/mipa-native-r6-20261102/baseline-r5/manifest.json`.
Existing bounds-checked native PMET hill-capacity test passes at32 entries.
