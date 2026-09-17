"""Changed H.wat generations must discover their own native source IDs."""
import json

import pytest

from tests.wepp.reports.test_report_cache_freshness import run, _rewrite, _table
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport


def test_characterize_changed_source_reuses_obsolete_ids(run):
    source = run / 'wepp/output/interchange/H.wat.parquet'
    _rewrite(source, 'wepp_id', 2)
    previous = HillslopeWatbalReport(run)
    _rewrite(source, 'wepp_id', 1)
    _table(run / 'watershed/hillslopes.parquet', [
        {'topaz_id': 101, 'wepp_id': 1, 'area': 1000.}])
    with pytest.raises(KeyError) as error:
        HillslopeWatbalReport(run)
    # The actual same native builder succeeds with its newly scanned ID set.
    rebuilt = previous._build_summary()
    print(json.dumps({'cache_reader_error': str(error.value),
                      'native_rebuilt_topaz': rebuilt['TopazID'].tolist()}))
    assert rebuilt['TopazID'].tolist() == [101]
