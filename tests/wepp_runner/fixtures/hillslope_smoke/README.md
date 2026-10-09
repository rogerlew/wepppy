# Committed hillslope smoke inputs

Minimal p1/shared-file subset of wepp-forest's committed
tests/fixtures/delicate_game_pw0/runs at source commit
5a01758b7b998d54cccc47d7eea01847b04d866b. The run requests three simulation
years. These files are inputs, not output-parity expectations.

Both host and container smoke scripts stage this directory into a temporary
workspace and verify normal completion through the requested final year.
Do not replace the defaults with a private or untracked run directory.
RUNS_DIR overrides are available for supplementary investigations only.
