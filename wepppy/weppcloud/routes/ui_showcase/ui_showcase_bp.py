from markupsafe import Markup
from flask import Blueprint, render_template


ui_showcase_bp = Blueprint("ui_showcase", __name__, url_prefix="/ui/components")


@ui_showcase_bp.route("/", methods=["GET"])
def component_gallery() -> str:
    """Render the UI component showcase gallery."""
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
    return render_template(
        "ui_showcase/component_gallery.htm",
        sample=sample,
        select_options=select_options,
        radio_options=radio_options,
        radio_mode_help=radio_mode_help,
        summary_rows=summary_rows,
    )
