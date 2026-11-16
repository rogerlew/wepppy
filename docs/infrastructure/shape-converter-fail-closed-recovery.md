# Shape-converter fail-closed recovery

The production deployment script exits `88` when it cannot prove that an
unqualified shape-converter is stopped. Treat this as a security stop: do not
start the former GDAL/Fiona implementation or any other parser fallback.

## Recover

1. Confirm the installed deployment intent with `wctl show-compose-files`. The
   full-stack host must include `docker/docker-compose.prod.yml`.
2. Find only this checkout's converter containers:

   ```bash
   docker ps -a \
     --filter label=com.docker.compose.service=shape-converter \
     --filter label=com.docker.compose.project.working_dir=/workdir/wepppy/docker
   ```

3. Stop each returned container ID with `docker stop --time 30 ID`. If stop
   fails, keep the converter unavailable at the proxy and escalate to the host
   operator; do not continue deployment.
4. Repeat the filtered query with `docker ps` (without `-a`) and require empty
   output. Also require the public
   `/utils/shape-converter/health/ready` request to fail while the service is
   intentionally down.
5. Before retrying, require a clean result for the shape-converter build inputs
   named by `ensure_shape_converter_build_inputs_clean` in
   `scripts/deploy-production.sh`. Reinstall the intended `wctl` preset if its
   reported paths are wrong.
6. Retry only through `scripts/deploy-production.sh`. The script must record the
   source revision, build the reviewed Rust-parser image, pass readiness and
   provenance checks, and verify the exact running image before success.

Retain the exit code, filtered container inventory, stop result, public
unavailability check, source revision, and final image ID in the deployment
receipt. A successful container stop by itself is not authorization to deploy.

During a failed full-stack cutover, rollback restores and verifies the retained
images for the other workloads. It excludes shape-converter from both the
explicit Compose service list and health verification, and uses `--no-deps` to
prevent a dependency from restarting the unreviewed parser. RQ resumes only
after retained workloads pass health and worker-registration checks. If stopping
the converter cannot be verified, exit `88` retains the RQ fence even if those
other workloads recover successfully.
