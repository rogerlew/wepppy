# Postfire Debris Flow

- Current domain specification: [specification.md](specification.md).
- Track delivery and loose ends in [implementation_roadmap.md](implementation_roadmap.md).
  Update the roadmap, specification, and affected detailed contracts together
  as implementation progresses; roadmap proposals are not accepted contracts.
- Status: offline soil helper and local dNBR backend exist; production NoDb/UI/RQ
  integration remains pending.
- Preserve accepted decisions and explicitly label proposals and unresolved inputs.
- Follow `../../AGENTS.md` and the repository contract-first standard before
  adding NoDb, UI, API, or RQ behavior. This scaffold is not a completed
  pre-implementation checkpoint.
- Implement published equations independently; do not copy or translate GPL
  pfdf code, tests, or documentation into this module.
- Reference PDF storage decisions live in `docs/pdfs/README.md`; gitignore
  publisher PDFs without established redistribution permission.
