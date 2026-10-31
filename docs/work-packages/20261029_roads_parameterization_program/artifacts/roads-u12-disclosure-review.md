# Roads U12 research disclosure review

Disposition: **do not commit/push the entire untracked artifact directory as-is.**
One patch and seven mixed-origin source-instrumentation scripts should remain in
the private native evidence tree in their present form. The four proposed ADRs,
scientific prose, numerical observations, original analysis/plot code and reviewed
figures are not prohibited by the legacy-source hold. This is a disclosure review,
not scientific acceptance, release promotion or authorization to publish sources.
No repository files were edited by this review; only `/tmp` review artifacts were
written. No commit, push, model execution or publication was performed.

## Scope and authority

Reviewed the new untracked files under
`docs/work-packages/20261029_roads_parameterization_program/artifacts/` and
ADR-0121 through ADR-0124 in `/workdir/wepppy`, plus the tracked one-line status
edit to `depend-root-ablation-r3-plan.md`. Inventory initially had 115 files;
`param-denominator-sign.pdf` and `review_param_u12_cedar.py` appeared during the
review and were also inspected. Final Cedar/source-verification JSON receipts
were added and checked before handoff: **119 files total** (29 Markdown,
40 Python, 43 JSON, five figures, one patch, one input archive). New files created after
this snapshot require their own check. This review does not reopen earlier
committed artifacts or independently establish the numerical claims.

Applicable policy:
`/workdir/wepp-forest-release-20261009/docs/release-notes/AUTHORING.md`,
“What May Be Described or Shown”:

- Detailed original prose, equations, diagrams, variable roles, branching and
  mathematical explanations are explicitly allowed.
- Our original stubs and implementation excerpts are allowed, with author/origin,
  version, purpose, production relationship and reviewed-disclosure provenance.
- “Do not reproduce raw legacy routines, source-tree excerpts, patch hunks with
  legacy context, complete modified legacy files or source attachments” without
  specific documented authorization.
- Renaming or translating a routine does not itself establish independent
  authorship. Generic release approval does not override the source hold.

The user's authorization to re-release undeployed `wepp_261029` after independent
gates does not authorize raw legacy context distribution. This is an application
of the recorded publication policy, not a legal determination that every short
statement is individually copyright-protected. No extra permission is needed to
retain the restricted artifacts privately and publish the allowed explanations.

## Concrete hold list: keep native/private as-is

All paths below are relative to the Roads program's `artifacts/` directory.
Line locations identify the current inspected files; no legacy listing is
reproduced in this review.

| Artifact | Evidence | Required disposition |
| --- | --- | --- |
| `depend-g1.patch` | Unified diff, including original DEPEND declarations, comments, Newton update and surrounding control flow, plus newly authored changes; hunks start at lines 5, 15, 45 and 57. | Retain the complete patch in private `wepp-forest` evidence. A public repair narrative and original standalone helper with explicit provenance can replace its public role; do not merely strip diff headers. |
| `observe_param_continuity_u11.py` | Lines 10–19 and 35 embed literal PARAM declarations, branch conditions, shear/transport expressions and assignments as insertion markers. These match revision-3 native source, mixed with original observer statements. | Keep the complete instrumenter native/private; publish numerical operand receipts and independently written descriptions. |
| `observe_particle_capacity_u11.py` | Lines 28, 58–60 and 81–82 contain native ENRICH/DEPOS/PARAM insertion context, including the rill clamp and coefficient-denominator assignment. | Retain native/private; the added capacity observer may be separately attributed/reviewed as original code if needed. |
| `observe_particle_closure.py` | Lines 17–28 include source insertion context and the literal ENRICH rill-clamp statement. | Retain native/private; original trace records and output comparisons are separately eligible. |
| `observe_erod_intervals.py` | Lines 9–10 and 20 embed native source anchors/declaration context in the script that modifies copied EROD/RUNGE units. | Retain native/private as a mixed-origin source instrumenter; do not treat its `.py` extension as source-free. |
| `observe_fraction_arithmetic_u11.py` | Lines 16–17, 34–35 and 43 carry native insertion anchors/control context around newly written arithmetic observations. | Retain native/private; preserve the independent certificate and numerical observations separately. |
| `param_sign_ablation.py` | Line 7 embeds the former PARAM branch verbatim; lines 8–11 contain the replacement, and lines 16–25 assemble whole modified source files. | Keep the source-rewriting script native/private as-is. Explain the sign rule in ADR/prose; an original isolated demonstrator can be reviewed separately. |
| `review_route_fixture.py` | Lines 57–58 embed DEPOS entry context and a three-statement ROUTE sequence to insert logging, alongside a newly authored fixture driver. | Retain the mixed script native/private. The driver may be separated and published with explicit provenance; it is not necessary to suppress the driver solely because it calls native interfaces. |

