import logging
from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.treatments.treatments as treatments_module
from wepppy.soils.ssurgo import SoilSummary


class DummyWatershed:
    def translator_factory(self):
        return object()


class DummyManagementSummary:
    def __init__(self, disturbed_class: str):
        self.disturbed_class = disturbed_class


class FakeLanduse:
    _instance = None

    def __init__(self, domlc_d, managements, mapping):
        self.domlc_d = domlc_d
        self.managements = managements
        self._mapping = mapping
        self.dump_called = False
        self._locked = False

    @classmethod
    def getInstance(cls, wd):
        return cls._instance

    def get_mapping_dict(self):
        return self._mapping

    @contextmanager
    def locked(self):
        self._locked = True
        try:
            yield
        finally:
            self._locked = False

    def islocked(self):
        return self._locked

    def dump_landuse_parquet(self):
        self.dump_called = True


class FakeSoils:
    _instance = None

    def __init__(self):
        self._locked = False

    @classmethod
    def getInstance(cls, wd):
        return cls._instance

    @contextmanager
    def locked(self):
        self._locked = True
        try:
            yield
        finally:
            self._locked = False

    def islocked(self):
        return self._locked


class FakeDisturbed:
    _instance = None

    def __init__(self):
        self.land_soil_replacements_d = {}

    @classmethod
    def getInstance(cls, wd):
        return cls._instance


@pytest.mark.unit
def test_build_treatments_updates_domlc_and_dumps_parquet(monkeypatch, tmp_path):
    mapping = {"140": {"DisturbedClass": "thinning_40_75", "IsTreatment": True}}
    landuse = FakeLanduse(
        domlc_d={"101": "41"},
        managements={
            "41": DummyManagementSummary("forest"),
            "124": DummyManagementSummary("thinning_40_75"),
        },
        mapping=mapping,
    )
    soils = FakeSoils()
    disturbed = FakeDisturbed()

    FakeLanduse._instance = landuse
    FakeSoils._instance = soils
    FakeDisturbed._instance = disturbed

    monkeypatch.setattr(treatments_module, "Landuse", FakeLanduse)
    monkeypatch.setattr(treatments_module, "Soils", FakeSoils)

    import wepppy.nodb.mods.disturbed as disturbed_module

    monkeypatch.setattr(disturbed_module, "Disturbed", FakeDisturbed)

    treatments = treatments_module.Treatments.__new__(treatments_module.Treatments)
    treatments.wd = str(tmp_path)
    treatments.logger = logging.getLogger("test.treatments")
    treatments._treatments_domlc_d = {"101": "140"}

    apply_calls = []
    modify_calls = []

    def fake_apply(self, landuse_instance, disturbed_instance, topaz_id, treatment, man_summary, disturbed_class):
        apply_calls.append((topaz_id, treatment, disturbed_class))
        return "124"

    def fake_modify(self, landuse_instance, soils_instance, disturbed_instance, topaz_id):
        modify_calls.append(topaz_id)

    monkeypatch.setattr(treatments_module.Treatments, "_apply_treatment", fake_apply, raising=True)
    monkeypatch.setattr(treatments_module.Treatments, "_modify_soil", fake_modify, raising=True)

    import wepppy.nodb.core.watershed as watershed_module

    monkeypatch.setattr(
        watershed_module.Watershed,
        "getInstance",
        classmethod(lambda cls, wd: DummyWatershed()),
        raising=True,
    )

    treatments.build_treatments()

    assert landuse.domlc_d["101"] == "124"
    assert landuse.dump_called is True
    assert apply_calls == [("101", "thinning_40_75", "forest")]
    assert modify_calls == ["101"]


@pytest.mark.unit
def test_validate_map_uses_valid_pixels_only_without_global_mode_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    treatments_dir = tmp_path / "treatments"
    treatments_dir.mkdir(parents=True)
    source_map = treatments_dir / "source.tif"
    source_map.write_text("placeholder", encoding="ascii")

    subwta_path = tmp_path / "subwta.tif"
    subwta_path.write_text("placeholder", encoding="ascii")

    class _DummyDs:
        @staticmethod
        def GetProjection() -> str:
            return "EPSG:32611"

    class _DummyLanduse:
        @staticmethod
        def getInstance(_wd):
            return _DummyLanduse()

        @staticmethod
        def get_mapping_dict():
            return {
                "140": {"DisturbedClass": "thinning_40_75", "IsTreatment": True},
                "41": {"DisturbedClass": "forest", "IsTreatment": False},
            }

    class _DummyWatershed:
        def __init__(self, subwta: str) -> None:
            self.subwta = subwta

    monkeypatch.setattr(treatments_module.gdal, "Open", lambda _path: _DummyDs())
    monkeypatch.setattr(treatments_module, "validate_srs", lambda _srs: True)
    monkeypatch.setattr(
        treatments_module,
        "raster_stacker",
        lambda _src, _subwta, dst: Path(dst).write_text("stacked", encoding="ascii"),
    )
    monkeypatch.setattr(
        treatments_module,
        "count_intersecting_raster_key_pairs",
        # 101 has valid treatment pixels, 102 is intentionally absent (nodata-only/off-map).
        lambda **_kwargs: {"101": {"140": 12}},
    )
    monkeypatch.setattr(
        treatments_module,
        "Watershed",
        type(
            "_WatershedProxy",
            (),
            {"getInstance": staticmethod(lambda _wd: _DummyWatershed(str(subwta_path)))},
        ),
    )
    monkeypatch.setattr(treatments_module, "Landuse", _DummyLanduse)
    monkeypatch.setattr(
        treatments_module.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: (_ for _ in ()).throw(FileNotFoundError())),
    )

    treatments = treatments_module.Treatments.__new__(treatments_module.Treatments)
    treatments.wd = str(tmp_path)
    treatments.logger = logging.getLogger("test.treatments.validate")
    treatments._treatments_domlc_d = {}
    treatments._treatments = {}

    treatments.validate(str(source_map))

    assert treatments.treatments_domlc_d == {"101": "140"}
    # Key 102 had no valid treatment pixels and must remain unassigned.
    assert "102" not in treatments.treatments_domlc_d


