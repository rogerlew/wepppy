# WEPPpy Technical Briefs

Point-in-time explanations for users of consequential WEPPpy changes: why a
change was made, what changed, who is affected, what results to expect, what
users should do, and what remains uncertain. These are shorter than scientific
release notes and can cover parameterization, datasets, workflows or software.

## First Brief

[TB-20261009-RRINIT: Low-Severity Forest Initial Random Roughness](20261009-rrinit/README.md)
explains the accepted 4 to 6 cm revision. Roger Lew approved document revision 1
for publication on 2026-10-10; the PDF and manifest are in the static reports tree.

## Authoring and Publication

Use [AUTHORING.md](AUTHORING.md) and the self-contained [template](templates/main.tex).
Keep authoring sources here. Do not rewrite closed work packages or silently
refresh historical results. Link the ADR, retained evidence and current user
guidance; a brief does not replace any of them.

After document-specific approval, copy the approved PDF and public manifest to:

```text
wepppy/weppcloud/static/reports/wepppy/technical-briefs/<date-topic>/
  <date-topic>-r1.pdf
  publication-manifest-r1.json
```

Caddy serves these at `/weppcloud/static/reports/wepppy/technical-briefs/`
without a new route, service or build dependency. Keep drafts out of that tree.
Only add user-facing download links once the approved files exist. Verify HTTP
200, PDF content type and downloaded SHA256. No model deployment is implied.

Use immutable revision filenames. A later correction gets a new revision and
an explicit supersedes statement, not an overwritten PDF. Publication manifests
record the document hash, author, change date/commit, evidence identities and
approval. Never include credentials or internal absolute paths in them.
