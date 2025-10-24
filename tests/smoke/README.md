# Smoke Profiles

YAML profiles in this directory describe common smoke scenarios.

```
profiles/
├── quick.yml         # US quick sanity
├── rattlesnake.yml   # (future) SBS scenario
├── blackwood.yml     # (future) larger watershed
├── earth.yml         # (future) international datasets
```

`wctl run-smoke --profile quick` (planned) will load the chosen profile, export the env vars, and invoke the Playwright suite.

See [`tests/README.smoke_tests.md`](../README.smoke_tests.md) for detailed instructions.
