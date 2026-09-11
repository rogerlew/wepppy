# WA-117 NFS client comparison results

## Inputs

| Client path | Files | Bytes | PASS | EBE | ELEMENT | LOSS | SOIL | WAT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Dell to HPC | 7,146 | 21,494,239,187 | 1,487,896,266 | 96,294,584 | 1,481,977,299 | 15,886,506 | 5,631,642,621 | 12,780,541,911 |
| wepp1 to legacy | 7,140 | 21,131,029,273 | 1,456,193,344 | 84,945,869 | 1,370,202,782 | 15,766,998 | 5,567,938,530 | 12,635,981,750 |

## Timings

| Phase | Dell wall | Dell user/system | wepp1 wall | wepp1 user/system | Legacy/Dell |
| --- | ---: | ---: | ---: | ---: | ---: |
| Stat | 2.375 s | 0.069/0.294 s | 2.601 s | 0.076/0.225 s | 1.09x |
| Open/close | 2.479 s | 0.070/0.127 s | 8.500 s | 0.226/0.505 s | 3.43x |
| First read | 435.461 s | 1.295/15.612 s | 787.019 s | 1.049/22.877 s | 1.81x |
| Second read | 162.245 s | 0.735/11.721 s | 14.099 s | 0.240/6.015 s | 0.087x |

Both full-read phases spent nearly all wall time outside user/system CPU. Dell
first-read throughput was 47.1 MiB/s versus 25.6 MiB/s on wepp1. Dell's second
pass reached 126.3 MiB/s; wepp1's 1,429.3 MiB/s is necessarily memory-cache
throughput rather than its 1 GbE physical NFS path.

## NFS and memory evidence

- Dell mount: NFSv4.2, `rsize=1048576`, hard mount.
- wepp1 mount: NFSv4.2, `rsize=65536`, hard mount.
- Dell READ delta: 46,032 calls and approximately 36.96 GB received.
- wepp1 READ delta: 329,540 calls and approximately 21.29 GB received.
- wepp1 memory: 251 GiB total, 218 GiB buffer/cache at closeout.
- Dell workload cgroup: 12 GiB, smaller than the 21.49 GB corpus.

## Finding

The results refute slower HPC metadata or first-read service as the cause of
the historical interchange gap. They support a cache-capacity mechanism:
legacy interchange can consume recently written WEPP output from a large host
page cache, while the capped Dell worker must reread evicted output over NFS.

This was a native-corpus comparison rather than an identical-byte corpus and
did not invoke the parser or Parquet writer. The very similar sizes and exact
per-family counts make it adequate to disposition the storage-latency
hypothesis, but the next optimization benchmark should use WA-117 and report
per-family native conversion timing, output parity, NFS READ bytes, and cgroup
memory at each concurrency level.
