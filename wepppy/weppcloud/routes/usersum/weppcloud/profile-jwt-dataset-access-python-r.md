# Profile JWT Dataset Access (Python and R)
> Get a personal JWT from the WEPPcloud profile page, then use it to open run datasets from Python or R.
> **See also:** `docs/dev-notes/auth-token.spec.md` and `docs/files-agent-api.md`.

## 1. Get a JWT from the profile page
1. Sign in to WEPPcloud.
2. Open `/weppcloud/profile`.
3. In **API Token**, click **Mint JWT Token**.
4. Click **Copy** and store it securely.

Notes:
- The token panel is available only to users with one of these roles: `Admin`, `PowerUser`, `Dev`, or `Root`.
- Profile-minted tokens expire after 90 days.
- Default audiences: `rq-engine`, `query-engine`.
- Default scopes: `runs:read`, `queries:validate`, `queries:execute`, `rq:status`, `rq:enqueue`, `rq:export`.
- Do not paste tokens into tickets, chat logs, or committed files.

## 2. Use the token with dataset file endpoints
For profile-minted user tokens, use:
- `GET /weppcloud/runs/{runid}/{config}/files/{path}?meta=true` to get metadata
- `GET /weppcloud/runs/{runid}/{config}/download/{path}` (from `download_url`) to fetch bytes

## 3. Python example (open a Parquet dataset)
```python
import io
from urllib.parse import quote, urljoin

import pandas as pd
import requests

BASE_URL = "https://your-weppcloud-host"
RUNID = "your-runid"
CONFIG = "your-config"
DATASET_PATH = "landuse/landuse.parquet"
JWT = "paste-token-here"

runid_q = quote(RUNID, safe="")
config_q = quote(CONFIG, safe="")
dataset_q = "/".join(quote(part, safe="") for part in DATASET_PATH.split("/"))
runs_root = f"/weppcloud/runs/{runid_q}/{config_q}"

headers = {
    "Authorization": f"Bearer {JWT}",
    "Accept": "application/json",
}

meta_url = urljoin(BASE_URL, f"{runs_root}/files/{dataset_q}?meta=true")
meta_resp = requests.get(meta_url, headers=headers, timeout=60)
meta_resp.raise_for_status()
meta = meta_resp.json()

download_url = urljoin(BASE_URL, meta["download_url"])
data_resp = requests.get(download_url, headers=headers, timeout=120)
data_resp.raise_for_status()

df = pd.read_parquet(io.BytesIO(data_resp.content))
print(df.head())
```

## 4. R example (open a Parquet dataset)
```r
library(httr2)
library(arrow)

base_url <- "https://your-weppcloud-host"
runid <- "your-runid"
config <- "your-config"
dataset_path <- "landuse/landuse.parquet"
jwt <- "paste-token-here"

runid_q <- URLencode(runid, reserved = TRUE)
config_q <- URLencode(config, reserved = TRUE)
parts <- strsplit(dataset_path, "/", fixed = TRUE)[[1]]
dataset_q <- paste(vapply(parts, URLencode, character(1), reserved = TRUE), collapse = "/")
runs_root <- paste0("/weppcloud/runs/", runid_q, "/", config_q)

meta_resp <- request(paste0(base_url, runs_root, "/files/", dataset_q, "?meta=true")) |>
  req_headers(Accept = "application/json") |>
  req_auth_bearer_token(jwt) |>
  req_perform()

meta <- resp_body_json(meta_resp, simplifyVector = TRUE)

data_resp <- request(paste0(base_url, meta$download_url)) |>
  req_auth_bearer_token(jwt) |>
  req_perform()

raw_bytes <- resp_body_raw(data_resp)
tbl <- read_parquet(rawConnection(raw_bytes))
print(head(tbl))
```

## 5. Common errors
- `401` Unauthorized: token is missing/expired/invalid.
- `403` Forbidden: your token is valid but your account cannot access that run.
- `404` Not found: wrong `runid`, `config`, or dataset path.

If you need to discover dataset paths first, call:
- `GET /weppcloud/runs/{runid}/{config}/files/?pattern=*.parquet&limit=1000`
