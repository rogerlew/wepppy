from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from wepppy.weppcloud.app import (
    Run,
    User,
    UserPreferences,
    app,
    db,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.unitizer import Unitizer
from wepppy.weppcloud.user_preferences import (
    PreferenceIdentityError,
    UserPreferenceValues,
    delete_registered_run,
    load_user_preferences,
    register_owned_run,
    resolve_account_preferences,
    resolve_creation_actor,
    resolve_unitizer_presentation_for_user,
    save_user_preferences,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_user():
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("PostgreSQL integration database is required")
        suffix = uuid.uuid4().hex
        user = User(
            fs_uniquifier=suffix,
            email=f"surf14a-{suffix}@example.com",
            active=True,
        )
        db.session.add(user)
        db.session.commit()
        user_id = int(user.id)
        email = str(user.email)
        fs_uniquifier = str(user.fs_uniquifier)

    yield user_id, email, fs_uniquifier

    with app.app_context():
        user = db.session.get(User, user_id)
        if user is not None:
            for run in list(user.runs):
                db.session.delete(run)
            db.session.delete(user)
            db.session.commit()
        db.session.remove()


def _save_in_thread(
    user_id: int,
    unit_system: str,
    boundary_behavior: str,
) -> UserPreferenceValues:
    with app.app_context():
        return save_user_preferences(
            user_id,
            unit_system,
            boundary_behavior,
        )


def _load_in_thread(user_id: int) -> UserPreferenceValues:
    with app.app_context():
        return load_user_preferences(user_id)


def test_postgres_schema_constraints_and_cascade(postgres_user) -> None:
    user_id, _email, _fs_uniquifier = postgres_user
    with app.app_context():
        inspector = sa.inspect(db.engine)
        assert inspector.get_pk_constraint("user_preferences")["name"] == (
            "pk_user_preferences"
        )
        assert inspector.get_foreign_keys("user_preferences")[0]["name"] == (
            "fk_user_preferences_user_id_user"
        )
        assert {
            constraint["name"]
            for constraint in inspector.get_check_constraints("user_preferences")
        } == {
            "ck_user_preferences_unit_system",
            "ck_user_preferences_wbt_boundary_touch_behavior",
        }

        save_user_preferences(user_id, "si", "error")
        user = db.session.get(User, user_id)
        assert user is not None
        db.session.delete(user)
        db.session.commit()
        assert db.session.get(UserPreferences, user_id) is None


def test_postgres_concurrent_first_save_retries_whole_record(
    postgres_user,
) -> None:
    user_id, _email, _fs_uniquifier = postgres_user
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_save_in_thread, user_id, "si", "warn"),
            executor.submit(_save_in_thread, user_id, "english", "error"),
        ]
        returned = {future.result(timeout=20) for future in futures}

    assert returned == {
        UserPreferenceValues("si", "warn"),
        UserPreferenceValues("english", "error"),
    }
    with app.app_context():
        assert load_user_preferences(user_id) in returned
        assert UserPreferences.query.filter_by(user_id=user_id).count() == 1


def test_postgres_existing_update_is_serialized_and_last_commit_wins(
    postgres_user,
) -> None:
    user_id, _email, _fs_uniquifier = postgres_user
    with app.app_context():
        save_user_preferences(user_id, "config", "config")
        engine = db.engine

    first_locked = threading.Event()
    second_attempted = threading.Event()
    allow_first_commit = threading.Event()

    def before_cursor_execute(
        _conn,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            threading.current_thread().name == "preference-second"
            and 'FROM "user"' in statement
            and "FOR UPDATE" in statement
        ):
            second_attempted.set()

    def after_cursor_execute(
        _conn,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            threading.current_thread().name == "preference-first"
            and 'FROM "user"' in statement
            and "FOR UPDATE" in statement
        ):
            first_locked.set()
            assert allow_first_commit.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    errors: list[BaseException] = []

    def run_save(unit: str, boundary: str) -> None:
        try:
            _save_in_thread(user_id, unit, boundary)
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(
        target=run_save,
        args=("si", "warn"),
        name="preference-first",
    )
    second = threading.Thread(
        target=run_save,
        args=("english", "error"),
        name="preference-second",
    )
    try:
        first.start()
        assert first_locked.wait(timeout=10)
        second.start()
        assert second_attempted.wait(timeout=10)
        allow_first_commit.set()
        first.join(timeout=20)
        second.join(timeout=20)
    finally:
        allow_first_commit.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    with app.app_context():
        assert load_user_preferences(user_id) == UserPreferenceValues(
            "english",
            "error",
        )


