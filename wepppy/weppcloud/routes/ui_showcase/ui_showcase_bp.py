from collections import OrderedDict
import os
from types import SimpleNamespace
from markupsafe import Markup
from flask import Blueprint, render_template, current_app

from wepppy.weppcloud.controllers_js import unitizer_map_builder

ui_showcase_bp = Blueprint("ui_showcase", __name__, url_prefix="/ui/components")


THEME_OPTIONS = [
    ("default", "Default (Light) · AA checked"),
    ("light-high-contrast", "High Contrast (Light) · AA checked"),
    ("onedark", "OneDark · Sensory preference"),
    ("dark-modern", "Dark Modern · Sensory preference"),
    ("ayu-dark", "Ayu Dark · Sensory preference"),
    ("ayu-mirage", "Ayu Mirage · AA checked"),
    ("ayu-light", "Ayu Light · Sensory preference"),
    ("ayu-dark-bordered", "Ayu Dark · Bordered · Sensory preference"),
    ("ayu-mirage-bordered", "Ayu Mirage · Bordered · AA checked"),
    ("ayu-light-bordered", "Ayu Light · Bordered · Sensory preference"),
    ("cursor-dark-anysphere", "Cursor Dark (Anysphere) · Sensory preference"),
    ("cursor-dark-midnight", "Cursor Dark (Midnight) · AA checked"),
    ("cursor-dark-high-contrast", "Cursor Dark (High Contrast) · Sensory preference"),
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
    cap_base_url = (
        current_app.config.get("CAP_BASE_URL")
        or os.getenv("CAP_BASE_URL")
        or "/cap"
    ).rstrip("/")
    cap_site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY", "demo")

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
            "<p>Ideal for quick analyzes where the run aligns with current observations.</p>"
        ),
        "mitigation": Markup(
            "<p>Highlights mitigation levers; pairs well with the unitizer for real-time conversions.</p>"
        ),
        "workspace": Markup(
            "<p>Currently gated to editors while we stabilize the experimental workflow.</p>"
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

    geneva_marker_series = [
        {"id": "series_0", "marker_class": "geneva-summary__marker-circle--0"},
        {"id": "series_1", "marker_class": "geneva-summary__marker-circle--1"},
        {"id": "series_2", "marker_class": "geneva-summary__marker-circle--2"},
        {"id": "series_3", "marker_class": "geneva-summary__marker-circle--3"},
        {"id": "series_4", "marker_class": "geneva-summary__marker-circle--4"},
        {"id": "series_fallback", "marker_class": "geneva-summary__marker-circle--fallback"},
    ]
    geneva_marker_labels = [
        {"id": "label_5m", "text": "5m"},
        {"id": "label_10m", "text": "10m"},
        {"id": "label_15m", "text": "15m"},
        {"id": "label_30m", "text": "30m"},
        {"id": "label_1h", "text": "1h"},
        {"id": "label_2h", "text": "2h"},
        {"id": "label_3h", "text": "3h"},
        {"id": "label_6h", "text": "6h"},
        {"id": "label_12h", "text": "12h"},
        {"id": "label_24h", "text": "24h"},
    ]
    geneva_marker_combinations = [
        {
            "id": f"{series['id']}_{label['id']}",
            "label": label["text"],
            "marker_class": series["marker_class"],
            "x": 42 + label_index * 54,
            "y": 34 + series_index * 44,
        }
        for series_index, series in enumerate(geneva_marker_series)
        for label_index, label in enumerate(geneva_marker_labels)
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
                },
                {
                    "name": "border_vs_background",
                    "foreground": "#theme_lab_secondary_button",
                    "background": "#theme_lab_secondary_button",
                    "foreground_mode": "border",
                    "aa_kind": "non_text",
                },
                {
                    "name": "disabled_border_vs_background",
                    "foreground": "#theme_lab_secondary_button_disabled",
                    "background": "#theme_lab_secondary_button_disabled",
                    "foreground_mode": "border",
                    "aa_kind": "non_text",
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
            "id": "wc_textbox_help",
            "label": "Textbox helper copy vs input background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "helper_vs_textbox",
                    "foreground": "#theme_lab_textbox_help",
                    "background": "#theme_lab_textbox",
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
            "id": "wc_field_spin_button",
            "label": "Numeric spin button vs input background",
            "threshold": 3.0,
            "aa_kind": "non_text",
            "pairs": [
                {
                    "name": "spin_vs_input",
                    "foreground": "#theme_lab_numeric",
                    "background": "#theme_lab_numeric",
                    "foreground_pseudo": "::-webkit-inner-spin-button",
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
            "id": "wc-return-period-measure",
            "label": "Return-period selected measure column",
            "pairs": [
                {
                    "name": "header_text_vs_highlight",
                    "foreground": "#theme_lab_return_period_measure_header",
                    "background": "#theme_lab_return_period_measure_header",
                },
                {
                    "name": "value_text_vs_highlight",
                    "foreground": "#theme_lab_return_period_measure_value",
                    "background": "#theme_lab_return_period_measure_value",
                },
            ],
        },
        {
            "id": "geneva_summary_marker_labels",
            "label": "Geneva summary marker labels",
            "pairs": [
                {
                    "name": marker["id"],
                    "foreground": f"#theme_lab_geneva_marker_{marker['id']}_label",
                    "foreground_mode": "fill",
                    "background": f"#theme_lab_geneva_marker_{marker['id']}_circle",
                    "background_mode": "fill",
                }
                for marker in geneva_marker_combinations
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
            "id": "wc_status_chip_success",
            "label": "Status chip success text vs background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_status_chip_success",
                    "background": "#theme_lab_status_chip_success",
                }
            ],
        },
        {
            "id": "browse_parquet_preview_banner",
            "label": "Browse parquet preview banner",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "preview_title_vs_banner",
                    "foreground": "#theme_lab_browse_preview_title",
                    "background": "#theme_lab_browse_preview_banner",
                },
                {
                    "name": "preview_message_vs_banner",
                    "foreground": "#theme_lab_browse_preview_message",
                    "background": "#theme_lab_browse_preview_banner",
                },
                {
                    "name": "filter_title_vs_banner",
                    "foreground": "#theme_lab_browse_filter_title",
                    "background": "#theme_lab_browse_preview_banner",
                },
                {
                    "name": "filter_summary_vs_banner",
                    "foreground": "#theme_lab_browse_filter_summary",
                    "background": "#theme_lab_browse_preview_banner",
                },
                {
                    "name": "filter_code_vs_code_background",
                    "foreground": "#theme_lab_browse_filter_code",
                    "background": "#theme_lab_browse_filter_code",
                },
                {
                    "name": "action_text_vs_background",
                    "foreground": "#theme_lab_browse_preview_action",
                    "background": "#theme_lab_browse_preview_action",
                },
                {
                    "name": "action_border_vs_background",
                    "foreground": "#theme_lab_browse_preview_action",
                    "background": "#theme_lab_browse_preview_action",
                    "foreground_mode": "border",
                    "aa_kind": "non_text",
                    "threshold": 3.0,
                },
            ],
        },
        {
            "id": "wc_checkbox_checked",
            "label": "Readonly toggle (checked)",
            "threshold": 3.0,
            "aa_kind": "non_text",
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
            "aa_kind": "non_text",
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
            "aa_kind": "non_text",
            "pairs": [
                {
                    "name": "icon_vs_button",
                    "foreground": "#theme_lab_landuse_toggle_icon",
                    "background": "#theme_lab_landuse_toggle",
                }
            ],
        },
        {
            "id": "wc_cap_checkbox",
            "label": "Cap checkbox border vs surface",
            "threshold": 3.0,
            "aa_kind": "non_text",
            "pairs": [
                {
                    "name": "border_vs_surface",
                    "foreground": "#theme_lab_cap_checkbox",
                    "background": "#theme_lab_cap_checkbox",
                    "foreground_mode": "border",
                }
            ],
        },
        {
            "id": "wc_cap_checkbox_verified",
            "label": "Cap checkbox verified vs background",
            "threshold": 3.0,
            "aa_kind": "non_text",
            "pairs": [
                {
                    "name": "verified_border_vs_background",
                    "foreground": "#theme_lab_cap_checkbox_verified",
                    "background": "#theme_lab_cap_checkbox_verified",
                    "foreground_mode": "border",
                }
            ],
        },
        {
            "id": "wc_select_disabled",
            "label": "Disabled select text vs background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_disabled_select",
                    "background": "#theme_lab_disabled_select",
                }
            ],
        },
        {
            "id": "wc_input_disabled",
            "label": "Disabled input text vs background",
            "threshold": 4.5,
            "pairs": [
                {
                    "name": "text_vs_background",
                    "foreground": "#theme_lab_disabled_input",
                    "background": "#theme_lab_disabled_input",
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
            "id": "wc_jexcel_table",
            "label": "JSpreadsheet cell state surfaces",
            "aa_exempt": True,
            "pairs": [
                {
                    "name": "thead_selected_text_vs_background",
                    "foreground": "#theme_lab_jexcel_header_selected",
                    "background": "#theme_lab_jexcel_header_selected",
                },
                {
                    "name": "tbody_selected_text_vs_background",
                    "foreground": "#theme_lab_jexcel_selected_cell",
                    "background": "#theme_lab_jexcel_selected_cell",
                },
                {
                    "name": "tbody_row_index_text_vs_background",
                    "foreground": "#theme_lab_jexcel_row_index",
                    "background": "#theme_lab_jexcel_row_index",
                },
                {
                    "name": "tbody_regular_text_vs_background",
                    "foreground": "#theme_lab_jexcel_regular_cell",
                    "background": "#theme_lab_jexcel_regular_cell",
                },
            ],
        },
        {
            "id": "sub_cmap_radio_default_checked",
            "label": "Subcatchment radio (checked) vs background",
            "threshold": 3.0,
            "aa_kind": "non_text",
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
            "aa_kind": "non_text",
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
            "aa_exempt": True,
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
            "aa_kind": "non_text",
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
            "aa_kind": "non_text",
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
        geneva_marker_combinations=geneva_marker_combinations,
        theme_contrast_targets=theme_contrast_targets,
        cap_base_url=cap_base_url,
        cap_site_key=cap_site_key,
    )


@ui_showcase_bp.route("/report-a11y", methods=["GET"])
def report_accessibility_probe() -> str:
    """Render a report-like accessibility probe page for axe scans."""
    summary_cards = [
        {"label": "Runoff depth", "value": "42.7 mm", "change": "12% below baseline"},
        {"label": "Sediment yield", "value": "0.31 t/ha", "change": "8% above baseline"},
        {"label": "Peak discharge", "value": "1.92 m³/s", "change": "3-year recurrence"},
        {"label": "Simulation years", "value": "2005-2025", "change": "21 annual events"},
    ]

    outlet_rows = [
        {"metric": "Runoff", "value": "42.7", "units": "mm", "per_area": "427", "per_area_units": "m³/ha"},
        {"metric": "Sediment yield", "value": "0.31", "units": "t/ha", "per_area": "0.31", "per_area_units": "t/ha"},
        {"metric": "Peak discharge", "value": "1.92", "units": "m³/s", "per_area": "0.019", "per_area_units": "m³/s/ha"},
        {"metric": "Total phosphorus", "value": "0.84", "units": "kg", "per_area": "0.008", "per_area_units": "kg/ha"},
    ]

    hillslope_rows = [
        {"id": "H01", "length": "112", "slope": "0.18", "runoff": "38.6", "sediment": "0.22"},
        {"id": "H02", "length": "146", "slope": "0.21", "runoff": "44.1", "sediment": "0.37"},
        {"id": "H03", "length": "98", "slope": "0.16", "runoff": "40.2", "sediment": "0.28"},
    ]

    month_filters = [
        {"value": "11", "label": "November", "checked": True},
        {"value": "12", "label": "December", "checked": True},
        {"value": "1", "label": "January", "checked": False},
        {"value": "2", "label": "February", "checked": False},
    ]

    return render_template(
        "ui_showcase/report_accessibility_probe.htm",
        summary_cards=summary_cards,
        outlet_rows=outlet_rows,
        hillslope_rows=hillslope_rows,
        month_filters=month_filters,
    )
