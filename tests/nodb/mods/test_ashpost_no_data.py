from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

import wepppy.nodb.mods.ash_transport.ashpost as ashpost_module


pytestmark = pytest.mark.unit


def test_run_post_treats_no_data_as_success_and_updates_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ashpost = object.__new__(ashpost_module.AshPost)
    ashpost.wd = str(tmp_path)
    ashpost._return_periods = {2: {}}
    ashpost._cum_return_periods = {2: {}}
    ashpost._burn_class_return_periods = {1: {}}
    (tmp_path / "ash" / "post").mkdir(parents=True)

    @contextmanager
    def noop_lock():
        yield ashpost

    ashpost.locked = noop_lock
    monkeypatch.setattr(ashpost_module, "remove_incompatible_outputs", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ashpost_module, "watershed_daily_aggregated", lambda *_args, **_kwargs: None)

    def fail_if_called(*_args, **_kwargs) -> None:
        raise AssertionError("no-data AshPost must not publish normal dataset metadata")

    monkeypatch.setattr(ashpost_module, "write_version_manifest", fail_if_called)
    monkeypatch.setattr(ashpost_module, "generate_ashpost_documentation", fail_if_called)

    catalog_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        ashpost_module,
        "update_catalog_entry",
        lambda wd, key: catalog_calls.append((wd, key)),
    )

    ashpost.run_post()

    assert ashpost.return_periods is None
    assert ashpost.cum_return_periods is None
    assert ashpost.burn_class_return_periods is None
    assert catalog_calls == [(str(tmp_path), "ash")]


def test_native_manifest_preserves_watershed_order_and_independent_ash_ids(monkeypatch, tmp_path):
    import logging
    from types import SimpleNamespace
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.nodb.core import Watershed
    from wepppy.nodb.mods.ash_transport import Ash

    ash_dir = tmp_path/'ash'; ash_dir.mkdir()
    pq.write_table(pa.table({'wind_transport (tonne/ha)': [1.]}), ash_dir/'H2_ash.parquet')
    pq.write_table(pa.table({'wind_transport (tonne/ha)': [1.]}), ash_dir/'H1_ash.parquet')
    watershed = SimpleNamespace(_subs_summary={'22': None, '11': None, '33': None},
        translator_factory=lambda: SimpleNamespace(wepp=lambda top: {'11':1,'22':2,'33':3}[top]),
        hillslope_area=lambda key: {'11':10000.,'22':20000.,'33':30000.}[key])
    ash = SimpleNamespace(ash_dir=str(ash_dir),logger=logging.getLogger('test'),
        meta={'11': {'burn_class':1,'ash_type':None}, '22': {'burn_class':2,'ash_type':1},
              '33': {'burn_class':3,'ash_type':1}, '99': {'burn_class':3,'ash_type':1}})
    monkeypatch.setattr(Watershed,'getInstance',lambda wd: watershed)
    monkeypatch.setattr(Ash,'getInstance',lambda wd: ash)
    calls = []
    def native(*args,**kwargs):
        calls.append((args,kwargs))
        return dict(input_rows=2,rows_written={},return_periods={'daily':{}},
                    cum_return_periods={'cum':{}},burn_class_return_periods={})
    monkeypatch.setattr(ashpost_module,'require_wepppyo3_interchange',
        lambda *args: SimpleNamespace(ashpost_to_parquet=native))
    result = ashpost_module.watershed_daily_aggregated(str(tmp_path),recurrence=[2])
    args, kwargs = calls[0]
    assert args[2] == [('ash/H2_ash.parquet',22,2.,2),('ash/H1_ash.parquet',11,1.,1)]
    assert kwargs['ash_wepp_ids'] == [2,3]
    assert kwargs['hydrology_path'] is None and kwargs['wat_path'] is None
    assert kwargs['field_metadata']['wind_transport (tonne)']['units'] == 'tonne'
    assert result == ({'daily':{}},{'cum':{}},{})


def test_native_failure_does_not_publish_metadata_or_catalog(monkeypatch, tmp_path):
    ashpost = object.__new__(ashpost_module.AshPost)
    ashpost.wd = str(tmp_path)
    @contextmanager
    def lock():
        yield
    ashpost.locked = lock
    def fail(*args, **kwargs):
        raise ValueError('invalid native input')
    def unexpected(*args, **kwargs):
        raise AssertionError('failed post must not publish success')
    monkeypatch.setattr(ashpost_module,'watershed_daily_aggregated',fail)
    monkeypatch.setattr(ashpost_module,'write_version_manifest',unexpected)
    monkeypatch.setattr(ashpost_module,'generate_ashpost_documentation',unexpected)
    monkeypatch.setattr(ashpost_module,'update_catalog_entry',unexpected)
    with pytest.raises(ValueError,match='invalid native input'):
        ashpost.run_post()