@pytest.mark.parametrize("first_operation", ("read", "save"))
def test_postgres_read_and_save_serialize_in_both_orders(
    postgres_user,
    first_operation: str,
) -> None:
    user_id, _email, _fs_uniquifier = postgres_user
    initial = UserPreferenceValues("si", "warn")
    updated = UserPreferenceValues("english", "error")
    with app.app_context():
        save_user_preferences(
            user_id,
            initial.unit_system,
            initial.wbt_boundary_touch_behavior,
        )
        engine = db.engine

    first_locked = threading.Event()
    second_attempted = threading.Event()
    allow_first_commit = threading.Event()

    def before_cursor_execute(
        _conn,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            threading.current_thread().name == "preference-second"
            and 'FROM "user"' in statement
            and "FOR UPDATE" in statement
        ):
            second_attempted.set()

    def after_cursor_execute(
        _conn,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            threading.current_thread().name == "preference-first"
            and 'FROM "user"' in statement
            and "FOR UPDATE" in statement
        ):
            first_locked.set()
            assert allow_first_commit.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    results: dict[str, UserPreferenceValues] = {}
    errors: list[BaseException] = []

    def run_operation(name: str, operation: str) -> None:
        try:
            if operation == "read":
                results[name] = _load_in_thread(user_id)
            else:
                results[name] = _save_in_thread(
                    user_id,
                    updated.unit_system,
                    updated.wbt_boundary_touch_behavior,
                )
        except BaseException as exc:
            errors.append(exc)

    second_operation = "save" if first_operation == "read" else "read"
    first = threading.Thread(
        target=run_operation,
        args=("first", first_operation),
        name="preference-first",
    )
    second = threading.Thread(
        target=run_operation,
        args=("second", second_operation),
        name="preference-second",
    )
    try:
        first.start()
        assert first_locked.wait(timeout=10)
        second.start()
        assert second_attempted.wait(timeout=10)
        allow_first_commit.set()
        first.join(timeout=20)
        second.join(timeout=20)
    finally:
        allow_first_commit.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    if first_operation == "read":
        assert results == {"first": initial, "second": updated}
    else:
        assert results == {"first": updated, "second": updated}


def test_postgres_identity_binding_and_owned_run_receipt(postgres_user) -> None:
    user_id, email, fs_uniquifier = postgres_user

    numeric = resolve_creation_actor(
        {"token_class": "user", "sub": str(user_id), "email": email}
    )
    assert numeric is not None and numeric.user_id == user_id
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_actor(
            {"token_class": "user", "sub": fs_uniquifier, "email": email}
        )

    with pytest.raises(PreferenceIdentityError):
        resolve_creation_actor(
            {
                "token_class": "user",
                "sub": str(user_id),
                "email": "conflict@example.com",
            }
        )
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_actor(
            {"token_class": "user", "sub": str(2_000_000_000)}
        )
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_actor({"token_class": "user"})

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.active = False
        db.session.commit()
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_actor(
            {"token_class": "user", "sub": str(user_id), "email": email}
        )
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.active = True
        db.session.commit()

    with app.app_context():
        save_user_preferences(user_id, "si", "warn")
    account = resolve_account_preferences(
        {"token_class": "user", "sub": str(user_id)}
    )
    assert account is not None
    assert account.user_id == user_id
    assert account.preferences == UserPreferenceValues("si", "warn")

    runid = f"surf14a-{uuid.uuid4().hex}"
    receipt = register_owned_run(runid, "disturbed9002_wbt", user_id)
    with app.app_context():
        run = db.session.get(Run, receipt.run_pk)
        user = db.session.get(User, user_id)
        assert run is not None and run.owner_id == str(user_id)
        assert user is not None and run in user.runs

    delete_registered_run(receipt)
    with app.app_context():
        assert db.session.get(Run, receipt.run_pk) is None


def test_postgres_runid_collision_cannot_delete_preexisting_run(
    postgres_user,
) -> None:
    user_id, _email, _fs_uniquifier = postgres_user
    runid = f"surf14a-collision-{uuid.uuid4().hex}"
    with app.app_context():
        existing = Run(
            runid=runid,
            config="existing-config",
            owner_id=str(user_id),
        )
        db.session.add(existing)
        db.session.commit()
        existing_pk = int(existing.id)

    with pytest.raises(IntegrityError):
        register_owned_run(runid, "disturbed9002_wbt", user_id)

    with app.app_context():
        preserved = db.session.get(Run, existing_pk)
        assert preserved is not None
        assert preserved.config == "existing-config"


def test_two_users_view_same_project_in_preferred_units_without_mutation(
    postgres_user,
    tmp_path,
) -> None:
    first_user_id, _email, _fs_uniquifier = postgres_user
    with app.app_context():
        suffix = uuid.uuid4().hex
        second_user = User(
            fs_uniquifier=suffix,
            email=f"surf14a-viewer-{suffix}@example.com",
            active=True,
        )
        db.session.add(second_user)
        db.session.commit()
        second_user_id = int(second_user.id)
        save_user_preferences(first_user_id, "si", "warn")
        save_user_preferences(second_user_id, "english", "warn")

    run_dir = tmp_path / "shared-project"
    run_dir.mkdir()
    Ron(str(run_dir), "disturbed9002_wbt.cfg?unitizer:is_english=true")
    unitizer_path = run_dir / "unitizer.nodb"
    durable = Unitizer.getInstance(str(run_dir))
    durable_preferences = dict(durable.preferences)
    before_bytes = unitizer_path.read_bytes()
    before_mtime_ns = unitizer_path.stat().st_mtime_ns

    with ThreadPoolExecutor(max_workers=2) as executor:
        si_future = executor.submit(
            resolve_unitizer_presentation_for_user,
            str(run_dir),
            first_user_id,
        )
        english_future = executor.submit(
            resolve_unitizer_presentation_for_user,
            str(run_dir),
            second_user_id,
        )
        si_view = si_future.result(timeout=20)
        english_view = english_future.result(timeout=20)

    assert si_view.is_english is False
    assert english_view.is_english is True
    assert si_view is not durable
    assert english_view is not durable
    assert Unitizer.getInstance(str(run_dir)) is durable
    assert durable.preferences == durable_preferences
    assert unitizer_path.read_bytes() == before_bytes
    assert unitizer_path.stat().st_mtime_ns == before_mtime_ns
    assert list(run_dir.glob("*.lock")) == []

    with app.app_context():
        second_user = db.session.get(User, second_user_id)
        assert second_user is not None
        db.session.delete(second_user)
        db.session.commit()
