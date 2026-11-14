# M0 baseline and sandbox prerequisite probe

Date: 2026-11-14 05:13 UTC. Status: M0 incomplete; selected candidate blocked.
Source HEAD: `127a55fad4eecf426a5346c79c307b05606a05b2` with pre-existing
dirty contract/package/tracker files. No production source edits were made.

## Baseline

Executed through `wctl run-pytest`, with `--maxfail=1`, these exact modules:

- `tests/shape_converter/unit/test_archive_validation.py`
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_cleanup_lifecycle.py`
- `tests/shape_converter/unit/test_health_routes.py`
- `tests/shape_converter/unit/test_runtime_hardening.py`
- `tests/shape_converter/integration/test_inspect_api.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/integration/test_runtime_hardening_api.py`

Result: **136 passed, 168 warnings in 59.52 seconds**. Warnings were dependency
deprecations. This baseline does not establish conformance to the new contract.

## Direct red observations

Disposable probes ran through `/opt/venv/bin/python` in
`wepppy-shape-converter`, using temporary directories automatically removed on
exit. No executable payload bytes were retained.

- FC-01: serialized an object whose `__reduce__` returned `Path.touch` and a
  temporary canary path; called the real `convert._read_parser_payload`.
  Result: `parent_result=invalid_shapefile`,
  `canary_created_before_rejection=True`, `temporary_root_removed=True`.
  Mapping validation occurs after executable deserialization.
- FC-05: real ZIP extraction admitted both `caf\u00e9.shp` and
  `cafe\u0301.shp` (Unicode escapes shown for reproducibility), and separately
  both `STRASSE.shp` and `stra\u00dfe.shp`: two members each.
- FC-07: real extraction and selection accepted `one.shp`, `one.shx`,
  `one.dbf`, and `two.shp`, selecting `one`. These files contained bounded dummy
  bytes; this observation concerns admission/selection, not native parsing.

Source inventory confirms pickle write at `convert_parser_worker.py:152`, read
at `convert.py:561`, direct subprocess launch at `convert.py:430`, driver
allowlist without identity assertion at `convert_parser_worker.py:43`, mode
string readiness at `app.py:90`, lowercase collision keys at
`archive_validation.py:153`, and complete-prefix selection at `inspect.py:236`.
The full semantic/driver/ratio/error red matrix remains pending.

## Existing runtime receipt

Running image:
`sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`.
This is an existing development image, not a rebuilt candidate.

- UID/GID `10001:10001`; effective/permitted/bounding capabilities zero.
- Read-only root, `cap_drop=ALL`, `no-new-privileges:true`; `NoNewPrivs: 1`.
- `docker-default (enforce)` AppArmor and `Seccomp: 2`.
- PID limit 256, memory 1073741824 bytes, CPU limit 1.5.
- `/tmp` tmpfs 734003200 bytes, `noexec,nosuid,nodev,mode=1777`.
- `/run/shape-converter` tmpfs 8388608 bytes,
  `noexec,nosuid,nodev,mode=755`.
- Internal `wepppy-shape-converter-sandbox` network.
- Read-only source mount and inherited Redis password secret mount exist.
  No secret content was read. These mounts reinforce why the worker needs a
  separate filesystem boundary; they are not authorization to change mounts.
- CLI GDAL 3.10.3; Fiona 1.10.1 linked GDAL 3.10.3;
  pyproj 3.7.1 / PROJ 9.5.1; Shapely 2.0.4 / GEOS 3.11.3.

Native linkage, build provenance, SBOM, current vulnerability disposition,
candidate build, and forest1 evidence remain pending. No dependency was upgraded.

## Candidate and prerequisite result

Evaluated Bubblewrap as the single namespace-based candidate. No precedent was
found in the dependency registry or searched infrastructure/architecture docs.
It provides filesystem/PID/network isolation absent from the current subprocess
launcher; it does not replace the owned geospatial stack. Upstream explicitly
states that the caller must define the sandbox policy and that unprivileged
operation uses user namespaces:
[Bubblewrap documentation](https://github.com/containers/bubblewrap).

The host already supplies Ubuntu package `0.9.0-1ubuntu0.3` (`bubblewrap 0.9.0`),
binary SHA-256
`e318903862396f96de3df57264e0158682b952fd3fb53ac23d876413e7b30f71`.
No package was installed. Dependency tax, maintenance/CVE assessment, and parity
benchmarks are deferred because the prerequisite failed; adoption is not approved.

First, inside the existing service:

    docker exec wepppy-shape-converter unshare --user --map-root-user --mount --pid --net --fork true
    unshare: unshare failed: Operation not permitted

Then, run the actual Bubblewrap executable in a disposable container:

    docker run --rm --user 10001:10001 --read-only --cap-drop ALL \
      --security-opt no-new-privileges:true --pids-limit 256 --memory 1g \
      --cpus 1.50 --ulimit nofile=65536:65536 \
      --tmpfs /tmp:size=734003200,noexec,nosuid,nodev,mode=1777 \
      --tmpfs /run/shape-converter:size=8388608,noexec,nosuid,nodev,mode=755 \
      --network wepppy-shape-converter-sandbox \
      --mount type=bind,src=/usr/bin/bwrap,dst=/probe/bwrap,readonly \
      --entrypoint /probe/bwrap \
      sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b \
      --unshare-all --die-with-parent --new-session --ro-bind /usr /usr \
      --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
      --proc /proc --dev /dev /usr/bin/true

Exit 1: `bwrap: No permissions to create new namespace`. This minimal startup
probe never reached its command. It is not a complete parser sandbox policy.
The disposable container was automatically removed; running services were not
reconfigured or restarted.

This establishes failure under the tested restrictions, not attribution to a
particular kernel/seccomp/AppArmor control. A host-provided executable in the
existing image is a prerequisite feasibility test, not production-equivalent
candidate acceptance. It does not prove every in-container mechanism impossible.

## Independent security review and resume gate

Independent `security_reviewer` agent `/root/sandbox_gate_review` inspected the
plan, source, and supplied probe results. Decision: retain M0 as incomplete and
stop before implementation. High findings for executable IPC and missing second
sandbox remain open; readiness is still non-attesting. No contract checkpoint,
implementation review approval, issue closure, or deployment is claimed.

Per M0, do not silently relax container protections or introduce a parser service.
The next operator decision is whether to authorize bounded evaluation of a
different, non-namespace mechanism under unchanged protections, or amend the
milestone order to deliver independent IPC/archive fixes while sandbox
conformance remains blocked. Neither choice authorizes rollout. Full containment,
semantic parity, timeout/descendant cleanup, and current dependency evidence are
still required before closure.
