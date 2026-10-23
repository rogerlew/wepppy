# Independent management-reference contract review

Date: 2026-10-23 UTC. Reviewer: integration_contract_review.
Initial suite checkpoint: `c4774cf2a`. Preimplementation review; production source
and legacy templates remain unchanged at the fingerprints below.

## Disposition and authority

Approved for the second contract checkpoint. No unresolved high or medium finding
remains. The native rejection prevents the requested no-traffic validation from
running, and the same transformation changes an existing residue reference's
meaning in two-OFE inputs. Repairing that bounded input-writer defect is a
necessary prerequisite within the authorized validation task. It does not
authorize changing legacy scientific parameters, model defaults, formulas,
routing, accounting, public APIs or historical project artifacts.

The initial package described a tests/fixtures/documentation-only scope. That
medium documentation finding is resolved: the package, active plan and canonical
suite contract now explicitly include this production reference-integrity repair
and its compatibility limits. The Roads specification's WEPP Run Assembly
Contract is the durable authority for the generated management behavior.

## Independent source findings

`_build_single_ofe_management_file` currently reduces the plant count to one and
removes the other plant definitions. In `3inslopen.man`, road initial condition
`iresd=2` deliberately names FILL, so the resulting reference exceeds the retained
plant table. The reported native error is consistent with this generated-input
defect. Do not clamp the reference or substitute a different residue to make the
run complete.

`_build_routed_two_ofe_management_file` currently deletes plant 2, renumbers
plant 3 as 2 and rewrites yearly FOREST `itype` from 3 to 2. It leaves the
no-traffic road's `iresd=2` unchanged, so that reference names the retained FOREST
plant instead of original FILL. Existing unit expectations encode this pruning
and must change with the contract. The current FILL/FOREST numerical plant rows
are identical; semantic rebinding alone is not evidence of a measured numerical
difference.

The proposed fix preserves the plant dictionary independently from OFE count:

| Generated profile | Plant definitions | Initial/yearly scenario assignments | Plant references |
| --- | --- | --- | --- |
| Single road OFE | Original ROAD=1, FILL=2, FOREST=3 | Select road and one OFE | Original road `iresd` and `itype` |
| Road/buffer OFEs | Same original three plants | Select road/forest scenarios; remap scenario/OFE assignments as needed | Original road/forest `iresd`; yearly `itype` 1 and 3 |
| Three/four OFEs and replacement arrangements | Same original three plants | Existing scenario selection/order | Original references, including repeated landuse assignments |

Scenario indices and plant indices are separate namespaces. Removing unused
initial/yearly scenarios does not authorize removing plant definitions referenced
by the retained scenarios. The existing arbitrary-OFE builder already preserves
the plant definitions and is not itself evidence for pruning them elsewhere.

## Compatibility and acceptance gates

- Existing management templates remain byte-identical. Current traffic selection
  still chooses `3inslope.man` or `3inslopen.man`; no new fallback template or
  traffic-specific parameter adjustment is introduced.
- Existing projects require fresh preparation/execution to consume the correction.
  Historical results remain historical, and baseline artifacts remain untouched.
  Regenerated two-OFE no-traffic results may change; quantify any difference
  before describing an effect on sediment or water totals.
- Verify both templates with direct parsing of emitted managements: all three
  plant definitions, original residue/plant references, selected initial/yearly
  scenarios, every rotation's assignment count and the requested OFE count/order.
  Text-count assertions alone do not establish reference integrity.
- Retain the failing pilot management and native diagnostic, then execute fresh
  corrected one/two-OFE no-traffic cases. Exercise traffic-present controls and
  three/four-OFE paths to establish that valid working arrangements remain valid.
- Read actual full-project prepared management files and native outputs on an
  isolated source copy. A helper-only test cannot prove the controller consumes
  the corrected file. Refresh matrix/report provenance after the builder changes.

This is a reference-mapping correction with unchanged legacy parameter values,
not experimental reparameterization. Any later proposal to edit those values,
default selections or formulas falls outside this checkpoint and under the
parameterization ADR standard. No new auth, path or locking boundary is proposed;
the existing Roads lifecycle and source-isolation requirements remain applicable.

## Reviewed fingerprints

| Document or source | SHA-256 |
| --- | --- |
| Roads specification.md | `a25c39dd5b0c3ec43e93b74d2c9af265f99ddadd5ed9046663f3ef281d2618e2` |
| roads-validation-suite-contract.md | `090b7d655095acecf2acb66e562be48c46839eb2a99fe80fb0a2ee00c62ac67c` |
| package.md | `5185cb64e58e84562406e4c80f1d3cbccf861311b86dc376d4209bd736229eba` |
| validation_execplan.md | `ce9a38010d9a3c5352b7511ddb12fc8eac556cdbd06dbba2f5bfe8cb67172b8d` |
| 20261023_management_contract_decision.md | `e362a2c8ef0582e78b31f5fddf293260ef6912b158fbd0c7be38bde71f8dc196` |
| roads.py, before implementation | `55aa09763891340757755df228d2dcb8f2c0553e191b9233f304f3782480668e` |
| 3inslope.man | `e2c3781ee9c5dc8333dc0ec16c76053c47872dd944e1a6a430afc7e70663e9a5` |
| 3inslopen.man | `2ba5f7daaf00dca177d765d5f0f9ccb8425d51def78473f4442e89a31bcc39d4` |
