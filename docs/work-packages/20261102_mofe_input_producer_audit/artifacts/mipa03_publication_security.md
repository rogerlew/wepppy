# MIPA-03 final publication security review

Reviewer: `mipa03_contract_security`, 2026-11-03 UTC.
Disposition: **PASS; approved for delivery of the exact PDF and manifest below
through the existing static report route.** No unresolved medium/high security
finding remains. This is an independent AI engineering review, not human or
institutional scientific approval.

## Exact approved attachments

| Attachment | SHA-256 |
| --- | --- |
| `wepp_261029_release-notes-r7.pdf` | `0cdd7c74ac7c2277a144e27d9a8053578eb6e63b6819b857bd45691b9fe69b3c` |
| `publication-manifest-r7.json` | `7c7d80526573e08148590a5196dbd0ff4990d55426d0f16c25a5582e203ab1ac` |

Reviewed native authoring directory:
`docs/release-notes/wepp_261029/`. The PDF is the unchanged four-page,
177,826-byte artifact independently approved by correctness and visual QA.
`pdfinfo` reports no JavaScript or forms; `pdfdetach -list` reports zero embedded
files. Extracted text contains no source listing, private filesystem paths,
credentials or private project records. The public manifest contains identities,
bounded validation results and limitations; it exposes neither the private
evidence register's paths nor its underlying logs or project data.

The public attachment allowlist is exactly the two files above. The intended PDF
path is
`/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r7.pdf`.
No authoring TeX, source freeze, evidence register, source archive, run artifact
or log is approved as a public attachment. Earlier static revisions 1–6 remain
present, and each existing PDF independently matches its issued manifest.

## Independent provenance verification

Rehashed both actual native and vendored binaries and sidecars. Their bytes agree,
and their hashes equal the manifest. Both sidecars identify build source
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`. The separately identified model port
and historical reference are consistent with the approved PDF and prior reviews.

Verified all **500 frozen source files** against both current files and Git blobs
at the declared build commit; verified all authoring hashes, all **130 retained
evidence files**, and all **five named review receipts**. The bound source-freeze
SHA-256 is `410ebd9c33291881d5ede896c16e818ac01df1bf8c50c982909956dca3bd39d4`;
evidence-register SHA-256 is
`37ffc0431df28724f66f9723dc0a81d51b8e3c14afb6164df0f9b73cd1ee8a61`.
This review is detached from that frozen manifest/register to avoid circular
approval hashes. Changing either approved attachment requires renewed binding.

Independent receipt:
`/wc1/holdouts/mipa-native-r7-20261103/publication-security-v1/receipt.json`,
SHA-256 `4435e7082f254a6b485ad9d434f8b5e1744372e22ee68141d65060ecf5b84422`.
It also binds all six earlier public PDF/manifest pairs before delivery.

## Terminal gates and disclosure

The manifest preserves the segmented broad Python history: initial fixture
failure, three-test fixture rerun, later catalog failure, 24-test unchanged-code
catalog rerun, and final continuation **206 passed, one skipped, 13,001
deselected**. The catalog's only return without `rows` is advisory-lock busy;
its transient-contention disposition is supported by the source and successful
rerun. The two continuation selections retain the same complete ordered 13,207
test collection and resume at their respective failed nodes. No skipped
continuation range or uninterrupted full-suite success is claimed; overlapping
counts are explicitly not summed.

Reviewed configured-artifact QA closes the previously pending observer probes:
identical final binary, inputs and service identity, correct soil/cover bindings,
and 24 byte-identical ordinary outputs. The successful local-disk diagnostic
replay is distinguished from the retained NFS trace timeout and from the complete
normal workflow that passed on NFS. The final disclosure preserves synthetic-data,
optional-null-storage, inherited graphics serialization and historical Roads
limitations. It neither retunes Anurag's reference science nor implies his review,
field validity, historical-binary equivalence or full conservation proof.

## Delivery boundary

The handoff explicitly authorizes revision-supplement publication. The parent may
copy only these exact approved bytes to the existing static route, preserving
earlier issued files. After copying, verify delivered HTTP status, MIME and SHA-256
for both attachments and recheck earlier-file preservation. HTTP delivery has not
yet been performed by this reviewer and remains the mechanical closeout gate.
No deployment, executable-default switch, new public route, source publication,
upload expansion, runtime-identity change or scientific change is authorized.
This reviewer changed only review/evidence artifacts and did not mutate the
manifest, PDF, production source or binaries.
