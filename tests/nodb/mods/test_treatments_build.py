import logging
from contextlib import contextmanager

import pytest

import wepppy.nodb.mods.treatments.treatments as treatments_module


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
