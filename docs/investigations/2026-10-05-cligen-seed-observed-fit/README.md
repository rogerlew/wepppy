# CLIGEN random-seed effect on observed-climate fit

- Owner: WEPPpy
- Status: complete
- Study date: 2026-10-05
- Runtime revision: `7288e8fe5a772b1bb658fd0143ce58880e4934db`
- Runtime image: `sha256:61723893c23d7b189a81c1d59ffbe5076a0c6e60070a228d469933741d9640ec`
- Cluster execution record: [open-wepp-org work package](https://github.com/rogerlew/open-wepp-org/tree/main/docs/work-packages/20261005-cligen-seed-observed-fit)

## Question

How much does the CLIGEN random seed change WEPP observed-climate fit metrics
when every other run input is held constant?

## Design

- Source run: `srivas42-clammy-citizenry` (`MicaCreek-MOFE`).
- Climate: GridMetPRISM, multiple spatial climate, 1990–2007, 18 years,
  station `id108062`.
- Response: WEPP Channels `Streamflow (mm)` observed-fit metrics.
- Pilot: one unseeded control plus explicit seeds 0, 1, and 99999.
- Larger sample: 30 seeded realizations. The pilot seeds were retained and 27
  additional seeds were selected without replacement by
  `random.Random(20261005)`.
- Isolation: every realization was an independent fork of the source run.

The study compared normalized landuse, soils, watershed, and WEPP controller
state and the byte-identical observed CSV before execution. Every seeded climate
build logged its expected `-r<seed>` argument and produced a distinct
`wepp.cli` hash. Source-run invariants remained unchanged after the study.

## Results

| Period / metric | Mean | Sample SD | Minimum | Maximum | 5th percentile | 95th percentile |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Daily NSE | -0.30436 | 0.01699 | -0.33519 | -0.26034 | -0.33063 | -0.27832 |
| Daily KGE | 0.28025 | 0.00897 | 0.26470 | 0.29812 | 0.26635 | 0.29212 |
| Daily PBIAS (%) | 27.53899 | 0.25047 | 27.03088 | 28.03683 | 27.13010 | 27.95242 |
| Daily RMSE | 2.48305 | 0.01619 | 2.44085 | 2.51228 | 2.45819 | 2.50798 |
| Daily R² | 0.51277 | 0.00696 | 0.49983 | 0.53126 | 0.50378 | 0.52467 |
| Yearly NSE | 0.24995 | 0.00849 | 0.22688 | 0.26265 | 0.23531 | 0.26096 |
| Yearly KGE | 0.60960 | 0.00257 | 0.60502 | 0.61563 | 0.60554 | 0.61302 |
| Yearly PBIAS (%) | 28.18106 | 0.25172 | 27.65554 | 28.67723 | 27.78399 | 28.60972 |
| Yearly RMSE | 163.22240 | 0.92192 | 161.83768 | 165.71636 | 162.02315 | 164.81048 |
| Yearly R² | 0.93609 | 0.00128 | 0.93322 | 0.93847 | 0.93405 | 0.93834 |

The seed has a measurable but modest effect for this watershed and period. The
largest relative variability among the reported metrics is daily NSE (sample SD
0.01699; range 0.07485), followed by yearly NSE (sample SD 0.00849). PBIAS,
RMSE, and R² are comparatively stable.

The unseeded control exactly matched explicit seed 0 for every fit metric,
although their generated climate-file hashes differed. This is an observed
property of this runtime and configuration, not a general contract that an
omitted seed is equivalent to seed 0.

The full per-seed result table is in [results.csv](results.csv).

## Interpretation boundary

These results characterize one watershed, climate configuration, station, and
18-year period. They support treating seed variability as a small uncertainty
component for this case; they do not establish a global seed-sensitivity bound.
Additional sites and climate configurations are required before generalizing.

## Reproduction notes

1. Fork the source once per condition without modifying the source.
2. Set the fork's CLIGEN seed override, rebuild climate, and verify the durable
   seed plus the exact `-r<seed>` invocation token.
3. Confirm normalized non-seed controller hashes and the observed CSV hash still
   match the source.
4. Run the normal WEPP DAG and calculate observed fit.
5. Extract Channels `Streamflow (mm)` Daily and Yearly NSE, KGE, PBIAS, RMSE,
   and R².
6. Verify the source invariants again after all realizations complete.

The open-wepp.org execution record retains job-level history, cluster health
evidence, and operational findings. It is not the canonical scientific result.

## Operational finding

The study exposed a cluster deployment defect unrelated to the scientific
result: the dedicated `fork-archive` worker could not cold-import `project_rq`
because its expected Discord token file was absent. Forks were serialized on
the healthy default worker pool. One completed fork also required a short NFS
visibility retry before its controller files appeared. Both findings remain
owned by the open-wepp.org infrastructure record.
