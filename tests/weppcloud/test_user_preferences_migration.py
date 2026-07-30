from __future__ import annotations

import importlib

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

pytestmark = pytest.mark.unit


def test_user_preferences_merge_migration_upgrade_downgrade_upgrade() -> None:
    migration = importlib.import_module(
        "wepppy.weppcloud.migrations.versions."
        "c91f6b2a4d7e_add_user_preferences"
    )
    assert migration.down_revision == ("7b3c068e7a1d", "b7d9c3e2f1a4")

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        inspector = sa.inspect(connection)
        assert "user_preferences" in inspector.get_table_names()
        assert inspector.get_pk_constraint("user_preferences")["name"] == (
            "pk_user_preferences"
        )
        assert {
            item["name"] for item in inspector.get_check_constraints("user_preferences")
        } == {
            "ck_user_preferences_unit_system",
            "ck_user_preferences_wbt_boundary_touch_behavior",
        }

        with Operations.context(context):
            migration.downgrade()
        assert "user_preferences" not in sa.inspect(connection).get_table_names()

        with Operations.context(context):
            migration.upgrade()
        assert "user_preferences" in sa.inspect(connection).get_table_names()
