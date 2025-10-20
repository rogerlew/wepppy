# Upload Handling Standard

This note defines the canonical pattern for handling user uploads inside the WEPPcloud stack. All existing upload endpoints (climate `.cli`, cover-transform, SBS raster, etc.) should converge on this workflow so validation, security, and telemetry remain consistent.

---

## 1. Goals
- Prevent duplicated boilerplate when saving run-scoped files.
- Enforce consistent validation (file size, extension, content type, destination path).
- Centralise error responses and telemetry hooks (StatusStream / RedisPrep).
- Provide a single integration point for per-upload post-processing (e.g., raster verification, CLI parsing).
- Simplify testing by consolidating logic into a reusable helper.

## 2. Scope
Covered upload entry points include:
- Climate: `tasks/upload_cli/`, `tasks/upload_future_cli/`, etc.
- Disturbed/BAER: SBS raster upload & removal.
- WEPP: cover transform upload.
- Any future run-level uploads (e.g., custom management files, CSV imports).

Non-run uploads (e.g., admin configs) may also use the helper but are out of scope for the initial migration.

## 3. Shared Helper (`uploads.py`)
Create `wepppy/weppcloud/utils/uploads.py` exposing:

```python
class UploadError(Exception):
    """Raised when validation fails (user-facing message)."""

def save_run_file(
    *,
    runid: str,
    config: str,
    form_field: str,
    allowed_extensions: Sequence[str],
    dest_subdir: str,
    run_root: str | Path | None = None,
    filename_transform: Optional[Callable[[str], str]] = None,
    overwrite: bool = False,
    post_save: Optional[Callable[[Path], None]] = None,
    max_bytes: Optional[int] = None,
) -> Path:
    """Validate & persist a file uploaded via Flask request.files."""
```

Behaviour:
1. **Request validation** – ensure `request.files` contains `form_field`, otherwise raise `UploadError("Could not find file")`.
2. **Filename validation** – reject empty names; use `secure_filename`. Filenames are lowercased by default; pass a `filename_transform` callback to preserve legacy casing.
3. **Extension check** – compare against `allowed_extensions` (case-insensitive). Optionally inspect MIME (future enhancement).
4. **Destination** – resolve run working directory (`get_wd(runid)` by default) or honour the `run_root` override, append `dest_subdir`, ensure the directory exists.
5. **Overwrite semantics** – if file exists and `overwrite=False`, raise `UploadError`. Otherwise remove/replace.
6. **Save** – use `FileStorage.save()` with buffered chunks (`buffer_size=64 * 1024`).
7. **Post-save hook** – if `post_save` provided, invoke with the final `Path`. Allow hook to raise `UploadError` for domain-specific issues (e.g., invalid raster). Any failure removes the saved artefact.
8. **Return** – `Path` to the saved file (absolute).

Expose a companion helper:

```python
def upload_success(
    message: str | None = None,
    *,
    content: Any | None = None,
    status: int = 200,
    **extras: Any,
) -> Response

def upload_failure(error: str, status: int = 400, **extras: Any) -> Response
```

These keep responses uniform across endpoints.

## 4. Error Handling
- Wrap invocations with `try/except UploadError` returning `upload_failure(str(err))`.
- Catch unexpected exceptions and route through `exception_factory` to preserve existing logging + HTTP codes.
- Keep HTTP status `400` for validation failures, `500` for unexpected errors.

## 5. Security & Limits
- Ensure Flask `MAX_CONTENT_LENGTH` guards huge uploads (set in config if not already).
- Add explicit max-size validation in `save_run_file` (optional parameter) for fine-grained limits (e.g., 100 MB SBS raster).
- Consider verifying raster metadata (projection, data type) or CLI header structure inside `post_save` hooks.
- Remove temporary files on failure to avoid partial artefacts.

## 6. Telemetry
- Post-save hooks can enqueue RedisPrep events or append to StatusStream logs (climate + WEPP already do this).
- For synchronous uploads (cover transform), log success via `controlBase.appendStatus`.
- For asynchronous flows, broadcast `"UPLOAD_COMPLETED"` events so StatusStream listeners update logs consistently.

## 7. Testing
- Add unit tests under `tests/weppcloud/utils/test_uploads.py` covering:
  - Missing file / invalid extension / overwrite behaviour.
  - Filename sanitisation.
  - Post-save hook raising `UploadError`.
  - Temp directory isolation (`tmp_path` fixture).
- Extend existing climate/disturbed tests to exercise the shared helper (e.g., `test_upload_cli` via Flask test client).

## 8. Migration Plan
1. Implement `uploads.py` + tests.
2. Update each upload endpoint sequentially:
   - Climate CLI uploads.
   - Cover transform upload.
   - SBS raster upload.
3. Remove duplicated validation code once routes switch to the helper.
4. Document new usage in each module docstring + update `control_components.md` where UI references the uploads.

## 9. Notes & Future Enhancements
- Investigate chunked uploads or background processing for multi-GB rasters if the helper proves insufficient.
- Integrate virus scanning if deployments require strict security policies.
- Consider returning structured metadata (e.g., CLI header info, raster statistics) directly from `post_save` for richer UI feedback.

---

**Maintainers:** update this document whenever we add new upload flows or adjust validation rules, keeping the helper in sync across the stack.