The seven Python determinations are based on exact native-source anchor matches,
not just filenames, routine names or the presence of Fortran syntax. Several
anchors are short/trivial, but distributing these mixed source-rewriting files
unchanged does not meet the policy's explicit source-excerpt hold. The smallest
clear remedy is to keep them beside their native fixtures and publish only their
hashes, declared purpose and source-free receipts.

## Eligible material and boundaries

**ADRs 0121–0124:** no raw routine listings or patch hunks found. They describe
root bracketing, interval support, inflow boundary conditions and sign/rounding
rules using original prose and equations. That is expressly allowed. Retain their
proposed/experimental status until the actual final decision is recorded. This
review does not waive their scientific or ADR acceptance gates.

**All 43 inspected JSON files:** numerical inputs/results, observations, audit
flags, hashes, paths, archive inventories and provenance. Recursive string checks
found no embedded source patch, routine body or compiler diagnostic reproducing
source lines. Source hashes and paths to restricted evidence are not copies of
that source. These are eligible research evidence; public release reports should
still omit unnecessary private filesystem paths and must not upload the source
archives merely because a receipt names them.

**Scientific Markdown:** no raw legacy listings found in the 29 new files. The
only fenced blocks inspected were an original verification command and a
mathematical error equation. Algorithm-level detail and inline formulas are
allowed. Draft release notes are drafts, not an accepted release statement.
The one-line tracked plan status update introduces no disclosure issue.

**Remaining 33 Python files:** original analyzers, certificates, probes, plotting,
build orchestration and replay wrappers; no substantive verbatim legacy-source
context was identified outside the hold list. Examples include
`certify_fraction_arithmetic_u11.py`, `audit_param_terminal_matrix_u12.py`,
`verify_param_terminal_quadrature_u12.py`, `review_param_u12_cedar.py`,
`build_erod_candidate.py` and `build_erod_candidate_u3_u5.py`. Reading/copying
restricted source from an existing private checkout during an internal build
is not the same as embedding it in the committed script. Their generated source
copies, object files, executables and source-containing archives must remain in
the private output/native retention tree.

The mathematical certificate is an original verifier/replay of observed
binary32 operations, not a public native implementation listing. Describe that
relationship accurately rather than claiming it is clean-room model source.
`review_route_fixture_extra.py` and the small route probes contain original test
setup/observer code; a generic RETURN anchor alone was not treated as a native
algorithm listing. If published, record their authorship and native-fixture
dependencies. A compact companion provenance register can cover the original
scripts/stubs: author (Codex/actual contributor), origin/version, purpose,
observer/test versus shipped status, and disclosure disposition. Do not imply
that authorship of an added observer grants rights to its surrounding legacy unit.

**Figures:** inspected PNG renderings and SVG metadata/content for
`depend-bounded-root` and `param-denominator-sign`; also inspected the new PARAM
PDF metadata/text/attachment list. These are independently generated numerical
illustrations, not source screenshots. No raw source, private path, script
attachment or credential was found. The PDF has one page, no JavaScript and no
embedded files. Plot helpers are original mathematical/numerical code; retain
reference-data provenance and the stated distinction between illustration and
model prediction. Public eligibility is not validation of a final release claim.

**`particle-closure-inputs.tar.gz`:** this is an input capsule, not a source
archive. Inspected all 24 members: two copies of twelve run inputs (`.slp`,
`.sol`, `.man`, `.cli`, `.run`, and auxiliary `.txt`/`.inp` files). No native
`.for`/`.inc` source, executable, object file, source patch, unsafe archive link
or nested bundle is present. Every member hash matches
`particle-closure-fixture.json`. Management content exactly matches tracked
FSWEPP2 `api/db/wepproad/managements/3outunr.man`; the soil identifies WEPPcloud
and SSURGO, and climate identifies CLIGEN/McMinnville. Preserve those origins
and the benchmark-generated lineage. The legacy-source hold does **not** itself
prohibit this capsule; it is not blanket clearance for unrelated private run
inputs or third-party assets. This capsule and its receipt can remain in the
public research set under the existing benchmark fixture provenance.

No credential or private-key patterns were found in the inspected text/figure
metadata. Local `/workdir/...` research paths are reproducibility pointers, not
credentials. I did not infer authorization to publish private run bundles from
the presence of such paths.

## Minimal remediation and commit procedure

