# 4096×4096 SBS Decoder Benchmark

**Date:** 2026-08-25
**Runtime:** Node.js 25, local development container host
**Input:** deterministic 4096×4096 RGBA buffer cycling through four current
palette colors, one historical color, one unknown opaque color, and one masked
pixel. Each measured run receives a fresh copy of the source buffer.

Reproduce from the repository root with:

```bash
node --expose-gc docs/work-packages/20260824_sbs_class_transport/artifacts/sbs_decoder_benchmark.mjs
```

The baseline is the pre-change shifted-mode string-key lookup. Each new path
was warmed once and then measured five times. Times are milliseconds.

| Path | Runs | Median | Baseline ratio |
| --- | --- | ---: | ---: |
| Existing shifted baseline | 2570.7, 2558.0, 2536.7, 2561.3, 2535.0 | 2558.0 | 1.000 |
| Run page, standard | 945.2, 941.3, 938.4, 949.8, 956.3 | 945.2 | 0.369 |
| Run page, shifted | 1049.9, 1046.4, 1046.5, 1080.6, 1045.4 | 1046.5 | 0.409 |
| GL Dashboard, standard | 1511.8, 1535.4, 1515.4, 1489.2, 1526.1 | 1515.4 | 0.592 |
| GL Dashboard, shifted | 1650.3, 1698.9, 1663.5, 1662.0, 1705.4 | 1663.5 | 0.650 |

All four paths are below the ratified 1.25× threshold. The implementation uses
a packed integer RGB lookup in the hot loop. Both clients retain the immutable
source canvas and at most one decoded destination canvas; changing display mode
replaces that destination instead of retaining a canvas per mode.

The harness measured a 67,108,864-byte source buffer and a 67,108,864-byte
destination-buffer increase. No additional image-sized buffer is retained by
either decoder. Canvas-cache tests and code inspection cover the client wrapper
that retains only the source plus the active destination canvas.
