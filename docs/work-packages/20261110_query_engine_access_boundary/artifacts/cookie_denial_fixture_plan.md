# Cookie denial follow-up fixture plan

Create one new private ordinary run owned by dev-agent and one new private Batch
base/child under a random `qe-cookie-denial-` group. Initialize only synthetic
map metadata and a two-row parquet file. No existing run, role or membership is
changed. The real dev-agent account is an Admin without Batch membership, as
confirmed by the retained principal readback.

Observe the existing collection admission separately from grouped query admission:
the page must remain200 while no Batch query cookie is minted and its query stays
denied. Recheck ordinary private cookie/query/logout behavior after the correction.
Retain the failing and passing browser attempts. Store cleanup metadata in ignored,
bind-mounted `docker/secrets`, release NFS log handles with graceful web reload,
then remove only manifest-listed rows/directories/caches/markers and the manifest.
