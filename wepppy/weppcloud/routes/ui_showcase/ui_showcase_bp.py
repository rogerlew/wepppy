from collections import OrderedDict
from types import SimpleNamespace
from markupsafe import Markup
from flask import Blueprint, render_template

from wepppy.weppcloud.controllers_js import unitizer_map_builder

ui_showcase_bp = Blueprint("ui_showcase", __name__, url_prefix="/ui/components")


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
    )