@pytest.mark.unit
def test_modify_soil_does_not_strip_isric_composite_mukey(tmp_path):
    class DummySoil:
        def __init__(self, clay: float, sand: float):
            self.clay = clay
            self.sand = sand

    class DummySoils:
        def __init__(self):
            self._locked = False
            self.domsoil_d = {"101": "Cambisols-clay loam"}
            # Key must be the full composite mukey (ISRIC uses WRB-texture IDs).
            self.soils = {"Cambisols-clay loam": DummySoil(clay=30.0, sand=30.0)}

        @contextmanager
        def locked(self):
            self._locked = True
            try:
                yield
            finally:
                self._locked = False

        def islocked(self):
            return self._locked

    class DummyDisturbed:
        sol_ver = 7778.0
        land_soil_replacements_d = {}

    landuse = FakeLanduse(
        domlc_d={"101": "41"},
        managements={"41": DummyManagementSummary("forest")},
        mapping={},
    )
    soils = DummySoils()
    disturbed = DummyDisturbed()

    treatments = treatments_module.Treatments.__new__(treatments_module.Treatments)
    treatments.wd = str(tmp_path)
    treatments.logger = logging.getLogger("test.treatments.modify_soil")

    with soils.locked():
        treatments._modify_soil(landuse, soils, disturbed, "101")


@pytest.mark.unit
def test_modify_soil_uses_parent_soil_file_when_clone_file_missing(monkeypatch, tmp_path):
    class DummySoils:
        def __init__(self, base_soil, parent_wd, soils_dir):
            self._locked = False
            self.parent_wd = parent_wd
            self.soils_dir = soils_dir
            self.domsoil_d = {"101": "763002"}
            self.soils = {"763002": base_soil}

        @contextmanager
        def locked(self):
            self._locked = True
            try:
                yield
            finally:
                self._locked = False

        def islocked(self):
            return self._locked

    class DummyDisturbed:
        sol_ver = 9005.0
        h0_max_om = 0.15
        land_soil_replacements_d = {("mock-texture", "forest high sev fire"): {"ki": 1.0}}

    parent_wd = tmp_path / "parent"
    parent_soils_dir = parent_wd / "soils"
    parent_soils_dir.mkdir(parents=True)
    (parent_soils_dir / "763002.sol").write_text("placeholder", encoding="utf-8")

    child_wd = tmp_path / "child"
    child_soils_dir = child_wd / "soils"
    child_soils_dir.mkdir(parents=True)

    base_soil = SoilSummary(
        mukey="763002",
        fname="763002.sol",
        soils_dir=str(child_soils_dir),
        build_date="2026-01-01T00:00:00",
        desc="base soil",
    )
    soils = DummySoils(base_soil, str(parent_wd), str(child_soils_dir))

    landuse = FakeLanduse(
        domlc_d={"101": "41"},
        managements={"41": DummyManagementSummary("forest high sev fire")},
        mapping={},
    )
    disturbed = DummyDisturbed()

    class _FakeWriter:
        def __init__(self, write_paths):
            self._write_paths = write_paths

        def write(self, fn):
            self._write_paths.append(fn)

    call_paths = []
    write_paths = []
    to_over9000_kwargs = {}

    class FakeWeppSoilUtil:
        def __init__(self, fn):
            call_paths.append(fn)
            self.clay = 30.0
            self.sand = 40.0

        def to_over9000(self, replacements, h0_max_om=None, version=None):
            to_over9000_kwargs.update(
                replacements=replacements,
                h0_max_om=h0_max_om,
                version=version,
            )
            return _FakeWriter(write_paths)

    monkeypatch.setattr(treatments_module, "simple_texture", lambda clay, sand: "mock-texture")
    monkeypatch.setattr(treatments_module, "WeppSoilUtil", FakeWeppSoilUtil)

    treatments = treatments_module.Treatments.__new__(treatments_module.Treatments)
    treatments.wd = str(child_wd)
    treatments.logger = logging.getLogger("test.treatments.modify_soil.parent_fallback")

    with soils.locked():
        treatments._modify_soil(landuse, soils, disturbed, "101")

    expected_source = str(parent_soils_dir / "763002.sol")
    expected_mukey = "763002-mock-texture-forest high sev fire"
    expected_output = str(child_soils_dir / f"{expected_mukey}.sol")

    assert call_paths == [expected_source]
    assert write_paths == [expected_output]
    assert soils.domsoil_d["101"] == expected_mukey
    assert expected_mukey in soils.soils
    assert to_over9000_kwargs["replacements"] == {"ki": 1.0}
    assert to_over9000_kwargs["h0_max_om"] == disturbed.h0_max_om
    assert to_over9000_kwargs["version"] == disturbed.sol_ver
