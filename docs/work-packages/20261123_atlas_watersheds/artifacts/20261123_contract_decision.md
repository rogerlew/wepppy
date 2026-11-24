# Watershed coverage on the Run Atlas

Starting revision 43ba346ae. Implementation conformance pending.
The operator requested restoration of all watersheds, removal of run IDs,
and removal of accesses and last access throughout the atlas. This changes
the Run Atlas section of the Pure landing contract. The previous public-only
contract matched the implementation. The change deliberately publishes exact
centroids for private projects while project access stays restricted.
The compiler derives display names from IDs, so omit both. Retain the existing
inventory, lifecycle rules, aggregation, unique runs, total hillslopes and four JSON URLs.

Verify mixed public/private input, duplicate coordinates, excluded lifecycle
states, and identifier-free generated JSON. Exercise old and new snapshots
through the landing and JSON aliases, verifying the public field allowlist,
absence of access dates and preservation of internal counters and TTL updates.

Independent correctness and security reviews accepted the scope. Clarified
the two retained metrics and required ordering by published fields so a
legacy snapshot cannot reveal access recency through marker order.
