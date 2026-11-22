# Publication review: revision 2

Matched Linux pair, source `ba9f2ad91b5165d5cd2954bd64b5df608798541e`.
Human author: Roger Lew, with Codex authoring assistance. No institutional
endorsement or human scientific peer-review claim.

## Owner authorization

The owner explicitly states that the original `wepp_261029` was not deployed
and authorizes same-name replacement and updating the existing release notes.
Revision 1 remains immutable history. The earlier statement that the owner
read and accepted the notes applies to revision 1, not these new sections.
Production deployment and project-default changes are outside this report.

## Independent review scope

- Scientific: `/root/scientific_review`, 2026-10-30, accepts final matched U10.
  Native work-package artifact `U10-Yalin-independent-scientific-review.md`,
  SHA256 `7a239ac7ed5f50f848296b0219bd218f61bcd1a263d136842909c2b81767359b`;
  binding incident receipt `review-U10-final-scientific-acceptance.json`.
- Implementation: `/root/implementation_review` verified final native gates,
  Roads input/output inventories, Disturbed outputs and frozen sidecars.
  Final PDF and manifest accepted in `evidence/independent-review-r2.md`.
- Disclosure: `/root/implementation_review` independently reviewed this final
  artifact. `/root/publication_review` authored revision 2 and is not its
  independent disclosure reviewer. Its earlier approval applies only to r1.

## Artifact checks and publication boundary

Compiled twice with shell escape disabled; 14 pages, six figures, selectable
text, Roger Lew author metadata, no embedded files or JavaScript, no undefined
references or overfull warnings. Source freeze includes every rendered figure,
main TeX with inline bibliography, source coverage and numerical evidence hashes.
Only the approved PDF and public manifest may be copied publicly; legacy source,
patches, raw input bundles and internal evidence remain excluded.

Final PDF SHA256: `c94db60e60ccd561a96dcdda89bad8bed209c32a783d3e699beb0e72485ddf44`.
Manifest: `publication-manifest-r2.json`. Independent final implementation/disclosure review accepts the exact PDF and
permits only review/status/publication fields in the manifest to be finalized.
The final approved public manifest SHA256 is
`28c3efb859ae339bfcf3d598b36f2a885486d219f62ddd7a9387d3310a93baf8`.
The approved PDF and manifest were copied to WEPPpy's existing static release
path and verified through the local development Caddy host route with forwarded
HTTPS. Both downloads return HTTP 200, correct `application/pdf` and
`application/json` content types, and the exact approved SHA256 values above.
The rendered model page returns HTTP 200 and links revision 2 and preserved
revision 1 with the material sediment-change disclosure. Receipt: WEPPpy
`docs/work-packages/20261030_wepp_261029_rerelease/artifacts/report-download-check.json`,
SHA256 `bf65bc66e63dbb1dbfd8a4162b7f3034569a4e9a8da417a5af44d8060a58ff13`.
This establishes local static publication and HTTP behavior, not production
deployment. The approved public manifest is immutable; its issue-time pending
HTTP gate is closed by this retained receipt rather than rewriting served bytes.
