# Implementation review

Reviewed generated-soil publication points, shared helper, upload branch,
source-property preservation, capacity enforcement and native evidence.

- Insertion occurs after existing parameter calculations. The new row copies
  every material token; its depth and OFE count are the only normalized changes.
- The pure helper does no I/O. All changed publication sites compute normalized
  text before opening their destination, including SIFT and channel writers.
- Existing exact boundaries, shallow/zero-layer profiles and zero-channel files
  remain unchanged. Required insertion and already-over-capacity generated files
  both reject an eleventh layer. Disturbed conversion cannot bypass that check.
- Ordinary/MOFE preparation inherits the normalizer. Accepted uploads use the
  existing explicit preservation serializer and the new synthesizer keyword.
- Anisotropy tests retain source hashes and single-read/single-write checks.
  Classification precedes final subdivision; the copied piece retains its assigned
  ratio. No Rust or 500 mm classification change is included.
- Native split/unsplit replay retains the exact binary, climate, management and
  geometry. All model records and all output hashes agree after preparation;
  comments correctly retain different source provenance.
- Roads execution hashing now includes the shared normalizer. Historical results
  and provenance remain unchanged; the staleness record acknowledges reviewed
  source changes explicitly.
- Existing SIFT and Australian header validity limitations are documented in the
  writer audit. Their boundary tests do not claim full native validity.

No new broad exceptions, dependencies, queue wiring, deployment, source-catalog
rewrites or native releases. The line-based broad-exception allowlist moved four
existing SIFT entries by one line because of the new import; no exception policy
was expanded. Documentation lint also found and corrected two pre-existing
relative links in the touched soil README.

The observe-only quality tool completed but lacked `radon` and reported no
changed-file analysis. It does not establish a complexity delta. Manual review
finds a bounded shared parser and small writer call-site changes; existing large
NoDb modules were not restructured. Generated root quality reports were restored
to their original tracked content; diagnostic output is retained in `/tmp`.

Spelling preview suggested changing the country name Chile to Chili; that
incorrect substitution was deliberately rejected.
