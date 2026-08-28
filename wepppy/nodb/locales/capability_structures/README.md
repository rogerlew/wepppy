# Capability Structure Catalog

`catalog.json` is the append-only reader authority for complete stored
schema-v2/schema-v3 capability graph structures. Each entry retains the full
canonical payload, its SHA-256 identity, and the first reader revision.

Do not regenerate or rewrite an existing entry when locale catalogs change.
Adding the first real map/capability structure requires its own ratified
contract amendment, fixture, reader-first Forest deployment, and rollback
evidence before a writer may persist it. Test-only evolution belongs in an
isolated in-memory catalog and must never be added here.

PC-24/WP12D amendment 5 appends one schema-v3 identity for each of the five
Builder locales. Those identities add the ratified climate envelopes and, for
Continental US, the complete annual NLCD, NLCD Ever Forest, and eMapR vote
land-cover envelope. The prior schema-v3 identities remain readable. The first
reader revision is recorded immediately after the standalone reader-floor
commit, before any writer or locale-profile change.

The structural payload includes locale, non-runtime axes, relations,
per-dataset method defaults, and normalized backend/representation pairs. It
excludes project `capability_defaults`, provider/binary provenance, the binary
axis, and the binary member of model tuples. The runtime loader canonicalizes
each payload as sorted-key compact JSON and refuses startup when its recorded
hash does not match.
