# Forest Workflow Builder

Workflows under `.github/workflows/` are generated from the specs in this directory.
Modify the specs, then run:

```bash
scripts/build_forest_workflows.py
```

The generator combines:
- shared environment variables / setup / cleanup from `bootstrap.yml`
- job-specific definitions from each `*.yml` spec

Do **not** edit the generated workflow files directly. Instead, update the specs and rerun the builder (or `scripts/build_forest_workflows.py --check` to verify they are up to date).
