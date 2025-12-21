from collections import OrderedDict
from types import SimpleNamespace
from markupsafe import Markup
from flask import Blueprint, render_template

from wepppy.weppcloud.controllers_js import unitizer_map_builder

ui_showcase_bp = Blueprint("ui_showcase", __name__, url_prefix="/ui/components")


THEME_OPTIONS = [
    ("default", "Default (Light)"),
    ("onedark", "OneDark"),
    ("dark-modern", "Dark Modern"),
    ("ayu-dark", "Ayu Dark"),
    ("ayu-mirage", "Ayu Mirage"),
    ("ayu-light", "Ayu Light"),
    ("ayu-dark-bordered", "Ayu Dark · Bordered"),
    ("ayu-mirage-bordered", "Ayu Mirage · Bordered"),
    ("ayu-light-bordered", "Ayu Light · Bordered"),
    ("cursor-dark-anysphere", "Cursor Dark (Anysphere)"),
    ("cursor-dark-midnight", "Cursor Dark (Midnight)"),
    ("cursor-dark-high-contrast", "Cursor Dark (High Contrast)"),
]


def _build_unitizer_demo():
    map_data = unitizer_map_builder.build_unitizer_map_data()
    precisions = OrderedDict()
    for category in map_data["categories"]:
        units = OrderedDict()
        for unit in category["units"]:
            units[unit["key"]] = unit["precision"]
        precisions[category["key"]] = units

    preferences = {}
    for category_key, units in precisions.items():
        keys = list(units.keys())
        preferences[category_key] = keys[1] if len(keys) > 1 else keys[0]

    unitizer_stub = SimpleNamespace(preferences=preferences, is_english=True)

    def cls_units(value):
        return (
            str(value)
            .replace("/", "_")
            .replace("^2", "-sqr")
            .replace("^3", "-cube")
            .replace(",", "-_")
        )

    def str_units(value):
        return (
            str(value)
            .split(",")[0]
            .replace("^2", "<sup>2</sup>")
            .replace("^3", "<sup>3</sup>")
        )

    return map_data, precisions, unitizer_stub, cls_units, str_units


