# Change Log

Canonical WEPP build/version history for `wepp-forest`.

Required maintenance rule:
- update this file whenever a new build or rebuild is made (including new
  release-tagged binaries and version-affecting commits).
- add new entries at the top (descending chronology).

Reconstructed from `git log` using release/version-related commits (latest
first), through **07/19/2022**.

| Date | Commit Hash | Compiler | Version | Notes |
| --- | --- | --- | --- | --- |
| 04/17/2026 | `eb88c57` | `gfortran` | `wepp_260417` | Released `wepp_260417` and `wepp_260417_hill` from the peak-flow multi-OFE saturation-excess runoff correction in `src/irs.for` (contour/non-contour scaling parity fix). |
| 04/14/2026 | `a371884` | `gfortran` | `wepp_260414` | Added dated release build workflow (`tools/build_wepp_dated_release.sh`), disabled unsafe `make all` race path in `src/makefile`, added in-repo `delicate_game_pw0` fixture with parity regression tests, and published `release/wepp_260414*` built with `-O2 -finit-local-zero`. |
| 04/09/2026 | `c982160` | `gfortran` | `wepp_260409` | Fixed lower-bound GLC table lookup handling in `hydchn.for`, rebuilt `wepp`/`wepp_hill` with `/usr/bin/gfortran`, and published `release/wepp_260409*`. |
| 03/24/2026 | `d6b923b` | `gfortran` | `wepp_260324` | Fixed watershed pass metadata parsing for widened hillslope IDs, added reconciled-condenser regression fixture/manual gate, and corrected watershed banner channel-line alignment. |
| 03/24/2026 | `41dc020` | `gfortran` | `wepp_260324` | Widened hillslope/channel ID output formatting and rebuilt binaries (`wepp_260324` vendored in `wepppy`). |
| 03/19/2026 | `be4cf6d` | `gfortran` | `wepp_260319` | Added pinned `gfortran` rebuild workflow and refreshed `wepp_260319` binaries. |
| 10/03/2025 | `74ec026` | `ifx` | `-` | Fixed IFX hillslope hangs by relaxing deposition tolerance. |
| 10/03/2025 | `356f64d` | `ifx` | `-` | Added hillslope-optimized binary build (`wepp_hill`) alongside watershed build. |
| 09/15/2025 | `08e8872` | `ifx` | `wepp_250915` | IFX 50k makefile and release refresh (`wepp_250915`). |
| 08/08/2025 | `f63fcf5` | `ifort` | `wepp_50k` | `wepp_50k` revision. |
| 08/05/2025 | `f48e495` | `ifort` | `wepp_50k` | Initial `wepp_50k` release commit. |
| 03/12/2025 | `a557997` | `ifort` | `-` | Watershed pass-file parsing updated for longer first-table hillslope filenames. |
| 03/12/2025 | `726fbd5` | `ifort` | `-` | Increased WEPP pass-file name size. |
| 03/11/2025 | `bcf2ac5` | `ifort` | `-` | Updated `cwshed.inc` release content. |
| 03/11/2025 | `30ae9f7` | `ifort` | `-` | Extended `filen` length to 111 characters. |
| 06/06/2024 | `548fe07` | `ifort` | `-` | `outfil.for`/`open.for` support for 91-character paths. |
| 06/06/2024 | `6e47b5a` | `ifort` | `-` | `outfil.for` `filen` length extended to 91 characters. |
| 06/22/2023 | `bc9bccb` | `ifort` | `wepp_bc9bccb` | Release revision commit (`wepp_bc9bccb`). |
| 06/13/2023 | `31131a7` | `ifort` | `-` | Added conditional `keff` behavior based on `lkeff`. |
| 06/13/2023 | `050dd9d` | `ifort` | `wepp_050dd9d` | Linux `release/wepp` refresh (`wepp_050dd9d`). |
| 04/21/2023 | `201e020` | `ifort` | `wepp_201e020` | Increased watershed size limit (`wepp_201e020`). |
| 04/14/2023 | `e4cdc93` | `ifort` | `wepp_e4cdc93` | Increased maximum channels to 3600 (`wepp_e4cdc93`). |
| 03/30/2023 | `eeaed4b` | `ifort` | `wepp_eeaed4b` | Linux compiled release (`wepp_eeaed4b`). |
| 08/09/2022 | `5800970` | `ifort` | `wepp_580097` | 9002 soils Linux build (`wepp_580097`). |
| 08/05/2022 | `57afbc8` | `ifort` | `-` | Validated 9002 soils release. |
| 08/05/2022 | `f5fc4cb` | `ifort` | `wepp_f5fc4cb` | 9002 soils Van Genuchten parsing release (`wepp_f5fc4cb`). |
| 07/19/2022 | `81fd281` | `ifort` | `-` | 9001 soils Linux build baseline (keff-adjusted line). |
