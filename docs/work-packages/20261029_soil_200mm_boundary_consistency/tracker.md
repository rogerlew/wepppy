# Soil boundary consistency tracker

Status: complete locally, 2026-10-29.

Implemented one shared 200 mm boundary normalizer across generated dataset,
ordinary/Disturbed/MOFE, Roads and channel writers. Uploaded topology remains
preserved. Rust owns no input-soil writer; no Rust code or binary changed.

Validation: **12,135 passed, 298 skipped**, no unresolved failures. The exact
native split/unsplit replay produces identical model records and output hashes,
including 17,532 validated daily OFE water-balance records per case.

See [validation](artifacts/validation.md), [writer audit](artifacts/writer-audit.md)
and [review](artifacts/review.md). Existing legacy SIFT/Australian header gaps are
recorded separately; native repair and Roads calibration remain outside this
completed writer-consistency change. No deployment was performed.
