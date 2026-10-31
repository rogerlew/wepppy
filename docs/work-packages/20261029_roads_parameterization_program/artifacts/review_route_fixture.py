"""Source-free entry point for privately retained Roads research instrumentation.

The implementation includes legacy source anchors and is retained in wepp-forest.
See private-research-tools.json and research-code-provenance.md for provenance.
This wrapper is original Codex code; it performs no model arithmetic itself.
"""
import os
from pathlib import Path
import runpy

if "WEPP_NATIVE_RESEARCH_TOOLS" not in os.environ:
    raise RuntimeError("Set WEPP_NATIVE_RESEARCH_TOOLS to the retained native private-tools directory; see research-code-provenance.md")
implementation = Path(os.environ["WEPP_NATIVE_RESEARCH_TOOLS"]) / Path(__file__).name
if not implementation.is_file():
    raise FileNotFoundError(implementation)
globals().update(runpy.run_path(str(implementation), run_name=__name__))
