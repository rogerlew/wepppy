"""Security-related blueprints for WEPPcloud."""

from .logging import security_bp as security_logging_bp
from .oauth import security_oauth_bp
from .ui import security_bp as security_ui_bp

# Backwards compatibility: existing imports expect `security_bp`
security_bp = security_logging_bp

__all__ = [
    "security_logging_bp",
    "security_ui_bp",
    "security_oauth_bp",
    "security_bp",
]
