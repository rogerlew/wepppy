"""Initialize an empty disposable CI account database, never an existing deployment."""
from importlib import import_module

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from wepppy.weppcloud.app import app, db


def main() -> None:
    with app.app_context(), db.engine.begin() as connection:
        if inspect(connection).get_table_names():
            raise RuntimeError("CI bootstrap requires an empty database")
        # Legacy migrations assume existing account tables. Current models supply
        # those tables; preferences require the migration's named PK/FK contract.
        db.metadata.create_all(
            connection,
            tables=[table for table in db.metadata.sorted_tables if table.name != "user_preferences"],
        )
        migration = import_module(
            "wepppy.weppcloud.migrations.versions.c91f6b2a4d7e_add_user_preferences"
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()


if __name__ == "__main__":
    main()
