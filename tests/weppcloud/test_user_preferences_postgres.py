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
from wepppy.weppcloud.user_preferences import (
    PreferenceIdentityError,
    UserPreferenceValues,
    delete_registered_run,
    load_user_preferences,
    register_owned_run,
    resolve_creation_preferences,
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
    barrier = threading.Barrier(2, timeout=10)
    local = threading.local()

    with app.app_context():
        engine = db.engine

    def after_cursor_execute(
        _conn,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            "FROM user_preferences" in statement
            and "FOR UPDATE" in statement
            and not getattr(local, "first_select_seen", False)
        ):
            local.first_select_seen = True
            barrier.wait()

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_save_in_thread, user_id, "si", "warn"),
                executor.submit(_save_in_thread, user_id, "english", "error"),
            ]
            returned = {future.result(timeout=20) for future in futures}
    finally:
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

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
            and "FROM user_preferences" in statement
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
            and "FROM user_preferences" in statement
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


def test_postgres_identity_binding_and_owned_run_receipt(postgres_user) -> None:
    user_id, email, fs_uniquifier = postgres_user

    numeric = resolve_creation_preferences(
        {"token_class": "user", "sub": str(user_id), "email": email}
    )
    unique = resolve_creation_preferences(
        {"token_class": "user", "sub": fs_uniquifier, "email": email}
    )
    assert numeric is not None and numeric.user_id == user_id
    assert unique is not None and unique.user_id == user_id

    with pytest.raises(PreferenceIdentityError):
        resolve_creation_preferences(
            {
                "token_class": "user",
                "sub": str(user_id),
                "email": "conflict@example.com",
            }
        )
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_preferences(
            {"token_class": "user", "sub": str(2_000_000_000)}
        )
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_preferences({"token_class": "user"})

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.active = False
        db.session.commit()
    with pytest.raises(PreferenceIdentityError):
        resolve_creation_preferences(
            {"token_class": "user", "sub": str(user_id), "email": email}
        )
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.active = True
        db.session.commit()

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
