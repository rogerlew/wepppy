# API Transcript

- Generated UTC: 2026-05-02T06:50:36Z
- BASE_HOST: `https://wc.bearhive.duckdns.org`
- rq-engine base: `https://wc.bearhive.duckdns.org/rq-engine/api`
- Auth mode: login session + CSRF POST /weppcloud/profile/mint-token (bearer user token)
- Token values are redacted.

## Calls

| UTC | Method | Path | Status | Key Fields |
|---|---|---|---:|---|
| 2026-05-02T06:10:05Z | GET | `/weppcloud/login` | 200 | <!doctype html>
<html lang="en" class="wc-page">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width...(truncated) |
| 2026-05-02T06:10:06Z | POST | `/weppcloud/login` | 302 | <!doctype html>
<html lang=en>
<title>Redirecting...</title>
<h1>Redirecting...</h1>
<p>You should be redirected automatically to the target...(truncated) |
| 2026-05-02T06:10:06Z | GET | `/weppcloud/profile` | 200 | <!doctype html>
<html lang="en" class="wc-page">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width...(truncated) |
| 2026-05-02T06:10:06Z | POST | `/weppcloud/profile/mint-token` | 200 |  |
| 2026-05-02T06:10:06Z | GET | `/rq-engine/api/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/pipeline` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:10:06Z | GET | `/rq-engine/api/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/readiness` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:10:06Z | GET | `/rq-engine/api/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/endpoints?include_operation_docs=true` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_revision', 'run_state_domain', 'run_state_vector', 'operations', 'operation_docs'] |
| 2026-05-02T06:10:06Z | POST | `/rq-engine/api/runs/moth-eaten-blackhead/disturbed9002-wbt-mofe/run-wepp` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434' |
| 2026-05-02T06:10:06Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:10:16Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:10:26Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:10:36Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:10:46Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:10:56Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:06Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:16Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:26Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:36Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:46Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:11:56Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:06Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:17Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:27Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:37Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:47Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:12:57Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='started' |
| 2026-05-02T06:13:07Z | GET | `/rq-engine/api/jobstatus/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='stopped' |
| 2026-05-02T06:13:07Z | GET | `/rq-engine/api/jobinfo/cda9f32a-afe8-4e65-8722-b58266d23434` | 200 | job_id='cda9f32a-afe8-4e65-8722-b58266d23434'; status='finished' |
| 2026-05-02T06:13:07Z | GET | `/rq-engine/api/runs/cochlear-beriberi/disturbed9002-mofe/pipeline` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:13:07Z | GET | `/rq-engine/api/runs/cochlear-beriberi/disturbed9002-mofe/readiness` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:13:07Z | GET | `/rq-engine/api/runs/cochlear-beriberi/disturbed9002-mofe/endpoints?include_operation_docs=true` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_revision', 'run_state_domain', 'run_state_vector', 'operations', 'operation_docs'] |
| 2026-05-02T06:13:08Z | POST | `/rq-engine/api/runs/cochlear-beriberi/disturbed9002-mofe/run-wepp` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1' |
| 2026-05-02T06:13:08Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:13:18Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:13:28Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:13:38Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:13:48Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:13:58Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:08Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:18Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:28Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:38Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:48Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:14:58Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:08Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:18Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:28Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:38Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:48Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:15:58Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:08Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:18Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:28Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:38Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:48Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:16:58Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:08Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:18Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:29Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:39Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:49Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:17:59Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:09Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:19Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:29Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:39Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:49Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:18:59Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:09Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:19Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:29Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:39Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:49Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:19:59Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:09Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:19Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:29Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:39Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:49Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:20:59Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='started' |
| 2026-05-02T06:21:09Z | GET | `/rq-engine/api/jobstatus/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='stopped' |
| 2026-05-02T06:21:09Z | GET | `/rq-engine/api/jobinfo/b6fa67aa-be85-491b-a2e3-795dd4deefc1` | 200 | job_id='b6fa67aa-be85-491b-a2e3-795dd4deefc1'; status='finished' |
| 2026-05-02T06:21:10Z | GET | `/rq-engine/api/runs/ordained-incentive/disturbed9002-wbt-mofe/pipeline` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:21:10Z | GET | `/rq-engine/api/runs/ordained-incentive/disturbed9002-wbt-mofe/readiness` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:21:10Z | GET | `/rq-engine/api/runs/ordained-incentive/disturbed9002-wbt-mofe/endpoints?include_operation_docs=true` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_revision', 'run_state_domain', 'run_state_vector', 'operations', 'operation_docs'] |
| 2026-05-02T06:21:10Z | POST | `/rq-engine/api/runs/ordained-incentive/disturbed9002-wbt-mofe/run-wepp` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2' |
| 2026-05-02T06:21:10Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:21:20Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:21:30Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:21:40Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:21:50Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:00Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:10Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:20Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:30Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:40Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:22:50Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:00Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:10Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:21Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:31Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:41Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:23:51Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:24:01Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='started' |
| 2026-05-02T06:24:11Z | GET | `/rq-engine/api/jobstatus/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='stopped' |
| 2026-05-02T06:24:11Z | GET | `/rq-engine/api/jobinfo/ccae766f-30ce-4ae0-917a-c6a005c07ad2` | 200 | job_id='ccae766f-30ce-4ae0-917a-c6a005c07ad2'; status='finished' |
| 2026-05-02T06:40:04Z | GET | `/rq-engine/api/runs/uninsured-deformation/disturbed9002-wbt-mofe/pipeline` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:40:04Z | GET | `/rq-engine/api/runs/uninsured-deformation/disturbed9002-wbt-mofe/readiness` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_domain', 'run_state_revision', 'run_state_vector', 'updated_at', 'data_state', 'data_updated_at'] |
| 2026-05-02T06:40:04Z | GET | `/rq-engine/api/runs/uninsured-deformation/disturbed9002-wbt-mofe/endpoints?include_operation_docs=true` | 200 | keys=['contract_version', 'deployment_revision', 'run_state_revision', 'run_state_domain', 'run_state_vector', 'operations', 'operation_docs'] |
| 2026-05-02T06:40:04Z | POST | `/rq-engine/api/runs/uninsured-deformation/disturbed9002-wbt-mofe/run-wepp` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2' |
| 2026-05-02T06:40:04Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:40:14Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:40:24Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:40:34Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:40:44Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:40:54Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:04Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:14Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:24Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:34Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:45Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:41:55Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:42:05Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:42:15Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:42:25Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='started' |
| 2026-05-02T06:42:35Z | GET | `/rq-engine/api/jobstatus/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='failed' |
| 2026-05-02T06:42:35Z | GET | `/rq-engine/api/jobinfo/27aa2b17-52e0-41d6-9ad4-6823d63806b2` | 200 | job_id='27aa2b17-52e0-41d6-9ad4-6823d63806b2'; status='finished' |
