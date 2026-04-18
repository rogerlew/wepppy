from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from wepppy.nodb.mods.geneva.schemas import config_from_mapping, default_geneva_config, merge_config

if TYPE_CHECKING:
    from wepppy.nodb.mods.geneva.geneva import Geneva


class GenevaConfigService:
    """Manage normalized Geneva config payloads."""

    def initialize_config(self, geneva: "Geneva") -> dict[str, Any]:
        if not hasattr(geneva, "_config"):
            geneva._config = default_geneva_config().to_payload()
        else:
            geneva._config = config_from_mapping(geneva._config).to_payload()
        # Migrate legacy default behavior for untouched runs so first HRU prep does
        # not fail on unresolved HSG cells.
        if (
            not bool(getattr(geneva, "_config_user_modified", False))
            and geneva._config.get("unresolved_hsg_policy") == "error"
            and geneva._config.get("default_hsg_code") in (None, "")
        ):
            geneva._config["unresolved_hsg_policy"] = "assume_d"
        return dict(geneva._config)

    def get_config(self, geneva: "Geneva") -> dict[str, Any]:
        return config_from_mapping(geneva._config).to_payload()

    def update_config(self, geneva: "Geneva", updates: Mapping[str, Any]) -> dict[str, Any]:
        current = self.get_config(geneva)
        merged = merge_config(current, updates)
        geneva._config = merged.to_payload()
        return dict(geneva._config)


__all__ = ["GenevaConfigService"]
