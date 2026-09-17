"""Disposable actual upload/parser/orchestration and recorder/replay probes.

No named run, queue, model executable or external request is used. Omni's costly
scenario executor is a recording seam; the actual decision to call/skip it is
production code. Recorder controller acquisition alone is injected.
"""
from contextlib import nullcontext
from io import BytesIO
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from osgeo import gdal, osr
from starlette.datastructures import FormData, UploadFile
from wepppy.microservices.rq_engine.omni_routes import _prepare_omni_scenarios
from wepppy.nodb.mods.omni.omni import OmniScenario, _scenario_name_from_scenario_definition
from wepppy.nodb.mods.omni.omni_input_parser import OmniInputParsingService
from wepppy.nodb.mods.omni.omni_run_orchestration_service import OmniRunOrchestrationService
from wepppy.nodb.mods.omni.omni_station_catalog_service import OmniStationCatalogService
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.mods.baer import Baer
from wepppy.profile_recorder.assembler import ProfileAssembler
from wepppy.profile_recorder.playback import PlaybackSession


def raster(path, value):
    ds = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 4400000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(np.full((2, 2), value, dtype=np.uint8))
    ds = None


def pixels(path):
    ds = gdal.Open(str(path))
    return ds.ReadAsArray().tolist()


class ScenarioContext:
    def __init__(self, root):
        self.wd = str(root)
        self.logger = logging.getLogger("freshness-probe")
        self.base_scenario = OmniScenario.Undisturbed
        self.scenario_dependency_tree = {}
        self.scenario_run_state = []
        self._scenarios = []
        self.executions = []
        self.loss = root / "base-loss.parquet"
        self.years = root / "years.parquet"
        pd.DataFrame({"loss": [25.0]}).to_parquet(self.loss)
        pd.DataFrame({"year": [2020]}).to_parquet(self.years)

    @property
    def scenarios(self):
        return self._scenarios

    def locked(self):
        return nullcontext()

    def _scenario_dependency_target(self, scenario, definition):
        return OmniStationCatalogService().scenario_dependency_target(self, scenario, definition)

    def _scenario_signature(self, definition):
        return OmniStationCatalogService().scenario_signature(self, definition)

    def _loss_pw0_path_for_scenario(self, scenario):
        return str(self.loss)

    def _year_set_for_scenario(self, scenario):
        return set(pd.read_parquet(self.years)["year"])

    def _normalize_scenario_key(self, scenario):
        return str(scenario)

    def run_omni_scenario(self, definition):
        self.executions.append(pixels(definition["sbs_file_path"]))
        return self.wd, _scenario_name_from_scenario_definition(definition)

    def _post_omni_run(self, *args):
        pass

    def compile_hillslope_summaries(self):
        pass

    def compile_channel_summaries(self):
        pass

    def scenarios_report(self):
        pass


with TemporaryDirectory(prefix="remaining-freshness-") as temporary:
    root = Path(temporary)
    upload_source = root / "sbs.tif"
    omni_root = root / "omni-probe"
    omni_root.mkdir()
    context = ScenarioContext(omni_root)
    paths, statuses = [], []
    for value in (1, 3):
        raster(upload_source, value)
        upload = UploadFile(filename="sbs.tif", file=BytesIO(upload_source.read_bytes()))
        parsed = _prepare_omni_scenarios(
            {"scenarios": [{"type": "sbs_map"}]}, None,
            FormData([("scenarios[0][sbs_file]", upload)]),
            runid="probe", config="test", wd=str(omni_root),
        )
        OmniInputParsingService().parse_scenarios(context, parsed)
        paths.append(context.scenarios[0]["sbs_file_path"])
        OmniRunOrchestrationService().run_omni_scenarios(context)
        statuses.append(context.scenario_run_state[0]["status"])
    omni_result = {
        "same_uploaded_path": paths[0] == paths[1], "statuses": statuses,
        "actual_current_pixels": pixels(paths[1]), "executor_observed_pixels": context.executions,
        "scope": "actual upload/parser/orchestrator; scenario execution is a recording seam",
    }
    assert statuses == ["executed", "skipped"]
    assert len(context.executions) == 1

    run_root = root / "profile-source"
    sbs_dir = run_root / "disturbed"
    sbs_dir.mkdir(parents=True)
    source = sbs_dir / "sbs.tif"
    data_root = root / "profile-data"
    assembler = ProfileAssembler(data_root)
    with patch.object(Disturbed, "getInstance", return_value=SimpleNamespace(disturbed_path=str(source))), patch.object(
        Baer, "getInstance", return_value=SimpleNamespace(baer_path=None),
    ):
        for value in (1, 3):
            raster(source, value)
            assembler.handle_event("probe", "capture", {
                "stage": "response", "category": "file_upload", "ok": True,
                "endpoint": "/rq-engine/api/tasks/upload-sbs", "request_id": f"upload-{value}",
            }, run_root)
    draft = data_root / "profiles" / "_drafts" / "probe" / "capture"
    session = object.__new__(PlaybackSession)
    session.seed_upload_root = draft / "seed" / "uploads"
    session.run_dir = root / "unused-sandbox"
    session.profile_run_root = run_root
    rebuilt = []
    for request_id in ("upload-1", "upload-3"):
        _, files = session._build_form_request("/rq-engine/api/tasks/upload-sbs", {"request_id": request_id})
        rebuilt.append(pixels(files["input_upload_sbs"][0]))
    profile_result = {
        "recorded_event_count": len((draft / "events.jsonl").read_text().splitlines()),
        "actual_current_pixels": pixels(source),
        "latest_named_seed_pixels": pixels(session.seed_upload_root / "sbs" / "sbs.tif"),
        "canonical_seed_pixels": pixels(session.seed_upload_root / "sbs" / "input_upload_sbs.tif"),
        "rebuilt_upload_pixels": rebuilt,
        "scope": "actual assembler and multipart reconstruction; no HTTP playback",
    }
    assert rebuilt == [[[1, 1], [1, 1]], [[1, 1], [1, 1]]]
    print(json.dumps({"omni_reupload": omni_result, "profile_reupload": profile_result}, indent=2))
