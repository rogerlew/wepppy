# WP12D Amendment 5 Forest writer acceptance

**Observation time**: 2026-08-28 18:42 UTC
**Host**: exact host `forest`
**Candidate revision**: `09ad4fbde329d96864df1bf50558f06eabdf91e8`
**Implementation checkpoint**: `1e30f7705`
**Reader floor**: `83165fd1b8cf6ebacf728daad6d22fc08052959e`
**Image**: unchanged `wepppy-dev` image `6ac7e7103046`
**Production action**: none; merge and production remain reserved to WP12

## Candidate deployment

Only `weppcloud`, `rq-engine`, and `rq-worker` were force-recreated from the
source-mounted development topology with `--no-build --no-deps`. All three
retained image digest
`sha256:6ac7e71030467a10e5d73dc18893cbd85c9202976d4b1b561a19dbb0d7ef2b75`.
WEPPcloud and rq-engine reported exact revision `09ad4fbde`; both health
endpoints returned HTTP 200. Recent service logs contained no traceback,
critical event, or startup failure.

The live Builder registry emitted the five new append-only identities:

- Continental US `3151e7e11be97967b32b887c6832b5286d252bf9b85841b889d5dcfbb24a8faf`:
  7 climate datasets, 114 land-cover datasets, default `nlcd-2019`;
- Europe `18eda2d24f57be54993d2f0b609c59de6c26a17632d8653cc62b5a926e66f2c7`:
  3 climate datasets, 5 CORINE datasets, default `corine-2018`;
- Canada `07f733c2b13589ac637fc898859b8e3eac4902199606a2580796eec47765d7b4`:
  3 climate datasets, 29 C3S datasets, default `c3s-landcover-2020`;
- Australia `1fd066a9e5bef26373414988d9f98e04fb84a8d0d08f7af280eef7cb1779a497`:
  3 climate datasets and its single Australian land-use dataset; and
- Earth `b1bbcd60e71b65064455da3abaacdb239a433bafe08c46854a2ffcfc9c50de92`:
  Vanilla/User-Defined climate and 29 C3S datasets.

## Real preset and provider evidence

The real `/wc1/runs/cl/closing-plump` `eu-disturbed` project resolved as
`preset_projection` for climate and landuse. Runtime discovery returned
exactly Vanilla CLIGEN, E-OBS Modified (Europe), and User-Defined Climate; its
land-cover graph contained exactly the five CORINE datasets with 2018 as the
default.

Unmocked climate builds used isolated copies of the real abstracted
`fatalist-ossuary` watershed:

- DEP NEXRAD downloaded and clipped a real 2013 breakpoint climate, applied
  daily temperature data, produced a one-year 18,685-byte CLI, and exported
  parquet, frequency, and Atlas-14 artifacts;
- Future CMIP5 retrieved real 2040 RCP8.5 data for the selected CLIGEN station,
  ran CLIGEN, produced a one-year 26,928-byte CLI, and exported its artifacts;
  and
- User-Defined Climate parsed a real 100-year uploaded CLI, calculated
  monthlies and station metadata, and emitted `wepp_cli.parquet` without a
  mocked executable or provider boundary.

Live WMesque retrieval plus rasterio/GDAL open validation passed for all 114
advertised U.S. land-cover datasets: 40 annual NLCD, 40 NLCD Ever Forest, and
34 eMapR vote years. Full unmocked `Landuse.build()` executions then passed for
`nlcd/2024`, `nlcd/ever_forest/2024`, and
`islay.ceoas.oregonstate.edu/v1/landcover/vote/2017`. Each produced a real
land-cover raster and 65 hillslope assignments; management construction also
completed.

## Refresh and reader-floor rollback

An isolated copy of the prior accepted schema-v3 project was previewed and
explicitly acknowledged. Capability refresh sequence 2 atomically changed:

- config SHA-256 from
  `f41b0672f9463b4af94b08a02e833093407e2719a877a1627c853a8dabc0d7ca`
  to `0d01f2eab4321787db8a27c97fbdc4d5be21b3efaeedf6479e367452c543fcf3`;
- manifest SHA-256 to
  `bc849c0d0d4f073abd631dbcd4ac9694de7bc7d7a180f80d310f3d73e004f0e1`;
  and
- stored structure to the new Continental-US identity `3151e7e1…8faf`, with
  7 climate and 114 land-cover datasets.

The next preview was unavailable, proving settlement. Services were then
recreated from exact reader floor `83165fd1b` with the update writer disabled.
That reader reopened the new stored identity with the same 7/114 axes, and the
config and manifest hashes remained byte-for-byte unchanged. The candidate was
restored without rebuilding; health, revision, stored identity, and both
hashes were reverified.

All provider and refresh work occurred in explicitly temporary copies; the
source projects were not modified. The temporary run copies, detached reader-
floor worktree, and Compose override were removed after evidence capture; the
copies are reproducible from their unchanged source projects. This acceptance
does not authorize merge or production deployment.
