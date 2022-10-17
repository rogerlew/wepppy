from pprint import pprint

from wepppy.fswepppy.wr import run_factory

d = run_factory('ib n h 7 100 30 17 150 32 101 7 clay https://dev.wepp.cloud/weppcloud/runs/base-monad/disturbed9002/browse/climate/id106388.cli', 'wd')
pprint(d)
