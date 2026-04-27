from __future__ import annotations


class GroupedSoilsDummy:
    class_name = "soils"

    def __init__(
        self,
        *,
        clip_soils: bool = False,
        clip_soils_depth: object | None = None,
        clip_soils_minimum: bool = False,
        clip_soils_minimum_depth: object | None = 0.0,
        rosetta_wc_fc_from_disturbed_bd_override: bool = False,
        initial_sat: object | None = None,
    ) -> None:
        self.clip_soils = clip_soils
        self.clip_soils_depth = clip_soils_depth
        self.clip_soils_minimum = clip_soils_minimum
        self.clip_soils_minimum_depth = clip_soils_minimum_depth
        self.rosetta_wc_fc_from_disturbed_bd_override = rosetta_wc_fc_from_disturbed_bd_override
        self.initial_sat = initial_sat
        self.grouped_update_calls: list[dict[str, object | None]] = []
        self.dump_calls: list[dict[str, object | None]] = []
        self._locked = False

    def lock(self) -> None:
        if self._locked:
            raise RuntimeError("already locked")
        self._locked = True

    def unlock(self) -> None:
        self._locked = False

    def dump(self) -> None:
        if not self._locked:
            raise RuntimeError("cannot dump without lock")
        self.dump_calls.append(self.snapshot_wepp_run_payload_updates())

    def snapshot_wepp_run_payload_updates(self) -> dict[str, object | None]:
        return {
            "clip_soils": self.clip_soils,
            "clip_soils_depth": self.clip_soils_depth,
            "clip_soils_minimum": self.clip_soils_minimum,
            "clip_soils_minimum_depth": self.clip_soils_minimum_depth,
            "rosetta_wc_fc_from_disturbed_bd_override": self.rosetta_wc_fc_from_disturbed_bd_override,
            "initial_sat": self.initial_sat,
        }

    def restore_wepp_run_payload_updates(self, snapshot: dict[str, object | None]) -> None:
        self.clip_soils = bool(snapshot["clip_soils"])
        self.clip_soils_depth = snapshot["clip_soils_depth"]
        self.clip_soils_minimum = bool(snapshot["clip_soils_minimum"])
        self.clip_soils_minimum_depth = snapshot["clip_soils_minimum_depth"]
        self.rosetta_wc_fc_from_disturbed_bd_override = bool(
            snapshot["rosetta_wc_fc_from_disturbed_bd_override"]
        )
        self.initial_sat = snapshot["initial_sat"]

    def stage_wepp_run_payload_updates(
        self,
        *,
        clip_soils: object | None = None,
        clip_soils_depth: object | None = None,
        clip_soils_minimum: object | None = None,
        clip_soils_minimum_depth: object | None = None,
        rosetta_wc_fc_from_disturbed_bd_override: object | None = None,
        initial_sat: object | None = None,
    ) -> bool:
        has_updates = any(
            value is not None
            for value in (
                clip_soils,
                clip_soils_depth,
                clip_soils_minimum,
                clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat,
            )
        )
        if not has_updates:
            return False
        self.grouped_update_calls.append(
            {
                "clip_soils": clip_soils,
                "clip_soils_depth": clip_soils_depth,
                "clip_soils_minimum": clip_soils_minimum,
                "clip_soils_minimum_depth": clip_soils_minimum_depth,
                "rosetta_wc_fc_from_disturbed_bd_override": rosetta_wc_fc_from_disturbed_bd_override,
                "initial_sat": initial_sat,
            }
        )
        if clip_soils is not None:
            self.clip_soils = bool(clip_soils)
        if clip_soils_depth is not None:
            self.clip_soils_depth = clip_soils_depth
        if clip_soils_minimum is not None:
            self.clip_soils_minimum = bool(clip_soils_minimum)
        if clip_soils_minimum_depth is not None:
            self.clip_soils_minimum_depth = clip_soils_minimum_depth
        if rosetta_wc_fc_from_disturbed_bd_override is not None:
            self.rosetta_wc_fc_from_disturbed_bd_override = bool(
                rosetta_wc_fc_from_disturbed_bd_override
            )
        if initial_sat is not None:
            self.initial_sat = initial_sat
        return True

    def apply_wepp_run_payload_updates(
        self,
        *,
        clip_soils: object | None = None,
        clip_soils_depth: object | None = None,
        clip_soils_minimum: object | None = None,
        clip_soils_minimum_depth: object | None = None,
        rosetta_wc_fc_from_disturbed_bd_override: object | None = None,
        initial_sat: object | None = None,
    ) -> None:
        self.lock()
        try:
            if not self.stage_wepp_run_payload_updates(
                clip_soils=clip_soils,
                clip_soils_depth=clip_soils_depth,
                clip_soils_minimum=clip_soils_minimum,
                clip_soils_minimum_depth=clip_soils_minimum_depth,
                rosetta_wc_fc_from_disturbed_bd_override=rosetta_wc_fc_from_disturbed_bd_override,
                initial_sat=initial_sat,
            ):
                return
            self.dump()
        finally:
            self.unlock()


class GroupedWatershedDummy:
    class_name = "watershed"

    def __init__(
        self,
        *,
        clip_hillslopes: bool = False,
        clip_hillslope_length: object | None = None,
        has_subcatchments: bool = True,
    ) -> None:
        self.clip_hillslopes = clip_hillslopes
        self.clip_hillslope_length = clip_hillslope_length
        self.has_subcatchments = has_subcatchments
        self.grouped_update_calls: list[dict[str, object | None]] = []
        self.dump_calls: list[dict[str, object | None]] = []
        self._locked = False

    def lock(self) -> None:
        if self._locked:
            raise RuntimeError("already locked")
        self._locked = True

    def unlock(self) -> None:
        self._locked = False

    def dump(self) -> None:
        if not self._locked:
            raise RuntimeError("cannot dump without lock")
        self.dump_calls.append(self.snapshot_wepp_run_payload_updates())

    def snapshot_wepp_run_payload_updates(self) -> dict[str, object | None]:
        return {
            "clip_hillslopes": self.clip_hillslopes,
            "clip_hillslope_length": self.clip_hillslope_length,
        }

    def restore_wepp_run_payload_updates(self, snapshot: dict[str, object | None]) -> None:
        self.clip_hillslopes = bool(snapshot["clip_hillslopes"])
        self.clip_hillslope_length = snapshot["clip_hillslope_length"]

    def stage_wepp_run_payload_updates(
        self,
        *,
        clip_hillslopes: object | None = None,
        clip_hillslope_length: object | None = None,
    ) -> bool:
        if clip_hillslopes is None and clip_hillslope_length is None:
            return False
        self.grouped_update_calls.append(
            {
                "clip_hillslopes": clip_hillslopes,
                "clip_hillslope_length": clip_hillslope_length,
            }
        )
        if clip_hillslopes is not None:
            self.clip_hillslopes = bool(clip_hillslopes)
        if clip_hillslope_length is not None:
            self.clip_hillslope_length = clip_hillslope_length
        return True

    def apply_wepp_run_payload_updates(
        self,
        *,
        clip_hillslopes: object | None = None,
        clip_hillslope_length: object | None = None,
    ) -> None:
        self.lock()
        try:
            if not self.stage_wepp_run_payload_updates(
                clip_hillslopes=clip_hillslopes,
                clip_hillslope_length=clip_hillslope_length,
            ):
                return
            self.dump()
        finally:
            self.unlock()
