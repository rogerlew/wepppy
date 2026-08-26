# Windows WEPP Hill 106 Sidecar Ballpark

## Result

The unburned reconstruction strongly indicates that Elliot's Windows run had
neither `wepp_ui.txt` nor `pmetpara.txt` in its working directory. The lane
without either sidecar closely reproduces his annual water balance, while each
sidecar produces a large, diagnostic departure.

## Environment

- Host: `blarhg`, Windows 10 build `26200.8973`.
- Executable: `C:\WEPP\wepp\wepp_2024.exe`.
- Executable SHA-256:
  `5741e1f0c1030371098c6925b9c1d920aadc3d29e83fc37f7a3cc03bfc825c5e`.
- Isolated working root: `C:\tmp\topanga-h106-20260807`.
- The installed `C:\WEPP\runs` directory contained neither tested sidecar.
- Replays completed successfully and did not modify the installed WEPP
  workspace.

The reconstruction used the vendored Hill 106 climate, slope, run-control, and
scenario management files. Its `7778` soil was transcribed from Appendix B of
Elliot's report. The report's visually merged `10` line was interpreted as the
required `1 0` OFE record after the literal transcription failed parsing and
canonical `7778` fixtures confirmed the format.

The source `p106.run` requests 45 years, whereas Elliot reports a 40-year
Windows analysis. Results below are therefore ballpark comparisons of annual
means, not a claim of exact reproduction.

## Unburned Sidecar Matrix

All depths are annual means in millimeters except maximum lateral flow, which
is a daily maximum in millimeters.

| Lane | `wepp_ui.txt` | `pmetpara.txt` | Precipitation | Surface runoff | ET | Lateral flow | Maximum lateral flow |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| neither | absent | absent | 610.7 | 225.9 | 364.7 | 21.0 | 1.03 |
| UI only | present | absent | 610.7 | 160.5 | 330.7 | 120.4 | 10.32 |
| PMET only | absent | present | 610.7 | 250.3 | 336.4 | 24.8 | 1.03 |
| both | present | present | 610.7 | 165.1 | 301.1 | 145.3 | 10.32 |
| Elliot report | unknown | unknown | 612 | 220 | 368 | 22 | 0.8 reported globally |

The no-sidecar lane is the only lane matching all of Elliot's unburned annual
terms. `wepp_ui.txt` alone increases lateral flow by nearly `100 mm/year` and
cannot plausibly be Elliot's configuration. PMET alone moves ET about
`28 mm/year` away from his result.

This PMET response is consistent with the related
[Stevens Canyon legacy-ET ablation](../../2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/legacy-et-ablation-results.md)
in showing that the ET sidecar leaves a material diagnostic signature. The
Stevens Canyon result adds an important qualification: removing `pmetpara.txt`
mostly changed evaporation/transpiration partitioning, while burned-to-reference
total-ET ratios remained similar under PMET and legacy ET. It therefore rejected
disabling PMET as a remedy for excessive burned-run ET. Here, the Topanga ET
shift is evidence about which sidecars Elliot used, not evidence that the
legacy ET method is preferable.

## Burned Check

The no-sidecar burned AR=10 and AR=15 runs were identical:

| Lane | Precipitation | Surface runoff | ET | Lateral flow | Maximum lateral flow |
| --- | ---: | ---: | ---: | ---: | ---: |
| burned AR=10 | 610.7 | 330.2 | 250.3 | 28.1 | 0.80 |
| burned AR=15 | 610.7 | 330.2 | 250.3 | 28.1 | 0.80 |
| Elliot report, AR=10 | 612 | 246 | 346 | 18 | 0.8 |

This exactly reproduces the reported insensitivity to anisotropy and the
reported `0.8 mm/day` burned maximum, but not the burned annual water balance.
The discrepancy was subsequently localized to management parameterization.

## Burned Management Ballpark

A factorial screen of the five records that differ between the WEPPcloud
burned and undisturbed management files showed that root depth, initial
canopy/interrill cover, and maximum LAI control the water-balance mismatch.
The fragile-residue code and initial rill cover had negligible effects.

A 40-year refinement with maximum root depth `0.5 m`, initial
canopy/interrill cover `0.70/0.90`, and maximum LAI `2.25` produced:

| Statistic | Ballpark replay | Elliot report |
| --- | ---: | ---: |
| Precipitation (mm/year) | 610.61 | 612 |
| Surface runoff (mm/year) | 245.22 | 246 |
| ET (mm/year) | 345.48 | 346 |
| Lateral flow (mm/year) | 18.23 | 18 |
| Maximum lateral flow (mm/day) | 0.80 | 0.8 |

The complete sweep and selected lane are preserved in the
[`burned-man-ballpark` fixture](../fixtures/hill-106/windows-reconstruction/burned-man-ballpark/README.md).
This close fit establishes a plausible management configuration, but it is
not evidence that Elliot used these exact values.

## Interpretation

Current best reconstruction:

1. Elliot ran the legacy daily water-balance path: no `wepp_ui.txt`.
2. Elliot ran legacy Penman ET: no `pmetpara.txt`.
3. His unburned inputs are closely reconstructed.
4. His burned `7778` soil and annual water balance can be closely
   reconstructed with a plausible management configuration, including the
   inactive layer-anisotropy sensitivity.

The next artifact to request from Elliot is the Windows burned `.man` file,
followed by the original `.run` and a directory listing that includes hidden
or zero-length sidecars.
