from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .runtime_catalog import RuntimeDoc


class UsersumSearchUnavailableError(RuntimeError):
    pass


def _import_postgres_driver() -> tuple[str, Any]:
    try:
        import psycopg  # type: ignore

        return "psycopg", psycopg
    except Exception:
        pass
    try:
        import psycopg2  # type: ignore

        return "psycopg2", psycopg2
    except Exception as exc:
        raise UsersumSearchUnavailableError(
            "No PostgreSQL driver is installed (tried psycopg and psycopg2)"
        ) from exc


class PostgresUsersumSearchBackend:
    def __init__(self, db_url: str, *, table_name: str = "usersum_docs_search") -> None:
        self._db_url = db_url
        self._table = table_name
        self._driver_kind, self._db_module = _import_postgres_driver()
        self._last_synced_signature: str | None = None

    def _connect(self):
        try:
            return self._db_module.connect(self._db_url)
        except Exception as exc:
            raise UsersumSearchUnavailableError(
                f"Could not connect to PostgreSQL for usersum search: {exc}"
            ) from exc

    def _exec_ddl(self, conn: Any) -> None:
        ddl_statements = [
            "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
              doc_id TEXT PRIMARY KEY,
              rel_path TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              title_norm TEXT NOT NULL,
              headings_text TEXT NOT NULL DEFAULT '',
              min_role TEXT NOT NULL CHECK (min_role IN ('user', 'operator', 'developer', 'internal')),
              category TEXT NOT NULL,
              audience_tags TEXT[] NOT NULL DEFAULT '{{}}',
              source TEXT NOT NULL CHECK (source IN ('local', 'vendor')),
              vendor_id TEXT NULL,
              nav_key TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'active',
              body_text TEXT NOT NULL,
              search_tsv tsvector NOT NULL,
              deleted_at TIMESTAMPTZ NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              content_hash TEXT NOT NULL
            );
            """,
            f"CREATE INDEX IF NOT EXISTS {self._table}_search_tsv_gin ON {self._table} USING GIN (search_tsv);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_title_trgm_gin ON {self._table} USING GIN (title_norm gin_trgm_ops);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_headings_trgm_gin ON {self._table} USING GIN (headings_text gin_trgm_ops);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_min_role_idx ON {self._table} (min_role);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_category_idx ON {self._table} (category);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_status_idx ON {self._table} (status);",
            f"CREATE INDEX IF NOT EXISTS {self._table}_vendor_idx ON {self._table} (vendor_id);",
        ]
        with conn.cursor() as cur:
            for stmt in ddl_statements:
                cur.execute(stmt)

    @staticmethod
    def _sync_signature(docs: Sequence[RuntimeDoc]) -> str:
        digest = hashlib.sha256()
        for doc in sorted(docs, key=lambda item: item["doc_id"]):
            digest.update(doc["doc_id"].encode("utf-8"))
            digest.update(doc["content_hash"].encode("utf-8"))
        return digest.hexdigest()

    def ensure_synced(self, docs: Sequence[RuntimeDoc]) -> None:
        signature = self._sync_signature(docs)
        if signature == self._last_synced_signature:
            return

        conn = self._connect()
        try:
            conn.autocommit = False
            self._exec_ddl(conn)
            with conn.cursor() as cur:
                upsert_sql = f"""
                INSERT INTO {self._table} (
                    doc_id, rel_path, title, title_norm, headings_text, min_role, category,
                    audience_tags, source, vendor_id, nav_key, status, body_text, search_tsv,
                    deleted_at, updated_at, content_hash
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    setweight(to_tsvector('english', coalesce(%s, '')), 'A')
                    || setweight(to_tsvector('english', coalesce(%s, '')), 'B')
                    || setweight(to_tsvector('english', coalesce(%s, '')), 'C'),
                    NULL, now(), %s
                )
                ON CONFLICT (doc_id) DO UPDATE SET
                    rel_path = EXCLUDED.rel_path,
                    title = EXCLUDED.title,
                    title_norm = EXCLUDED.title_norm,
                    headings_text = EXCLUDED.headings_text,
                    min_role = EXCLUDED.min_role,
                    category = EXCLUDED.category,
                    audience_tags = EXCLUDED.audience_tags,
                    source = EXCLUDED.source,
                    vendor_id = EXCLUDED.vendor_id,
                    nav_key = EXCLUDED.nav_key,
                    status = EXCLUDED.status,
                    body_text = EXCLUDED.body_text,
                    search_tsv = EXCLUDED.search_tsv,
                    deleted_at = NULL,
                    updated_at = now(),
                    content_hash = EXCLUDED.content_hash;
                """

                rows = []
                for doc in docs:
                    headings_text = " ".join(doc["headings"])
                    body_text = doc["body_text"]
                    rows.append(
                        (
                            doc["doc_id"],
                            doc["rel_path"],
                            doc["title"],
                            doc["title"].lower(),
                            headings_text,
                            doc["min_role"],
                            doc["category"],
                            doc["audience_tags"],
                            doc["source"],
                            doc["vendor_id"],
                            doc["nav_key"],
                            doc["status"],
                            body_text,
                            doc["title"],
                            headings_text,
                            body_text,
                            doc["content_hash"],
                        )
                    )
                cur.executemany(upsert_sql, rows)

                doc_ids = [doc["doc_id"] for doc in docs]
                cur.execute(
                    f"UPDATE {self._table} SET deleted_at = now() WHERE doc_id <> ALL(%s::text[]);",
                    (doc_ids,),
                )

            conn.commit()
            self._last_synced_signature = signature
        except Exception as exc:
            conn.rollback()
            raise UsersumSearchUnavailableError(
                f"Failed to sync usersum search index in PostgreSQL: {exc}"
            ) from exc
        finally:
            conn.close()

    def search(
        self,
        *,
        query: str,
        roles: Sequence[str],
        categories: Sequence[str] | None,
        limit: int,
        offset: int,
    ) -> tuple[List[Dict[str, Any]], int]:
        conn = self._connect()
        try:
            q_norm = " ".join(query.strip().lower().split())
            conn.autocommit = True
            sql = f"""
            WITH params AS (
                SELECT
                    %(query)s::text AS query,
                    %(q_norm)s::text AS q_norm,
                    websearch_to_tsquery('english', %(query)s) AS tsq
            ),
            scored AS (
                SELECT
                    d.doc_id,
                    d.title,
                    d.rel_path,
                    d.min_role,
                    d.category,
                    d.updated_at,
                    d.search_tsv @@ p.tsq AS lexical_hit,
                    ts_rank_cd(d.search_tsv, p.tsq, 32) AS fts_rank,
                    similarity(d.title_norm, p.q_norm) AS title_sim,
                    similarity(d.headings_text, p.q_norm) AS headings_sim,
                    GREATEST(
                        similarity(d.title_norm, p.q_norm),
                        similarity(d.headings_text, p.q_norm)
                    ) AS trgm_rank,
                    ((ts_rank_cd(d.search_tsv, p.tsq, 32) * 0.85)
                      + (GREATEST(similarity(d.title_norm, p.q_norm), similarity(d.headings_text, p.q_norm)) * 0.15)
                    ) AS score,
                    ts_headline(
                        'english',
                        d.body_text,
                        p.tsq,
                        'MaxFragments=2,MinWords=8,MaxWords=24'
                    ) AS snippet
                FROM {self._table} d
                CROSS JOIN params p
                WHERE d.deleted_at IS NULL
                  AND d.status = 'active'
                  AND d.min_role = ANY(%(roles)s::text[])
                  AND (%(categories)s::text[] IS NULL OR d.category = ANY(%(categories)s::text[]))
                  AND (
                        d.search_tsv @@ p.tsq
                     OR similarity(d.title_norm, p.q_norm) >= 0.35
                     OR similarity(d.headings_text, p.q_norm) >= 0.30
                  )
            ),
            paged AS (
                SELECT
                    doc_id,
                    title,
                    rel_path,
                    min_role,
                    category,
                    COALESCE(NULLIF(snippet, ''), substr(rel_path || ' ' || title, 1, 220)) AS snippet,
                    score,
                    count(*) OVER() AS total
                FROM scored
                ORDER BY lexical_hit DESC, score DESC, fts_rank DESC, updated_at DESC, doc_id ASC
                LIMIT %(limit)s
                OFFSET %(offset)s
            )
            SELECT doc_id, title, rel_path, min_role, category, snippet, score, total
            FROM paged;
            """
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    {
                        "query": query,
                        "q_norm": q_norm,
                        "roles": list(roles),
                        "categories": list(categories) if categories else None,
                        "limit": limit,
                        "offset": offset,
                    },
                )
                rows = cur.fetchall()

            if not rows:
                return [], 0

            results: List[Dict[str, Any]] = []
            total = int(rows[0][7])
            for row in rows:
                results.append(
                    {
                        "doc_id": row[0],
                        "title": row[1],
                        "rel_path": row[2],
                        "min_role": row[3],
                        "category": row[4],
                        "snippet": row[5] or "",
                        "score": float(row[6]),
                    }
                )
            return results, total
        except Exception as exc:
            raise UsersumSearchUnavailableError(
                f"Usersum PostgreSQL search query failed: {exc}"
            ) from exc
        finally:
            conn.close()