@ui_showcase_bp.route("/", methods=["GET"])
def component_gallery() -> str:
    """Render the UI component showcase gallery."""
    map_data, precisions, unitizer_stub, cls_units, str_units = _build_unitizer_demo()

    sample = {
        "project_name": "South Fork Demo",
        "scenario": "baseline",
        "location": "Idaho, USA",
        "description": (
            "This gallery demonstrates the forthcoming Pure.css control shell "
            "and form macros. Use it to experiment with layout patterns before "
            "migrating production controls."
        ),
    }
    select_options = [
        ("baseline", "Baseline"),
        ("thinned", "Thinning Treatment"),
        ("mulch", "Mulching Treatment"),
    ]
    radio_options = [
        {
            "label": "Baseline",
            "value": "baseline",
            "description": "Use observed climate and current vegetation.",
            "selected": True,
        },
        {
            "label": "Mitigation",
            "value": "mitigation",
            "description": "Blend mulching and road hardening strategies.",
        },
        {
            "label": "Scenario Workspace",
            "value": "workspace",
            "description": "Switch to an offline draft using experimental inputs.",
            "disabled": True,
        },
    ]
    radio_mode_help = {
        "baseline": Markup(
            "<p>Ideal for quick analyses where the run aligns with current observations.</p>"
        ),
        "mitigation": Markup(
            "<p>Highlights mitigation levers; pairs well with the unitizer for real-time conversions.</p>"
        ),
        "workspace": Markup(
            "<p>Currently gated to editors while we stabilise the experimental workflow.</p>"
        ),
    }
    summary_rows = [
        {"parameter": "Slope Length", "value": "112", "units": "m"},
        {"parameter": "Average Gradient", "value": "18", "units": "%"},
        {"parameter": "Soil Texture", "value": "Sandy Loam", "units": "-"},
    ]
    sample_run = SimpleNamespace(
        runid="RX-2025-Preview",
        config_stem="cfg",
        name=sample["project_name"],
        scenario=sample["scenario"],
        readonly=False,
        public=True,
        pup_relpath=None,
    )

    theme_lab_sub_cmap_options = [
        {
            "id": "sub_cmap_radio_default",
            "label": "Default",
            "value": "default",
            "selected": True,
            "attrs": {"data-subcatchment-role": "cmap-option"},
        },
        {
            "id": "sub_cmap_radio_landuse_cover",
            "label": "Vegetation Cover (%)",
            "value": "landuse_cover",
            "attrs": {"data-subcatchment-role": "cmap-option"},
        },
        {
            "id": "sub_cmap_radio_dom_lc",
            "label": "Dominant Landcover",
            "value": "dom_lc",
            "attrs": {"data-subcatchment-role": "cmap-option"},
        },
    ]

    theme_contrast_targets = [
        {
            "id": "pure_button_primary",
            "label": "Primary button text vs background",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_primary_button",
                    "background": "#theme_lab_primary_button",
                }
            ],
        },
        {
            "id": "pure_button_secondary",
            "label": "Secondary button text vs background",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_secondary_button",
                    "background": "#theme_lab_secondary_button",
                }
            ],
        },
        {
            "id": "wc_field_help",
            "label": "Helper copy vs input background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "helper_vs_input",
                    "foreground": "#theme_lab_textfield_help",
                    "background": "#theme_lab_textfield",
                }
            ],
        },
        {
            "id": "wc_field_hint_text",
            "label": "Numeric hint vs input background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "hint_vs_input",
                    "foreground": "#theme_lab_numeric_help",
                    "background": "#theme_lab_numeric",
                }
            ],
        },
        {
            "id": "wc_text_muted",
            "label": "Muted copy vs surface",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "muted_vs_surface",
                    "foreground": "#theme_lab_muted_copy",
                    "background": "#theme_lab_muted_surface",
                }
            ],
        },
        {
            "id": "job_hint",
            "label": "Job hint vs surface",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "hint_vs_surface",
                    "foreground": "#theme_lab_job_hint",
                    "background": "#theme_lab_muted_surface",
                }
            ],
        },
        {
            "id": "wc_checkbox_checked",
            "label": "Readonly toggle (checked)",
            "threshold": 3.0,
            "actions": [{"type": "set_checked", "target": "#theme_lab_checkbox", "value": True}],
            "pairs": [
                {
                    "name": "checked_vs_surface",
                    "foreground": "#theme_lab_checkbox",
                    "background": "#theme_lab_checkbox_surface",
                }
            ],
        },
        {
            "id": "wc_checkbox_unchecked",
            "label": "Readonly toggle (unchecked)",
            "threshold": 3.0,
            "actions": [{"type": "set_checked", "target": "#theme_lab_checkbox", "value": False}],
            "pairs": [
                {
                    "name": "unchecked_vs_surface",
                    "foreground": "#theme_lab_checkbox",
                    "background": "#theme_lab_checkbox_surface",
                }
            ],
        },
        {
            "id": "wc_landuse_toggle_icon",
            "label": "Landuse wrench vs toggle background",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "icon_vs_button",
                    "foreground": "#theme_lab_landuse_toggle_icon",
                    "background": "#theme_lab_landuse_toggle",
                }
            ],
        },
        {
            "id": "pure_button_disabled",
            "label": "Disabled primary button text vs background",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_disabled_button",
                    "background": "#theme_lab_disabled_button",
                }
            ],
        },
        {
            "id": "sub_cmap_radio_default_checked",
            "label": "Subcatchment radio (checked) vs background",
            "threshold": 3.0,
            "actions": [{"type": "click", "target": "#sub_cmap_radio_default"}],
            "pairs": [
                {
                    "name": "checked_vs_background",
                    "foreground": "#sub_cmap_radio_default",
                    "background": "#theme_lab_subcmap_field",
                }
            ],
        },
        {
            "id": "sub_cmap_radio_default_unchecked",
            "label": "Subcatchment radio (unchecked) vs background",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "unchecked_vs_background",
                    "foreground": "#sub_cmap_radio_landuse_cover",
                    "background": "#theme_lab_subcmap_field",
                }
            ],
        },
        {
            "id": "sub_cmap_radio_checked_vs_unchecked",
            "label": "Subcatchment radio checked vs unchecked token",
            "threshold": 1.0,
            "pairs": [
                {
                    "name": "checked_vs_unchecked",
                    "foreground": "#sub_cmap_radio_default",
                    "background": "#sub_cmap_radio_landuse_cover",
                }
            ],
        },
        {
            "id": "leaflet_zoom_in",
            "label": "Leaflet zoom-in button",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_zoom_in",
                    "background": "#theme_lab_zoom_control",
                }
            ],
        },
        {
            "id": "leaflet_zoom_out",
            "label": "Leaflet zoom-out button",
            "threshold": 3.0,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_zoom_out",
                    "background": "#theme_lab_zoom_control",
                }
            ],
        },
    ]

    class SampleUser:
        is_authenticated = True

        @staticmethod
        def has_role(role: str) -> bool:
            return role == "Admin"

    return render_template(
        "ui_showcase/component_gallery.htm",
        sample=sample,
        select_options=select_options,
        radio_options=radio_options,
        radio_mode_help=radio_mode_help,
        summary_rows=summary_rows,
        current_ron=sample_run,
        user=SampleUser(),
        precisions=precisions,
        unitizer_nodb=unitizer_stub,
        cls_units=cls_units,
        str_units=str_units,
        unitizer_map=map_data,
        theme_options=THEME_OPTIONS,
        theme_lab_sub_cmap_options=theme_lab_sub_cmap_options,
        theme_contrast_targets=theme_contrast_targets,
    )
