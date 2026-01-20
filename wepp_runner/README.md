# `wepp_runner` a Python wrapper for running WEPP simulations.

============================================================================

This module provides functions for running WEPP simulations for hillslopes, flowpaths, and watersheds
with continuous, single storm (ss), and batch single storm (ss_batch) climates.

### General workflow for running WEPP simulations:
0. assumes you already have p<wepp_id>.sol, p<wepp_id>.cli, p<wepp_id>.slp, and p<wepp_id>.man
   files in the runs_dir

1. generate the hillslope .run files using one of the `make*_hillslope_run` functions
2. run the hillslope simulations using `run_hillslope`, `run_ss_hillslope`, or `run_ss_batch_hillslope`
3. generate the watershed .run file using one of the `make*_watershed_run` functions
4. run the watershed simulation using `run_watershed` or `run_ss_batch_watershed`

### Flowpaths
support for continuous and single storm flowpath simulations
flowpaths are independent from the hillslope/watershed simulations and WEPP does not support watershed 
routing of flowpaths.

### `*_relpath`s for hillslope running functions
wepp.cloud has an Omni functionality that builds scenarios as child projects within a parent.
The `make*_hillslope_run` functions have optional arguments to specify relative paths to the
management, climate, slope, and soil files from the runs_dir. This embeds the relative paths
in the .run files so that wepp can find files from the parent project. This prevents the climates,
and slopes from being copied into each child project.

### `make_watershed_omni_contrasts_run`
This supports mix and matching the hillslope outputs from different sibling and parent projects for
watershed simulations. The `wepp_path_ids` is a list of relative paths to the hillslope pass files
with the wepp_id included (without the .pass.dat). 
  e.g. ['H1', '../../<scenario>/wepp/output/H2', 'H3', 'H4', ...]
