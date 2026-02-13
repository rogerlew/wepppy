import pytest

from wepppy.nodb.core.wepp import Wepp


pytestmark = pytest.mark.unit


class _DummyClimate:
    ss_batch_storms = []


class _DummyWepp:
    def __init__(self, *, output_dir: str, locked: bool = False) -> None:
        self.output_dir = output_dir
        self._locked = locked
        self.climate_instance = _DummyClimate()

    def islocked(self) -> bool:
        return self._locked


def test_has_run_true_with_interchange_loss_out_parquet(tmp_path):
    output_dir = tmp_path / "wepp" / "output"
    interchange_dir = output_dir / "interchange"
    interchange_dir.mkdir(parents=True)
    (interchange_dir / "loss_pw0.out.parquet").write_text("stub")

    dummy = _DummyWepp(output_dir=str(output_dir))
    assert Wepp.has_run.fget(dummy) is True


def test_has_run_false_when_locked_even_with_interchange_outputs(tmp_path):
    output_dir = tmp_path / "wepp" / "output"
    interchange_dir = output_dir / "interchange"
    interchange_dir.mkdir(parents=True)
    (interchange_dir / "loss_pw0.out.parquet").write_text("stub")

    dummy = _DummyWepp(output_dir=str(output_dir), locked=True)
    assert Wepp.has_run.fget(dummy) is False

