# Theme Mapping Guide

> Last updated: 2025-10-27  
> Owners: GPT-5 Codex (implementation), Claude Sonnet (planning)

This note explains how the configurable mapping system translates VS Code theme JSON files into WEPPcloud CSS variables. The mapping lives at:

- Editable file: `wepppy/weppcloud/themes/theme-mapping.json`
- Canonical defaults: `wepppy/weppcloud/themes/theme-mapping.defaults.json`

Use the editable file for day-to-day tweaks. If things go sideways, run:

```bash
python wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py --reset-mapping
```

to restore the editable file from the defaults template.

---

## File Structure

```jsonc
{
  "version": 1,
  "meta": { ... },
  "themes": {
    "onedark": { ... }
  },
  "variables": {
    "--wc-color-page": {
      "description": "...",
      "fallback": "#f6f8fa",
      "tokens": [
        "titleBar.inactiveBackground",
        { "token": "sideBar.background" }
      ],
      "overrides": {
        "some-theme": "#123456"
      }
    }
  }
}
```

- **`meta.defaults`** – default paths for the converter (themes dir, output dir, combined file name).
- **`themes`** – metadata for each theme we want to generate.
  - `label`: Human-friendly name.
  - `source`: VS Code theme JSON file (relative to `themes_dir`).
  - `variant`: `"light"` or `"dark"` (informational).
  - `options.flat_cards`: `true` removes borders/shadows for cards and control shells.
  - `options.suppress_shadows`: `true` keeps borders but removes shadows.
  - `overrides`: map of CSS variables to fixed values for that theme.
  - `extra_css`: optional array of raw CSS strings appended to the generated file.
- **`variables`** – mapping rules for each CSS custom property.
  - `tokens`: ordered list of VS Code color keys to try. The first one that exists in the theme wins.
    - Tokens can be simple strings or objects with transforms:
      ```json
      { "token": "focusBorder", "alpha": 0.2 }
      { "token": "activityBarBadge.background", "darken": 0.1 }
      { "literal": "#FF00FF" }
      ```
  - `fallback`: value applied when no token resolves.
  - `overrides`: per-variable, per-theme overrides (e.g., `"onedark": "#181A1F"`).

---

## Converter Usage

```
python wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py [options]

Options:
  --validate-only      Resolve tokens and print a summary without writing files
  --theme SLUG         Build a single theme (can be repeated)
  --mapping PATH       Use an alternate mapping JSON
  --output-dir PATH    Override the output directory
  --combined-file NAME Override the combined bundle filename
  --reset-mapping      Restore the editable mapping from the defaults template
```

Running without flags will:

1. Load `theme-mapping.json`
2. Convert every theme listed under `"themes"`
3. Write individual CSS files to `wepppy/weppcloud/static/css/themes/`
4. Build a combined bundle (`all-themes.css` by default)
5. Print a validation summary showing which variables fell back to defaults

Example:

```bash
python wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py \
  --report wepppy/weppcloud/themes/themes-contrast.json \
  --md-report wepppy/weppcloud/themes/themes-contrast.md
```

Generated files (checked into git):

- `static/css/themes/onedark.css`
- `static/css/themes/all-themes.css`
- `themes/themes-contrast.json` (machine-readable contrast results)
- `themes/themes-contrast.md` (human-readable summary)

---

## Editing Tips

- Keep token lists short and ordered by preference. The first match wins.
- Use `"overrides"` for small tweaks (e.g., adjust a single variable for a theme).
- Use `"options.flat_cards": true` for Mariana-style flat controllers (drops borders/shadows).
- Prefer hex colors in overrides. The converter understands `#RGB`, `#RRGGBB`, `#RRGGBBAA`.
- `alpha`, `lighten`, and `darken` transforms are fractional numbers between `0` and `1`.
  - `alpha: 0.2` -> `rgba(...)` output
  - `lighten: 0.1` mixes 10% white onto the token color
  - `darken: 0.2` mixes 20% black

---

## Adding a New Theme

1. Drop the VS Code theme JSON into `wepppy/weppcloud/themes/` (keep it in git).
2. Add a new entry under `"themes"` in the mapping:

   ```json
   "github-dark": {
     "label": "GitHub Dark",
     "source": "GitHubDark.json",
     "variant": "dark",
     "description": "GitHub's official dark theme.",
     "options": {
       "flat_cards": false
     }
   }
   ```

3. Run the converter in validate-only mode. Check the summary for variables that fell back, update tokens as needed.
4. Generate CSS and preview in the app by setting `data-theme="github-dark"` on `<html>` (temporary dev hook).
5. Submit the generated CSS along with the mapping change.

---

## Troubleshooting

- **“Missing token” warnings** – add more tokens for that variable or accept the fallback.
- **Theme feels too flat/too outlined** – adjust overrides (`--wc-color-border`, `--wc-shadow-*`) or flip `flat_cards`.
- **Stakeholder wants different taste** – teach them to edit `theme-mapping.json` and run the converter; no code changes needed.
- **Need a clean slate** – run `--reset-mapping` then reapply intentional overrides.

---

## Next Steps

- Phase 1 will introduce the runtime theme switcher and localStorage persistence.
- Accessibility validation (contrast checks) will land in Phase 2.
- Cross-device sync (`/api/theme/preference`) is deferred to Phase 3.

For now, Phase 0 deliverables are baked:

- Configurable mapping (`theme-mapping.json`)
- Dynamic converter script
- Reset/validate tooling
- Initial OneDark build + flat-card overrides

Feel free to extend the mapping—just keep the `defaults` file pristine so we always have a recovery path.
