from __future__ import annotations

from typing import Optional

import awesome_codename


def generate_runid(email: Optional[str] = None) -> str:
    """Generate a new run id using the standard create-run rules."""
    runid = awesome_codename.generate_codename().replace(" ", "-").replace("'", "")

    email_value = email or ""
    if email_value.startswith("mdobre@"):
        runid = f"mdobre-{runid}"
    elif email_value.startswith("srivas42@"):
        runid = f"srivas42-{runid}"

    return runid
