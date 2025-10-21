# weppcloud test suite

## Running route tests inside Docker

Many route and blueprint tests rely on dependencies installed in the Docker dev
environment (for example `rasterio`, `wepppyo3`, etc.). To exercise those tests,
use the `wctl` helper from the repo root:

```bash
wctl run "pytest tests/weppcloud/routes/test_blueprint_registration.py"
```

or to run the entire `tests/weppcloud` suite:

```bash
wctl run "pytest tests/weppcloud"
```

Behind the scenes `wctl run` executes the command inside the running
`weppcloud` container, so all optional dependencies are available. You can
substitute `pytest` arguments as needed (e.g. `-k`, `-q`, etc.).
