# Theme Contrast Report

`python wepppy/weppcloud/static-src/scripts/convert_vscode_theme.py --validate-only --report wepppy/weppcloud/themes/themes-contrast.json`

The converter now writes `themes-contrast.json`; sample values:

```json
{
  "generated_at": "2025-10-28T03:50:56.321570+00:00",
  "themes": {
    "onedark": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Muted Text vs Surface",
          "ratio": 2.7,
          "required": 3.0
        },
        {
          "pair": "Link vs Surface",
          "ratio": 4.33,
          "required": 4.5
        }
      ]
    },
    "ayu-dark": {
      "missing": [],
      "contrast_failures": []
    },
    "ayu-dark-bordered": {
      "missing": [],
      "contrast_failures": []
    },
    "ayu-light": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Link vs Surface",
          "ratio": 1.8,
          "required": 4.5
        },
        {
          "pair": "Link vs Surface Alt",
          "ratio": 1.73,
          "required": 4.5
        }
      ]
    },
    "ayu-light-bordered": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Link vs Surface",
          "ratio": 1.85,
          "required": 4.5
        },
        {
          "pair": "Link vs Surface Alt",
          "ratio": 1.73,
          "required": 4.5
        }
      ]
    },
    "ayu-mirage": {
      "missing": [],
      "contrast_failures": []
    },
    "ayu-mirage-bordered": {
      "missing": [],
      "contrast_failures": []
    },
    "cursor-dark-anysphere": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Muted Text vs Surface",
          "ratio": 2.16,
          "required": 3.0
        }
      ]
    },
    "cursor-dark-midnight": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Muted Text vs Surface",
          "ratio": 2.19,
          "required": 3.0
        }
      ]
    },
    "cursor-dark-high-contrast": {
      "missing": [],
      "contrast_failures": [
        {
          "pair": "Muted Text vs Surface",
          "ratio": 2.46,
          "required": 3.0
        },
        {
          "pair": "Link vs Surface",
          "ratio": 1.06,
          "required": 4.5
        },
        {
          "pair": "Link vs Surface Alt",
          "ratio": 1.06,
          "required": 4.5
        }
      ]
    },
    "cursor-light": {
      "missing": [],
      "contrast_failures": []
    }
  }
}
```

Focus follow-ups:
- OneDark: increase muted text + link contrast.
- Ayu Light variants: adjust link palette.
- Cursor Dark themes: muted text/link updates.