1. Retain the eight held files, byte-for-byte with hashes, in a private native
   work-package/artifact location. Do not delete the only reproduction evidence.
   Replace public links with a native-relative receipt and the public mechanism
   explanation. No history rewrite or remote deletion is requested by this review.
2. Fix dependent commands/imports deliberately. In particular
   `observe_param_sign_u12.py` imports `param_sign_ablation`; moving its dependency
   requires an explicit native helper path or moving the wrapper with it. Other
   replay/certificate runners may rely on private observers without themselves
   containing restricted source. Do not leave a public “reproducible” command that
   silently depends on a removed sibling. No fallback that masks missing evidence.
3. Add the concise original-code provenance register. For published equivalent
   test code, record its source relationship and limitations; for any actual
   excerpt retain the specific publication basis. Do not rewrite the numerical
   results to make this separation easier.
4. Stage an explicit reviewed allowlist; do not `git add` the whole artifact
   directory. Inspect the actual staged diff and every new archive. Ensure the
   eight held files and copied `out/.../src` trees are absent from the public
   commit. Keep the negative scientific results and unresolved gates visible.
5. Recheck any files added after this inventory. Scientific/native release gates,
   final release report review, binary promotion and production deployment remain
   independent actions; this review approves none of those actions.

## Adjacent pre-existing issue, outside this change

`artifacts/proposed-negative-fin-fix.patch` is already tracked and contains a
legacy-source patch. Its existence is not authorization or precedent for the new
patch. Review its publication history separately if needed; this task neither
changes it nor assumes that deleting a working-tree file would remove published
history. No other earlier artifact receives retroactive approval here.

## Verification performed

- Enumerated untracked scope and inspected all four ADRs; checked the tracked plan
  delta and source-related Python literals/markers against native revision-3 units.
- Parsed all JSON recursively for embedded source/patch/compiler excerpts;
  inspected Markdown code blocks and source-oriented scripts, including the
  newly appearing Cedar verifier.
- Read every input archive member and verified all 24 hashes; matched management
  data to its existing tracked FSWEPP2 asset.
- Visually inspected both numerical figures; inspected SVG metadata and PDF
  properties/text/attachments. No tool-generated source or model execution was
  performed by this review.

The scope inventory and exact held-file/ADR/input hashes below identify the
reviewed snapshot. Further content edits require rechecking the affected files.

### Snapshot hashes

| Artifact | SHA256 |
| --- | --- |
| `ADR-0121-depend-bounded-root-search.md` | `b6fc39adf5ed921284fefac2625bb995c49ca71844717aac18e03fb67fc673ab` |
| `ADR-0122-erod-subgrid-interval-support.md` | `9befdc0c78229b3109ef29c0d6f7520a6faa31f19435fdcb2c8de3c342785889` |
| `ADR-0123-roads-nonzero-inflow-sediment-boundary.md` | `064360fee3e292c68e1d2ef6451793e45e13c83af864bd31baa466fa012d88e5` |
| `ADR-0124-param-rounded-continuity-denominator-sign.md` | `844eabdff2563a11f92463bff8859028faa98f449cdd723fe1e036c12c0fbb32` |
| `depend-g1.patch` | `38edb4ccf9a8f90e82f3d7aa1fb5dea4007310b0c65673d150a445eb850a4ae1` |
| `observe_erod_intervals.py` | `113802c3b74260a302585e11190137f1ec0943e96b7930e3d5901a1a07a259c2` |
| `observe_fraction_arithmetic_u11.py` | `9c78388fbd01d96390e562d0ee6541e29bf50434601b33bf26d8c5a8780a6b91` |
| `observe_param_continuity_u11.py` | `31549af22f90c8fddeedbd0a0248cd00e7541287a866affa3eafb236b704449a` |
| `observe_particle_capacity_u11.py` | `c3ed6454a66ac57681bca61727e07ef5ed069da7e477b8697a7a5fee264fc3be` |
| `observe_particle_closure.py` | `807d24a662ab924f3148b17a99437a4bf80d940961bc069b126d8f28bea4599f` |
| `param_sign_ablation.py` | `ceea4ffc8fcc3049deb83ca00b05f262256ab33f54f576e8d821e3e00de81837` |
| `particle-closure-inputs.tar.gz` | `5ab5d792182b471d537379859fca7eed4d2e7bb892053acd6d48f4cabd6b32c8` |
| `review_route_fixture.py` | `c01bc5aec50c5f1c923a3cf70f550900a9138f9921901166bf8e662ab1f1abef` |

Inventory: `/tmp/roads-u12-disclosure-inventory.json`, SHA256 `32f4abadb1769f7ef4997eea0bd85de0d95ca63904d96f7fb4b46395a03b8247`.
