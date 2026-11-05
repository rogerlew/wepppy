"""Daily inbox population on the existing batch queue."""

import os
import sqlalchemy as sa

__all__ = ["populate_notifications"]


def populate_notifications(registration_ids=None):
    from wepppy.weppcloud.configuration import _build_postgres_uri
    from wepppy.weppcloud.notifications.producer import reconcile_ttl_notifications

    engine = sa.create_engine(os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
                              or _build_postgres_uri(), hide_parameters=True,
                              poolclass=sa.pool.NullPool)
    try:
        return reconcile_ttl_notifications(engine, registration_ids=registration_ids)
    finally:
        engine.dispose()
