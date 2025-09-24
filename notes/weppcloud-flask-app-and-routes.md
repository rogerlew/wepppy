# WEPPcloud App

## Routes

### Organization

- `weppcloud/app.py` configures the Flask app, initializes extensions, and
  registers blueprints. Try to keep it limited to wiring and shared helpers.
- Blueprint modules live under `wepppy/weppcloud/routes`. Use either a
  package (for large feature areas like `browse/`) or a single module
  (`rhem.py`, `command_bar.py`, etc.) depending on the scope of the feature.
- Each blueprint is responsible for its templates/static assets. Templates are
  co-located under `wepppy/weppcloud/templates` using the same folder names as
  the feature (for example `templates/reports/rhem/`).
- Utility code that multiple blueprints rely on should live in
  `wepppy/weppcloud/utils` (for example `authorize` in
  `utils/helpers.py`). Avoid importing `app` inside blueprints to prevent
  circular references.

### Notes on creating blueprints / refactor app routes to new Blueprints

**When to extract a blueprint**

- Routes share a logical feature area (e.g., RHEM reporting, command bar APIs).
- They have dedicated templates/static files or are likely to grow.
- The code requires specialized authorization or request handling that is
  easier to reason about in isolation.

**Authoring a new blueprint**

1. Create a module under `wepppy/weppcloud/routes/` and define the blueprint.
   ```python
   from flask import Blueprint

   feature_bp = Blueprint('feature', __name__)
   ```
2. Move the relevant route functions into the module. Keep imports minimal and
   prefer helpers such as `get_wd`, `authorize`, or
   `exception_factory` from `weppcloud.utils.helpers` instead of pulling them
   from `app.py`. Move functions to `weppcloud.utils.helpers` if they are shared
   across multiple routes.
3. Preserve route decorators exactly as they exist in `app.py` so URLs and
   allowed HTTP methods do not change. Bring over any try/except blocks or
   logging so behavior remains identical.
4. Register the blueprint in `weppcloud/app.py`:
   ```python
   from routes.feature import feature_bp

   app.register_blueprint(feature_bp)
   ```
   Keep registrations grouped with similar features for readability.
5. Remove the original route definitions from `app.py` once they are in the
   blueprint. Verify that helper imports left in `app.py` are still needed.
6. Search for and update `url_for()` calls in `.htm`, `.html` and `.j2` templates. 
7. Run `python -m compileall path/to/blueprint.py` (fast syntax check) and any
   relevant tests or smoke checks before considering the refactor complete.
8. Smokecheck `app.py` with `python -m compileall`

**Tips**

- Avoid circular imports by keeping blueprint modules free of app-level
  objects. If shared state is required, push it into a helper module or use a
  Flask extension.
- Blueprint names (`Blueprint('rhem', __name__)`) become part of endpoint ids.
  Keep them short and consistent with the folder name.
- If a route needs template context defaults (`runid`, `config`), use
  `render_template` so failures fall back to JSON responses, matching
  existing app behavior.
- Document the change in this file when adding new patterns so future refactors
  stay consistent.
