# Forest CI Host Baseline
> Host: `forest.local`  
> Scope: self-hosted GitHub Actions execution for `rogerlew/wepppy`  
> Last verified: 2026-03-29 (America/Los_Angeles)

## Purpose
Define what must be running on this machine so CI workflows targeting `self-hosted` + `homelab` continue to pick up jobs.

## Required Continuous Services
The following must be `active (running)` at all times:

| Component | Expected state | Why it is required |
| --- | --- | --- |
| `actions.runner.rogerlew-wepppy.forest.service` | enabled + active | Primary runner (`forest`) that matches `self-hosted`, `Linux`, `X64`, `homelab` labels. |
| `actions.runner.rogerlew-wepppy.forest-2.service` | enabled + active | Secondary runner (`forest-2`) for queue depth and parallelism. |
| `docker.service` | enabled + active | CI jobs use `wctl` wrappers and containerized tooling. |

## Not Required As Always-On Services
- Full WEPPcloud app stack containers are not required to run continuously for CI.
- CI jobs bring up/down the container context they need through `wctl` as part of workflow steps.

## Required Registration State
Both runners should appear in GitHub as `online` for the `rogerlew/wepppy` repository.

```bash
gh api repos/rogerlew/wepppy/actions/runners \
  --jq '.runners[] | {name,status,busy,labels:[.labels[].name]}'
```

Expected:
- runner names include `forest` and `forest-2`
- both expose labels `self-hosted`, `Linux`, `X64`, `homelab`
- status is `online` when idle or executing jobs

## Required Filesystem Layout
| Path | Expectation |
| --- | --- |
| `/workdir/wepppy` | repository checkout exists and is writable by runner user |
| `/workdir/wepppy/docker/.env` | present; workflows copy this into job workspaces via `RUNNER_DOCKER_ENV` |
| `/workdir/actions-runner` | configured runner install with `.runner` and `.credentials` |
| `/workdir/actions-runner-2` | configured second runner install with its own `.runner` and `.credentials` |

## Health Checks
Use this quick check set when jobs queue unexpectedly:

```bash
# 1) systemd state
systemctl --no-pager --full status \
  actions.runner.rogerlew-wepppy.forest.service \
  actions.runner.rogerlew-wepppy.forest-2.service \
  docker.service

# 2) runner registration / labels
gh api repos/rogerlew/wepppy/actions/runners \
  --jq '.runners[] | {name,status,busy,labels:[.labels[].name]}'

# 3) queued jobs snapshot
gh run list --repo rogerlew/wepppy --limit 20 \
  --json databaseId,workflowName,status,conclusion,headBranch,url
```

## Common Failure Mode (Observed 2026-03-12 to 2026-03-29)
Symptom:
- queued jobs remain unclaimed
- runner status is `offline`
- systemd shows `status=203/EXEC`

Cause:
- service unit `ExecStart` points at a non-existent runner path or `runsvc.sh`

## Recovery Procedure
Reinstall service units from each runner root so `ExecStart` matches the actual path.

```bash
# primary
cd /workdir/actions-runner
sudo ./svc.sh install roger
sudo ./svc.sh start

# secondary
cd /workdir/actions-runner-2
sudo ./svc.sh install roger
sudo ./svc.sh start
```

Then verify:

```bash
systemctl --no-pager --full status \
  actions.runner.rogerlew-wepppy.forest.service \
  actions.runner.rogerlew-wepppy.forest-2.service

gh api repos/rogerlew/wepppy/actions/runners \
  --jq '.runners[] | {name,status,busy}'
```

## Legacy Unit Cleanup
If legacy units exist and point to old paths, disable and remove them:

```bash
sudo systemctl disable --now \
  actions.runner.rogerlew-wepppy.forest-runner-1.service \
  actions.runner.rogerlew-wepppy.forest-runner-2.service

sudo rm -f \
  /etc/systemd/system/actions.runner.rogerlew-wepppy.forest-runner-1.service \
  /etc/systemd/system/actions.runner.rogerlew-wepppy.forest-runner-2.service

sudo systemctl daemon-reload
```
