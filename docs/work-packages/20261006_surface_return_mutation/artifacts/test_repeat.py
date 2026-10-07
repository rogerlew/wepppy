"""Research-harness regression checks, including the observer indexing failure."""
from pathlib import Path
import importlib.util
import sys

import pandas as pd
import numpy as np
import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


repeat = load('repeat_census')
plot = load('plot_figures')


def fixture(tmp_path, runoff=.01, peak=1e-6):
    (tmp_path / 'runs').mkdir()
    (tmp_path / 'output').mkdir()
    (tmp_path / 'runs/census.csv').write_text(f'1980,9,1,{runoff},{peak},.003\n')
    (tmp_path / 'output/H1.element.dat').write_text('head\nunits\n1 9 1 1 20 10 0 3.6\n')
    return tmp_path


def test_full_precision_observer_matches_report(tmp_path):
    result = repeat.validate_report(fixture(tmp_path), 1)
    assert result['matched_report_rows'] == 1
    assert result['max_runoff_rounding_mm'] == 0
    assert result['max_peak_rounding_mm_h'] < 1e-12


def test_wrong_zero_based_array_slot_is_rejected(tmp_path):
    with pytest.raises(AssertionError):
        repeat.validate_report(fixture(tmp_path, 0, 0), 1)


def test_duplicate_trace_date_is_rejected(tmp_path):
    fixture(tmp_path)
    p = tmp_path / 'runs/census.csv'
    p.write_text(p.read_text() * 2)
    with pytest.raises(AssertionError):
        repeat.read_trace(tmp_path)


@pytest.mark.parametrize('value', ['nan', 'inf', '-0.1'])
def test_invalid_trace_is_rejected(tmp_path, value):
    with pytest.raises(AssertionError):
        repeat.read_trace(fixture(tmp_path, value))


def test_original_direction_and_tail_conventions():
    data = pd.DataFrame({'x': [1, 1, 1, 1, 1], 'y': [1, 2, .2, 6, .1],
                         'direction': ['plus', 'minus', 'plus', 'plus', 'minus']})
    stats = plot.statistics(data)
    assert stats == {'n': 5, 'outside_2x': 3, 'outside_5x': 2, 'congruent': 2,
                     'ties': 1, 'incongruent_including_ties': 3}


def test_plot_render_and_count_contract(tmp_path):
    f = pd.DataFrame({'x': [1., 2.], 'y': [1.1, 1.8],
        'scenario': ['burned', 'undisturbed'], 'family': ['ksat', 'cover'],
        'direction': ['minus', 'plus'], 'has_surdra': [True, False]})
    result = plot.plot(f, 3, 'Test Peak', 'peak (mm/h)', np.array([.3, 800.]), tmp_path, peak=True)
    assert result['all']['n'] == 2
    assert result['all']['congruent'] == 2
    assert result['outside_axis_limits'] == 0
    assert (tmp_path / 'figure-3.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
