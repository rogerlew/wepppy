# Tracker – WA-117 NFS client comparison

## Quick status

**Timezone**: UTC  
**Started**: 2026-09-11 11:44 UTC  
**Current phase**: Closed  
**Last updated**: 2026-09-11 12:00 UTC  
**Security impact**: `low`

## Completed work

- [x] Verified both native WA-117 paths and mount identities.
- [x] Inventoried all six interchange source families.
- [x] Ran simultaneous read-only probes from Dell and wepp1.
- [x] Captured pre/post mount statistics and host memory context.
- [x] Removed probe files and documented conclusions.

## Decision log

- **2026-09-11 11:44 UTC** – Preserve serial execution and test storage first.
  Concurrency could conceal rather than explain the historical difference.
- **2026-09-11 12:00 UTC** – Reject generic Dell-to-HPC metadata/read latency
  as the leading cause. Retain limited client page-cache capacity as the
  evidence-backed explanation to test when optimizing native interchange.

## Result

The two corpora differed by only 1.7% in bytes. Dell metadata and first-read
performance were better, but wepp1's second pass was 11.5x faster because its
251 GiB host retained the complete corpus. No errors or mutations occurred.
