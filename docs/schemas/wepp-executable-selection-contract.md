# WEPP executable capabilities and selection (CBEXEC-01)

Status: operator-authorized 2026-10-12; independent review and implementation conformance pending.

## Purpose and authority

Users must be able to select newly installed WEPP releases for existing Config
Builder projects without recreating the project or refreshing its config.
Executable availability is deployment state, not a creation-time project
restriction. This contract amends the binary member only of project-owned
capability authority; all non-binary axes, geometry, authorization, read-only,
CSRF and NoDb locking rules remain authoritative. No default or saved executable
is automatically changed. `wepp_260803` remains the Builder default.

## Release declarations

The existing `wepp-binary-release-metadata-v1` sidecar `features` object gains
strict boolean `mofe_supported` and `single_user_defined_inputs_supported`
members. The second declares support for the native formats and limits in the
Single User-Defined input contract, not arbitrary uploaded files. Each feature
must be true in both runner-resolved watershed and hillslope sidecars to admit
a new selection requiring it. Missing sidecars or missing members mean unknown
support, never date/name inference. False means unsupported. Non-boolean
members, mismatched paired declarations, malformed metadata or a declaration
whose SHA-256 does not match its executable fail explicitly. Sidecars bind
the resolved binary name and agree on release tag and source repository, branch
and commit; positive declarations require that provenance. Single-OFE
ordinary selection does not require either optional feature.

The sidecar generator on wepp-forest's default branch owns declarations. Its
refresh mode must verify existing name, role, release, source identity and
binary hash before changing capability fields. Preserve build time, all
existing provenance, PASS-format declarations and validation records. Remint
both roles of 260803 and261010, then vendor identical sidecars. Executable
bytes are unchanged. Declare upload-reader support only after equivalent
native input validation. Future releases declare their capabilities during
minting; no WEPPpy release-name allowlist is permitted.

## Builder and existing projects

Use the complete unique `get_linux_wepp_bin_opts()` provider output for
ordinary single-OFE choices. Multiple OFE requires WBT and declared MOFE support.
Checked single-file upload projects additionally require declared input-reader
support. Keep their existing feature exclusions, native source validation,
maximum OFE count and buffer prohibition. Unsupported selections produce
field-specific errors; do not silently replace the requested executable.

The Builder registry revision must include effective sidecar capabilities as
well as existing role-byte identities. A metadata change between description
and creation therefore triggers the existing stale-schema conflict. New stored
graphs record actual compatible tuples; historical graphs with only the
260803 MOFE tuple remain readable without consulting live sidecars. Stored
graph validation still rejects invalid axes, references, defaults, duplicate
tuples and unsupported backend/representation pairs. It must not require one
release name as the only MOFE tuple.

If no installed binary declares MOFE support, ordinary single-OFE creation and
selection remain available. The graph retains its supported geometry axes but
has zero MOFE executable tuples, so the UI cannot offer MOFE for that provider
state. Only this optional representation may lack an executable tuple; binary
and backend participation and all other closure checks remain required.
Structural identity describes geometry independently of currently installed
binary support: TOPAZ/single, WBT/single and WBT/multiple where the corresponding
axes exist. This preserves historical accepted structural identities and avoids
turning missing optional metadata into a global Builder outage.

Existing flattened schema-v1/v2/v3 projects use current installed compatible
binary choices in the run page and paired submission/schema surfaces. Preserve
their stored backend/representation authorization. Do not regenerate project
config, update its manifest or migrate other capabilities merely to select an
executable. The selected executable persists through the existing Wepp lock and
reload contract and is used by preparation and execution. Schema enums and
operation metadata must describe the same effective binary choices as the UI
and submission validator; their freshness identity must reflect live binary
capabilities. Model-authority metadata retains the complete stored-authorized
geometry with live compatible tuples, while the executable field enum is
filtered for the current geometry. `executable_revision` identifies live role
bytes and declarations separately from the stored `provider_revision`.

An omitted field preserves saved selection. A previously saved binary no longer
available or lacking a newly required declaration remains visible as current
legacy state; unchanged legacy submissions retain established behavior. It
must not be advertised as an eligible new choice, and another executable must
never be substituted silently. Explicit changes must be exact installed
provider IDs and satisfy required features before any NoDb mutation or enqueue.
Use existing current-value and disabled-option metadata to distinguish saved
legacy display from eligible choice enums; do not put a disabled current value
back into the eligible enum merely to render it.
Reject arbitrary paths and unknown IDs. Legacy non-flattened projects retain
their existing selection behavior unless the user changes to a new executable
on a capability-governed upload path.

## Evidence and limits

Cover absent/empty declarations, true/false, malformed values, mismatched roles,
stale hashes, sidecar changes during description/create, old graphs, saved legacy
choices and hostile IDs. Exercise real save/reload and prepared-run executable
selection; retain current binary identity and actual generated MOFE outputs.
Preserve source soil/management inputs. Capability support does not establish
numerical stability for every project. Changing releases requires matching
hillslope and watershed outputs under the existing runner/PASS contracts.
