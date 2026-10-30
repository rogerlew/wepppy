"""Native auxiliary inputs and activation must agree with the declared runtime."""
import importlib.util
from pathlib import Path
import pytest

pytestmark=pytest.mark.unit
PATH=Path(__file__).resolve().parents[2]/'docs/work-packages/20261029_roads_drainage_validation/artifacts/analyze.py'
SPEC=importlib.util.spec_from_file_location('roads_drainage_runtime_analysis',PATH)
a=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(a)


def prepared(tmp_path):
    runs=tmp_path/'runs';runs.mkdir()
    for name in ('p1.sol','reference.sol','stdout','stderr'):(runs/name).write_text('')
    return dict(inputs={'p1.sol':'unused-by-runtime-check'})


def test_undeclared_sidecar_rejected(tmp_path):
    record=prepared(tmp_path)
    a.validate_runtime(tmp_path,{},record)
    (tmp_path/'runs/snow.txt').write_text('unexpected model option')
    with pytest.raises(ValueError,match='Unrecorded'):a.validate_runtime(tmp_path,{},record)


@pytest.mark.parametrize('file_present,banner_present',[(True,False),(False,True),(False,False)])
def test_ui_request_requires_file_and_native_activation(tmp_path,file_present,banner_present):
    record=prepared(tmp_path)
    if file_present:
        (tmp_path/'runs/wepp_ui.txt').write_text('');record['inputs']['wepp_ui.txt']='unused'
    if banner_present:(tmp_path/'runs/stdout').write_text('WEPP hourly water seepage update set (UI code)')
    with pytest.raises(ValueError,match='UI mode'):a.validate_runtime(tmp_path,{'runtime':'ui-only'},record)


def test_activated_ui_rejected_for_legacy_control(tmp_path):
    record=prepared(tmp_path)
    (tmp_path/'runs/wepp_ui.txt').write_text('');record['inputs']['wepp_ui.txt']='unused'
    (tmp_path/'runs/stdout').write_text('WEPP hourly water seepage update set (UI code)')
    a.validate_runtime(tmp_path,{'runtime':'ui-only'},record)
    with pytest.raises(ValueError,match='UI mode'):a.validate_runtime(tmp_path,{},record)


def test_negative_flux_remains_invalid_when_signed_totals_reconcile():
    rows=[dict(year=1,julian=day,OFE=ofe,SedLeave=value)
          for day,values in ((1,(20.,25.,30.)),(2,(20.,-8.436,-8.42)))
          for ofe,value in enumerate(values,1)]
    budget,_=a.sediment_diagnostics(rows,4,1,(30-8.42)*4)
    assert budget['numerical_report_reconciled'] is True
    assert budget['report_reconciled'] is False
    assert budget['physical_budget_valid'] is False
    assert [r['sediment_kg_m'] for r in budget['negative_fluxes']]==[-8.436,-8.42]
    assert budget['ofes'][2]['boundary_kg_yr']==pytest.approx((30-8.42)*4)


def test_positive_flux_preserves_audited_accounting():
    rows=[dict(year=1,julian=1,OFE=i,SedLeave=v) for i,v in enumerate((2.,5.,3.),1)]
    result,days=a.sediment_diagnostics(rows,4,1,12)
    expected,expected_days=a.a.sediment_budget(rows,4,1,12,strict=False)
    assert result.pop('negative_fluxes')==[]
    assert result.pop('physical_budget_valid') is True
    assert result==expected and days==expected_days
