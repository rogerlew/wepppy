# TB-20261009-RRINIT

**Low-Severity Forest Initial Random Roughness**

Document date: 2026-10-10. Change date: 2026-10-09. Revision: 1.
Status: approved for publication by Roger Lew on 2026-10-10. Document approval
is separate from parameter adoption (ADR-0083) and model deployment.

This brief explains the 4 to 6 cm low-burn forest consistency correction,
affected mappings, modeled sediment consequences, negligible tested runoff
changes and project regeneration/override implications. It uses retained
896-run and 112-run studies; no new simulations or parameter edits.

## Build and Verify

From this directory:

```bash
mkdir -p build
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
python verify.py
```

The PDF is `build/main.pdf`. Compile inputs are self-contained; the author
verification reads committed comparison CSV/identity evidence in this repo.
No external run or private fixture is required. See [publication-review.md](publication-review.md).

## Publication

Approved revision 1 and its public manifest are vendored at:

```text
wepppy/weppcloud/static/reports/wepppy/technical-briefs/20261009-rrinit/
  20261009-rrinit-r1.pdf
  publication-manifest-r1.json
```

Serve through the existing Caddy prefix `/weppcloud/static/reports/`.
Disturbed ENDUSER and the existing Usersum WEPP page link the PDF. The manifest
records its hash, study identities and explicit publication approval. Rebuilding
updates the local manifest; it does not update or replace an issued static PDF.
Production availability follows deployment of these files.
