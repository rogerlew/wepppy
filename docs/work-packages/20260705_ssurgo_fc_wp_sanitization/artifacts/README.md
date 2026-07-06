# Artifacts

Store production invalidation dry-run and live JSONL transcripts here. Use filenames like:

- `wepp1-deployed-sanitizer-proof-YYYYMMDDTHHMMSSZ.json`
- `wepp1-active-batch-jobs-YYYYMMDDTHHMMSSZ.json`
- `wepp1-invalidation-dry-run-YYYYMMDDTHHMMSSZ.jsonl`
- `wepp1-invalidation-live-YYYYMMDDTHHMMSSZ.jsonl`
- `wepp1-invalidation-postcheck-YYYYMMDDTHHMMSSZ.json`

These files are the rollback/audit source for deployed-code proof, active-job preflight, pre-mutation task timestamp values, live mutation output, and post-mutation read-back status.
