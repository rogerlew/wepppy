# Quarto esbuild repair

Production and development now compile esbuild 0.25.10 from Quarto’s original upstream source revision with Go 1.26.11. The build stage pins the toolchain image by digest, verifies the source commit and uses a Go workspace with the current toolchain defaults. The Quarto installation step checks both esbuild versions before replacing the executable in the same image layer. Only the resulting executable enters the runtime image. Updating Quarto requires rechecking its expected esbuild version and its actual PATH report.

The Docker build produced SHA-256 `8745a1d1193f38f8198683b0c234182a01232b9de5e09387d6fffc8d59fafea6`, identical to the independently qualified executable. The frozen Go database returned zero module findings for it. The PATH report called the replacement twice, produced a readable map and preserved the expected scientific CSV result. A standalone JavaScript bundle and source map matched the originals byte for byte, and the bundled program returned the expected result.

The current public Quarto 1.11.9 Debian package also rendered the PATH case, producing 2,154,248 bytes of HTML. Its esbuild 0.28.1 contains the Go 1.26.4 version string and lacks build metadata recognized by the Go scanner, so that trial could not establish a fix. The same-version build retains the qualified reporting stack and preserves Go build information for future scans. [Quarto 1.11.9](https://github.com/quarto-dev/quarto-cli/releases/tag/v1.11.9) · [esbuild source](https://github.com/evanw/esbuild/tree/d6b668f96fb00d6a6d035f058e38b6bd2507beb6)

Protected component build and public Quarto comparison receipts are in the private `round2/` evidence directory. The independent scanner and render evidence is in `security/go/trials/`.
