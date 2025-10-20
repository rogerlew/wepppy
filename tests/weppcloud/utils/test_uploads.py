import io
from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask

from wepppy.weppcloud.utils import uploads
from wepppy.weppcloud.utils.uploads import UploadError


@pytest.fixture()
def app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "testing"
    return app


@pytest.fixture(autouse=True)
def override_get_wd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    def _fake_get_wd(runid: str) -> str:
        return str(tmp_path / runid)

    monkeypatch.setattr(uploads, "get_wd", _fake_get_wd)
    return tmp_path


def test_missing_file(app: Flask) -> None:
    with app.test_request_context("/", method="POST"):
        with pytest.raises(UploadError) as excinfo:
            uploads.save_run_file(
                runid="run",
                config="default",
                form_field="input_upload_cli",
                allowed_extensions=[".cli"],
                dest_subdir="climate",
            )
    assert str(excinfo.value) == "Could not find file"


def test_invalid_extension(app: Flask) -> None:
    with app.test_request_context(
        "/",
        method="POST",
        data={"input_upload_cli": (io.BytesIO(b"abc"), "bad.txt")},
        content_type="multipart/form-data",
    ):
        with pytest.raises(UploadError) as excinfo:
            uploads.save_run_file(
                runid="run",
                config="default",
                form_field="input_upload_cli",
                allowed_extensions=["cli"],
                dest_subdir="climate",
            )
    assert "Invalid file extension" in str(excinfo.value)


def test_overwrite_behavior(app: Flask, tmp_path: Path) -> None:
    runid = "run"
    with app.test_request_context(
        "/",
        method="POST",
        data={"input_upload_cli": (io.BytesIO(b"first"), "sample.cli")},
        content_type="multipart/form-data",
    ):
        saved_path = uploads.save_run_file(
            runid=runid,
            config="default",
            form_field="input_upload_cli",
            allowed_extensions=["cli"],
            dest_subdir="climate",
            overwrite=False,
        )
    assert saved_path.read_bytes() == b"first"

    with app.test_request_context(
        "/",
        method="POST",
        data={"input_upload_cli": (io.BytesIO(b"second"), "sample.cli")},
        content_type="multipart/form-data",
    ):
        with pytest.raises(UploadError):
            uploads.save_run_file(
                runid=runid,
                config="default",
                form_field="input_upload_cli",
                allowed_extensions=["cli"],
                dest_subdir="climate",
                overwrite=False,
            )

    with app.test_request_context(
        "/",
        method="POST",
        data={"input_upload_cli": (io.BytesIO(b"second"), "sample.cli")},
        content_type="multipart/form-data",
    ):
        uploads.save_run_file(
            runid=runid,
            config="default",
            form_field="input_upload_cli",
            allowed_extensions=["cli"],
            dest_subdir="climate",
            overwrite=True,
        )

    final_path = tmp_path / runid / "climate" / "sample.cli"
    assert final_path.read_bytes() == b"second"


def test_filename_sanitisation(app: Flask, tmp_path: Path) -> None:
    runid = "run"
    with app.test_request_context(
        "/",
        method="POST",
        data={
            "input_upload_cli": (
                io.BytesIO(b"content"),
                "../Weird Name.CLI",
            )
        },
        content_type="multipart/form-data",
    ):
        saved_path = uploads.save_run_file(
            runid=runid,
            config="default",
            form_field="input_upload_cli",
            allowed_extensions=["cli"],
            dest_subdir="climate",
        )

    assert saved_path.name == "weird_name.cli"
    assert saved_path.read_bytes() == b"content"


def test_post_save_error_removes_file(app: Flask, tmp_path: Path) -> None:
    runid = "run"

    def _raise_error(_: Path) -> None:
        raise UploadError("hook failed")

    with app.test_request_context(
        "/",
        method="POST",
        data={"input_upload_cli": (io.BytesIO(b"content"), "test.cli")},
        content_type="multipart/form-data",
    ):
        with pytest.raises(UploadError) as excinfo:
            uploads.save_run_file(
                runid=runid,
                config="default",
                form_field="input_upload_cli",
                allowed_extensions=["cli"],
                dest_subdir="climate",
                post_save=_raise_error,
            )

    assert str(excinfo.value) == "hook failed"
    assert not (tmp_path / runid / "climate" / "test.cli").exists()


def test_upload_helpers_responses(app: Flask) -> None:
    with app.app_context():
        response = uploads.upload_success()
        assert response.status_code == 200
        assert response.get_json() == {"Success": True}

        response = uploads.upload_success(message="ok", content={"foo": "bar"})
        assert response.status_code == 200
        assert response.get_json() == {
            "Success": True,
            "Message": "ok",
            "Content": {"foo": "bar"},
        }

        response = uploads.upload_failure("bad request", status=422)
        assert response.status_code == 422
        assert response.get_json() == {"Success": False, "Error": "bad request"}
