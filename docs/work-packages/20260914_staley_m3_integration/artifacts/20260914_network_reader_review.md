# Bounded delivery and result-reader review

Authority: `2de5ca737`; scientific/runtime ancestors `89d673c38`, `7328a0004`,
`0792c7e59`. No additional service, source refresh or shared soil/cache write.

Independent reviewers: `source_boundary_review` (security/noninterference) and
`source_contract_review` (scientific correctness). Both approve bounded delivery,
offline replay and shared result-mask dispatch after the corrections below.
Production binding/worker/publication remains a separate pending review.

- Parent watchdog enforces native and individual HTTP deadlines even while C
  execution prevents Python signal delivery; controlled blocked-native tests pass.
- FilePath clones share range cache, aggregate budget and latched callback errors.
- Reject malformed SDA tables/collection identities and nonidentity TIFF encoding.
- Preserve request start/failure diagnostics and acquisition-time body hashes.
- Compare initial/final basin, cache and WAL identities without upstream writes.
- Replay regenerates lineage from raw query/response, checks same-byte response
  hashes, pins original decoded TIFF before replay and verifies it afterward.
- Replay records zero network requests and unknown original retrieval timestamp;
  it is not a fresh remote-identity observation. Nonfinite NoData is string-tagged.
- Legacy schema-1 predictors cannot select M3 formulas through an extra label;
  new result masks use fixed paths and replay without original project access.

Validation: four-suite acquisition/transport/results/M3 gate: **81 passed**;
later transport/body-pin gate: **26 passed**. Same-length body tampering and
catalog relabeling were independently rejected. Existing legacy results pass.
Production/full/live acceptance counts must be recorded separately.

## Live source evidence

Executed in the development `weppcloud` container as uid 1000/gid 993. Initial
receipt: `postfire_debris_flow/source_preparation/b2824aee990b4ff98eee0fc1b8c82cc4/receipt.json`
within `/wc1/runs/ad/addicted-reservist`; SHA-256
`3844f2e29dfee46a5a6bb5d3f36e278dcb1a7a53ebd40fbc89b814d93250fcd4`.

SDA identified SSURGO keys 53947/53958 (AZ683, current survey version 21),
and eight STATSGO keys (US, version 3). Cached horizon vintage stays unknown.
The retained raw response hash is
`a7994366cdc50f868d96f117d0ca25ebf24d7e5ee8af29223c106487a024433c`.
The USGS object was 352,422,285 bytes; eight identity-checked requests included
six 64-KiB ranges, totaling **393,216 received bytes**. Native decode succeeded;
receipt serialization failed on the original NaN NoData declaration.

The failed acquisition remains unchanged and browsable. Generic offline replay
successfully produced fresh receipt
`postfire_debris_flow/source_preparation/d0a0f389b467467ab56d69b1b2b14701/receipt.json`.
No second network acquisition or activation occurred at this checkpoint.

Source classification follows the NRCS
[SSURGO/STATSGO query guidance](https://sdmdataaccess.nrcs.usda.gov/documents/DiscriminatingBetweenSSURGOAndSTATSGO.pdf)
and [survey relationships](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf).
The installed Rasterio adapter protocol was checked against its
[1.3.10 implementation](https://raw.githubusercontent.com/rasterio/rasterio/1.3.10/rasterio/_filepath.pyx).
