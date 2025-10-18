# QMD Reports Feature Sandbox Spec

## Context
- Capture requirements from discussion on running Quarto `.qmd` notebooks in a constrained execution environment.
- Goal: enable deterministic report generation without exposing host filesystem or uncontrolled CPU/memory usage.

## Execution Environment
- Container image bundles Quarto CLI, Python runtime, and required kernels/dependencies with pinned versions for reproducibility.
- Run container with restrictive flags such as `--rm`, `--read-only`, `--memory=<limit>`, `--cpus=<limit>`, and optional `--pids-limit`.
- Mount project assets read-only via `-v /host/reports:/app:ro`; add `--tmpfs /tmp` or a minimal writable scratch volume for intermediates.

## Report Rendering Flow
- Invoke `quarto render <file>.qmd --to html` inside the container.
- Preferred extraction pattern: stream HTML to host through stdout using `--output -`, allowing the wrapper to persist or forward the artifact.
- Alternative: provide a narrow read-write bind (e.g., `-v /host/out:/out:rw`) and set `--output-dir /out` for captured files.
- For ad-hoc debugging, `docker cp <container>:/path/report.html -` remains an option but is not required for automation.

## Security Hardening
- Assume embedded Python can run arbitrary code; rely on container isolation, read-only mounts, and limited resources.
- Drop root privileges inside the container, tighten seccomp/apparmor profiles, and disable or isolate networking unless explicitly needed.
- Audit writable paths to ensure only ephemeral or scratch locations are exposed.

## Next Steps
1. Author a Dockerfile that installs Quarto, Python, and notebook dependencies with locked versions.
2. Implement a host wrapper (script or service) that launches the container with the resource limits above, streams stdout to capture HTML, and manages temporary volumes.
