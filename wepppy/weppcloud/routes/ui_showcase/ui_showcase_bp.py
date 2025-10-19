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
    return render_template(
        "ui_showcase/component_gallery.htm",
        sample=sample,
        select_options=select_options,
    )
