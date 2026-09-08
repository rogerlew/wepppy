# Postfire Debris Flow PDF Cache

## Storage Decision: Staley 2017

Decision date: 2026-09-08. Keep `staley_2017.pdf` as a **gitignored local
reference**, not a Git LFS object, until redistribution rights for the exact
PDF are established. The operator-provided 42-page accepted manuscript is now
stored locally; see the [retrieval record](../README.md) for its checksum.

Evidence and rationale:

- Root `.gitattributes` applies Git LFS to `*.pdf`; RUSLE already uses that
  storage convention. LFS changes binary storage, not redistribution rights.
- The initially indexed file is the 14-page journal version. The supplied
  local file is a different version: a 42-page accepted manuscript with an
  Elsevier cover sheet identifying it as unedited and awaiting production.
  No explicit Creative Commons or public-repository redistribution grant was
  found in its extracted text.
- [Crossref metadata](https://api.crossref.org/works/10.1016/j.geomorph.2016.10.019)
  lists text/data-mining licenses, not an explicit open redistribution license.
- [Elsevier copyright policy](https://www.elsevier.com/about/policies-and-standards/copyright)
  recognizes public-domain US government employee works. That alone does not
  establish rights in this exact PDF, which also includes a
  nonfederal institutional affiliation.
- [Elsevier permission guidance](https://www.elsevier.support/elsevier/answer/when-is-permission-not-required)
  distinguishes public-domain underlying work from its formatted published
  version. This restriction on the final formatted version is not by itself
  a reason to exclude the supplied accepted manuscript.
- [Accepted-manuscript sharing policy](https://www.elsevier.com/about/policies-and-standards/sharing)
  permits specified author sharing and public hosting after embargo, subject
  to conditions including a DOI link, CC-BY-NC-ND notice, and hosting policy.
  The supplied file has no such license notice, and permission for this
  repository's redistribution has not been established. Do not attach a
  license on behalf of the rights holders. Retain the ignore decision pending
  version-specific evidence rather than treating all accepted manuscripts as
  prohibited from redistribution.
- Availability on a government mirror establishes a discovery location, not
  blanket permission to redistribute. This decision records uncertainty; it
  does not assert that the underlying scientific work is copyrighted.

Commit this README, the citation catalog, and the scoped `.gitignore`.
Do not force-add the PDF. If an explicit reusable license, applicable
public-domain confirmation, or permission for repository distribution is later
obtained, document the evidence and exact version here, remove its ignore rule,
and let the existing root PDF LFS rule handle storage. No `.gitattributes`
change is necessary.

This decision is independent of pfdf's GPL-3.0-only software license and does
not prohibit independently implementing the published mathematical method.
