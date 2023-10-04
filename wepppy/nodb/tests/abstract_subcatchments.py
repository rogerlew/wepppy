from wepppy.nodb import Watershed

if __name__ == '__main__':
    wd = '/geodata/weppcloud_runs/leery-amphetamine/'
    watershed = Watershed.getInstance(wd)
    watershed.abstract_watershed()

    # python3  -m cProfile abstract_subcatchments.py
