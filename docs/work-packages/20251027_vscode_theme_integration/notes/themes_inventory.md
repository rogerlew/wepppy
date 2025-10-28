# Themes Directory Inventory
> **Generated:** 2025-10-28  
> **Location:** `wepppy/weppcloud/themes/`

## Theme Files

### Configuration
- `theme-mapping.json` - Primary mapping configuration (11 themes)
- `theme-mapping.defaults.json` - Backup/default mappings
- `themes-contrast.json` - Automated contrast validation results (JSON)
- `themes-contrast.md` - Human-readable contrast report (Markdown)

### VS Code Theme Sources

**OneDark Family (1 theme):**
- `OneDark.json` - Atom-inspired dark theme by akamud
- `LICENSE.onedark` - MIT License

**Ayu Family (7 themes):**
- `ayu-dark.json` - Flat cards variant
- `ayu-dark-bordered.json` - Bordered cards variant
- `ayu-light.json` - Light theme with shadows
- `ayu-light-bordered.json` - Light theme with borders
- `ayu-mirage.json` - Mid-contrast dark (flat cards)
- `ayu-mirage-bordered.json` - Mid-contrast dark (bordered)
- `ayu-icons.json` - Icon theme (not used for colors)
- `LICENSE.ayu` - MIT License

**Cursor Family (4 themes):**
- `Cursor-Dark-Anysphere-color-theme.json` - Cursor Anysphere dark
- `Cursor-Dark-Midnight-color-theme.json` - Cursor Midnight dark
- `Cursor-Dark-High-Contrast-color-theme.json` - Cursor high-contrast dark
- `Cursor-Light-color-theme.json` - Cursor light theme
- `LICENSE.cursor` - License (check file for details)

## Generated CSS Output

**Location:** `wepppy/weppcloud/static/css/themes/`

- `all-themes.css` - Combined bundle (~10KB) loaded on every page
- Individual CSS files per theme (12 files):
  - `onedark.css`
  - `ayu-dark.css`
  - `ayu-dark-bordered.css`
  - `ayu-light.css`
  - `ayu-light-bordered.css`
  - `ayu-mirage.css`
  - `ayu-mirage-bordered.css`
  - `cursor-dark-anysphere.css`
  - `cursor-dark-midnight.css`
  - `cursor-dark-high-contrast.css`
  - `cursor-light.css`

## WCAG AA Compliance Summary

**6/11 themes pass** (54% compliance rate):

### ✅ Passing (WCAG AA Compliant)
1. **Ayu Dark** - All checks passed
2. **Ayu Dark Bordered** - All checks passed
3. **Ayu Mirage** - All checks passed
4. **Ayu Mirage Bordered** - All checks passed
5. **Cursor Light** - All checks passed

### ⚠️ Minor Issues (Near Compliant)
6. **OneDark** - 2 minor issues:
   - Muted Text vs Surface: 2.70 (needs 3.0)
   - Link vs Surface: 4.33 (needs 4.5)

7. **Cursor Dark (Anysphere)** - 1 minor issue:
   - Muted Text vs Surface: 2.16 (needs 3.0)

8. **Cursor Dark (Midnight)** - 1 minor issue:
   - Muted Text vs Surface: 2.19 (needs 3.0)

### ❌ Contrast Issues
9. **Ayu Light** - 2 issues:
   - Link vs Surface: 1.80 (needs 4.5)
   - Link vs Surface Alt: 1.73 (needs 4.5)

10. **Ayu Light Bordered** - 2 issues:
   - Link vs Surface: 1.85 (needs 4.5)
   - Link vs Surface Alt: 1.73 (needs 4.5)

11. **Cursor Dark (High Contrast)** - 3 issues:
   - Muted Text vs Surface: 2.46 (needs 3.0)
   - Link vs Surface: 1.06 (needs 4.5)
   - Link vs Surface Alt: 1.06 (needs 4.5)

## Theme Mapping Features

### Per-Theme Options
- `flat_cards` - Removes card borders and shadows (Ayu Dark, Mirage, Cursor Dark themes)
- `suppress_shadows` - Minimizes shadow effects (OneDark, Ayu Bordered variants)

### Per-Theme Overrides
Themes can override specific CSS variables:
- `--wc-color-border` / `--wc-color-border-strong`
- `--wc-shadow-sm` / `--wc-shadow-md`

Example (OneDark):
```json
"overrides": {
  "--wc-shadow-sm": "0 6px 18px rgba(0, 0, 0, 0.35)",
  "--wc-shadow-md": "0 18px 48px rgba(0, 0, 0, 0.45)",
  "--wc-color-border": "#181A1F",
  "--wc-color-border-strong": "#0F1115"
}
```

## Converter Tool Usage

**Location:** `wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py`

### Basic Commands
```bash
# Convert all themes (reads theme-mapping.json)
python convert_vscode_theme.py

# Generate contrast reports
python convert_vscode_theme.py --report themes-contrast.json
python convert_vscode_theme.py --md-report themes-contrast.md

# Validate without generating CSS
python convert_vscode_theme.py --validate-only

# Reset to defaults
python convert_vscode_theme.py --reset-mapping
```

### Advanced Usage
```bash
# Use custom mapping config
python convert_vscode_theme.py --mapping custom-theme-mapping.json

# Convert specific theme
python convert_vscode_theme.py --theme onedark

# Combine options
python convert_vscode_theme.py --validate-only --report output.json
```

## Theme Switcher UI

**Location:** `wepppy/weppcloud/templates/header/_theme_switcher.htm`

Simple dropdown selector with 12 options:
1. Default (Light) - System default (grayscale)
2. OneDark
3. Ayu Dark
4. Ayu Mirage
5. Ayu Light
6. Ayu Dark · Bordered
7. Ayu Mirage · Bordered
8. Ayu Light · Bordered
9. Cursor Dark (Anysphere)
10. Cursor Dark (Midnight)
11. Cursor Dark (High Contrast)
12. Cursor Light

**Persistence:** localStorage key `wc-theme`  
**Controller:** `wepppy/weppcloud/controllers_js/theme.js`

## Recommendations

### For Final Catalog
Consider reducing from 11 themes to 8-10:
- **Keep:** All Ayu variants (7 themes) - comprehensive family with good compliance
- **Keep:** Cursor Light - only WCAG AA compliant light theme beyond Ayu
- **Evaluate:** OneDark (2 minor issues but popular)
- **Evaluate:** Cursor Dark variants (3 themes with varying compliance)

### For WCAG AA Improvement
- Add Default Dark theme (guaranteed WCAG AA compliance)
- Fix Ayu Light link contrast (override `--wc-color-link` in mapping)
- Consider dropping Cursor Dark High Contrast (worst compliance)

### For Documentation
- Add to UI Style Guide (`docs/ui-docs/ui-style-guide.md`)
- Create stakeholder guide for editing `theme-mapping.json`
- Document theme testing procedure for new themes
