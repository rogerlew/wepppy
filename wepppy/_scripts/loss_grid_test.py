
from wepppy.nodb import Wepp

if __name__ == "__main__":
    wd = '/geodata/weppcloud_runs/bb967f25-9fd6-4641-b737-bb10a1cf7843'
    wepp = Wepp.getInstance(wd)
    wepp.make_loss_grid()