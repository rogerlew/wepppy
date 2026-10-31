"""Exact combined U12 pair, unchanged Roads840/downstream348 development inputs."""
from pathlib import Path
import depend_bounded_replay as replay
replay.ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/param-sign-u12-combined')
replay.BINARY=replay.ROOT/'bin/wepp'
if __name__=='__main__':replay.main()
