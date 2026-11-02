# General native comparator identity map

Date: 2026-11-01. Read-only source, provenance, and ELF inspection. No builds or model invocations.

## Smallest usable general comparator

The existing `/workdir/wepp-forest-release-20261009/src/wepp` hashes to `2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48`. This exactly matches the approved release binary in `docs/release-notes/wepp_261029/publication-manifest-r4.json` in that native repository. The manifest binds model source identity `b01a739957bef5aacf35b4a89bc13eddc9d94804` and records completed native, hillslope, Roads, downstream, and host gates. This is retained provenance, not a new claim of gate execution by this reviewer.

The inspected canonical HEAD is `c58ad035cd6cb38e74fc4dfe5ba4efa1ddc39a76`. `git diff b01a739957bef5aacf35b4a89bc13eddc9d94804 HEAD -- src` is empty, and `git status --short src` is empty. Thus the later canonical revision does not introduce different source bytes under `src` from the manifest's source revision. The existing executable has debug information and a `frostn_` symbol at `0x4aaea0`; `nm` reports no `rrcstart_` symbol. Its ELF build ID is `5be2dd6e9f4fa5f10078aae696d34caeda1547f8`.

This supports using the existing released binary as a new general-native comparator without rebuilding. Freeze its runtime-library identities, address lookup, input inventories, and observed output schema in a new declaration before execution. Do not reuse the research binary's frost address or assume identical file headers without checking. This map itself grants no execution approval.

## Relationship to the Roads research binary

Research executable `17fbcf4540e7d7a29980b4eccb0851652689160960663ae8140ed3cddb377b72` lives at `out/frozen-water-flux-20261101/campaign-v2/build/src/wepp`. A direct source comparison against canonical identifies differences in 20 Fortran files and the extra `fh_state.inc`. The differences span allocation, hydraulic, roughness, stock, frozen-history, and flux observation hooks. A mechanical unified-diff inventory found no removed active canonical statements except relocation of the final `frwatc` routine boundary; the research additions nevertheless include executable controls and therefore are not universally inert.

The restrictive roughness observer requires three OFEs, continuous hillslope mode, native land use 1, at least two soil layers, no configured irrigation, and no buffer tillage; initialization and management anchors are also checked. Its `roughness-control.txt` requires target 3 and mode 0 or 1. Mode 1 replaces buffer roughness. Mode 0 leaves that replacement inactive but still enforces every context guard. The canonical source has neither this control-file requirement nor these experimental context restrictions.

The accepted frozen-water history and flux investigations explicitly describe observation-only work and unchanged canonical behavior. Their accepted fluxes are physical quantities being observed, not approved source repairs. Their reviews demonstrate bounded observation/parity readback, not broad physical closure. Consequently there is no established frozen-water physics repair in research `17f` that must be transplanted merely to use canonical for F03. Shared preexisting canonical water behavior is retained; the research additions should not be treated as a general-purpose release.

The current A03 interception-allocation candidate is a separate new source/build lane under `out/rock-water-development-20261101/A03-*`, assembled from the experimental base. Its authored allocation implementation is absent from both the released canonical comparator and the older `17f` observer. A local successful candidate result does not make it an accepted general fix, and this read-only mapping does not adjudicate A03 admission.

## Recommended identity lanes

| Lane | Identity and purpose | Applicability |
| --- | --- | --- |
| Historical | Verified `wepp2010`, SHA `a12976166deb2b2d7c9adc0e0f23bac24d54057031a5072b4bb0a176c7c730b8` | Existing legacy eRMiT and Roads observations; historical behavior only |
| General release | Existing `wepp_261029` / canonical source-equivalent binary `2a3f9f2b…` | F03 one-OFE eRMiT comparator and general baseline panels, with explicit per-fixture validation |
| Roads observer | Frozen `17fbcf45…` research build | Retain existing three-OFE evidence; do not generalize its instrumentation to other geometry |
| Allocation candidate | Separately declared A03 source/build | Candidate evaluation against the appropriate matched baseline; no implicit production admission |

For F03, retain the exact two-year eRMiT physical fixture and historical frost sidecar, use the general-release comparator plain/debug, and reuse successful legacy F02 evidence. Do not change geometry or land use to accommodate a Roads observer. The modern calendar guard still applies; the original nonconsecutive ten-year climate remains a separate compatibility question.

For a future general retention-consumer panel, start from the general release and add only narrowly required observation hooks or a separately admitted allocation repair, each as an explicit source delta with matched baseline/candidate identities. Reusing the entire Roads instrumentation stack would import unsupported geometry and irrigation constraints. Policy causality requires comparing the relevant source changes; a legacy-versus-modern result by itself establishes version compatibility differences, not exclusive attribution to frost.
