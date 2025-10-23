# NoDb State Management

> File-backed, Redis-cached singleton controllers for WEPPcloud run state management with distributed locking and zero-downtime serialization.

> **See also:** [AGENTS.md](../../AGENTS.md#working-with-nodb-controllers) for coding conventions and [docs/dev-notes/style-guide.md](../../docs/dev-notes/style-guide.md) for clarity expectations.

## Overview

The NoDb module replaces traditional relational databases with a constellation of file-backed singleton objects for managing WEPPcloud run state. Each NoDb controller:

- **Serializes to JSON** - Human-readable `.nodb` files in the working directory
- **Caches in Redis** - 72-hour TTL in DB 13 for instant hydration
- **Distributed locking** - Redis-backed locks (DB 0) prevent concurrent mutations
- **Singleton per run** - `getInstance(wd)` guarantees same object across workers
- **Structured telemetry** - Integrated logging pipeline to Redis pub/sub (DB 2)

Instead of SQL queries, developers interact with rich Python objects that expose domain-specific methods and properties. Redis provides coarse-grained locking and caching so these objects can be quickly deserialized and shared across workers and RQ tasks without conflicts.

**Why NoDb?**
- **Portability** - Zip a run directory and move it anywhere
- **Schema flexibility** - Add attributes without migrations
- **Developer ergonomics** - Python methods instead of SQL queries
- **Crash safety** - Redis caching with disk fallback
- **Distributed coordination** - Multi-worker safe via Redis locks

**Tradeoffs:**
- No relational queries or foreign keys
- Lock discipline required for all mutations
- JSON payloads can grow large
- Learning curve for bespoke patterns

