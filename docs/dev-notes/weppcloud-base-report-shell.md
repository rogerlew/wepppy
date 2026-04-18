# WEPPcloud `_base_report.htm` Developer Notes

This note documents how to use `wepppy/weppcloud/templates/reports/_base_report.htm` safely from report routes and templates.

## When to use `_base_report.htm`
Use `_base_report.htm` for run-scoped report pages that need the standard WEPPcloud report shell:
- Pure run header (run badge, name/scenario fields, More menu)
- shared Unitizer and PowerUser modals
- command bar include
- report script bundle includes (`controllers-gl.js`, `report_csv.js`, sort/copy helpers)

Do not include `header/_run_header_fixed.htm` from templates that already extend `_base_report.htm`.

## Template contract
A report template should start with:

```jinja
{% extends "reports/_base_report.htm" %}
```

Use the base blocks:
- `report_title`
- `head_extras` (optional CSS)
- `report_content`

## Required route context
Routes rendering templates that extend `_base_report.htm` must provide these context objects explicitly:
- `runid`
- `config`
- `ron`
- `current_ron`
- `user`
- `unitizer_nodb`
- `precisions`

`_base_report.htm` and included partials reference these directly (`ron.name`, `ron.mods`, `unitizer_nodb.is_english`, unit preference radios, etc.).

If any are missing, Jinja can raise `UndefinedError` while rendering shared header/modal partials.

## Minimal route pattern

```python
from wepppy.nodb.core import Ron
from wepppy.nodb.core.ron import RonViewModel
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS

...

ctx = load_run_context(runid, config)
wd = str(ctx.active_root)
ron = Ron.getInstance(wd)
unitizer = Unitizer.getInstance(wd)

return render_template(
    "reports/<module>/<name>.htm",
    runid=runid,
    config=config,
    ron=ron,
    current_ron=RonViewModel(ron),
    user=current_user,
    unitizer_nodb=unitizer,
    precisions=UNITIZER_PRECISIONS,
    ...,
)
```

## Operational notes
- If you wrap rendered HTML in a `Response(...)` (for example, to set `Cache-Control`), keep the same template context contract above.
- Keep report-specific payloads in a dedicated JSON node (`<script type="application/json">`) and let client JS parse that node.
- For run-scoped query/report pairs, keep the payload shape identical between `/query/...` and `/report/...` outputs.

## Related references
- `docs/ui-docs/report-ui-conventions.md`
- `wepppy/weppcloud/templates/reports/_base_report.htm`
