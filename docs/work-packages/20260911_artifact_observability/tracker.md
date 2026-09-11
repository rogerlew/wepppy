# Tracker

- Contract and migration design prepared; independent reviews pending.
- Rule: observability takes precedence over concealment for completion/atomicity.
- Discovery: canonical archive uses os.walk and does not blanket-exclude dot
  paths; browse does exclude them. Tests will verify actual archive/restore bytes.
- Implementation, focused tests and live migration/browser checks pending.
