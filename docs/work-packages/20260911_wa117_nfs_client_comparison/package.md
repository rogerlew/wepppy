# WA-117 NFS client comparison

**Status**: Closed (2026-09-11)
**Timezone**: UTC

## Overview

This package tests whether Dell-to-HPC NFS metadata or read latency explains
the historical WA-117 hillslope-interchange regression relative to wepp1 and
the legacy NAS. It performs read-only, normalized scans of the six real input
families before any interchange concurrency change.

## Scope and complexity budget

Included work is read-only inventory, stat/open-close timing, two full reads,
mount-stat deltas, analysis, and documentation. Production run data, mounts,
caches, services, queues, binaries, and configuration are not changed.

- **Existing mechanisms reused**: existing WA-117 outputs, Kubernetes exec,
  SSH, Python standard library, and Linux mount statistics.
- **New mechanisms permitted**: one package-owned read-only probe.
- **Simplest plausible change tested first**: direct measurement of the two
  native client paths.
- **Real acceptance condition**: normalized metadata and first/warm read
  evidence sufficient to retain or reject NFS latency as the leading cause.
- **Evidence required before escalation**: unexplained path disadvantage after
  normalizing file and byte counts.
- **Explicitly prohibited expansion**: cache dropping, mount/storage changes,
  production-data writes, new services, or interchange implementation changes.

## Security and operational impact

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- The probe reads existing model output and writes only `/tmp` result files.
  It prints no credentials or secrets.
- The bounded scan adds NFS read load but cannot affect control-plane quorum or
  storage availability. Stop conditions were NFS errors, worker workload
  collision, or unexpected writes.

## Success criteria

- [x] File and byte counts are recorded for both WA-117 corpora.
- [x] Metadata, first-read, and repeated-read timings are captured.
- [x] Client CPU time and NFS mount deltas distinguish CPU from I/O/cache.
- [x] The original NFS-latency hypothesis is dispositioned.
- [x] Temporary remote files are removed and durable results are documented.

## Closure notes

The Dell path was faster for metadata and first reads; HPC NFS latency is not
the cause of the historical 2.2x interchange regression. The legacy host's
large page cache retained the whole corpus, while the 12 GiB Dell worker cgroup
could not. See [results](artifacts/results.md).
