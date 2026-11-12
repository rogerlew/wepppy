# Native ownership review: coverage is not yet complete

The independent read-only review of parser image `sha256:05f4d047b5460e0a867876aeff6af27b5515afab1a54b31b6b4a5df6d31931a9`
partitions every scanner-unknown native file. All 2,105 archive hashes agree with
the direct inventory; 1,201 hashes are unique. No RECORD hash mismatch was found.

| Ownership evidence | Paths | Unique hashes |
|---|---:|---:|
| Python RECORD or identical-byte build aliases | 1,803 | 924 |
| CPython base layer and version headers | 79 | 79 |
| Owned binaries requiring build provenance | 221 | 196 |
| Other unresolved components | 2 | 2 |

The two unresolved components are the separately installed DuckDB spatial
extension and a netifaces build probe. The review does not approve them or
silently exclude build/cache files.

Of the Python-owned paths, 243 paths/120 hashes are explicit bundled native
libraries or solvers. Other extensions also embed static dependencies, including
cryptography, lxml, PyNaCl, DuckDB and Matplotlib. RECORD attribution therefore
does not establish complete advisory coverage. Embedded SBOMs help but are
incomplete: Pillow's names Pillow and libXau while omitting Brotli and most codecs.

Eighty-eight cache-only hashes have no installed counterpart; these include
different NumPy, Cython and CFFI versions. They cannot inherit coverage from the
installed package. CPython attribution references the identified Python 3.12.16
artifact and retains its eight current advisory rows.

Retained private packet:
`evidence/parser-batch-20261112/qa-native-coverage-20261112/review-packet.json`.
SHA-256: `b8528caf3042675852fdf2fbc3aae54cef7cc060d726d0b292bdc50604f0aec7`.
Its itemized `coverage-proposals.json` contains every hash and alias, with no
fabricated owner/approver. Manifest SHA-256:
`e15825c558a19c41060c9c58f6d7f10d073044c96620da19ebe46be33b544ca2`.

M1 still needs supplemental component/version/build evidence, advisory evaluation
and reviewed coverage records. None of these ownership proposals is an accepted
risk or M4 clearance. Native repairs must preserve the existing codec, font,
geospatial and model workflows; disabling features is not an authorized shortcut.
