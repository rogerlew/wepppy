
from wepppy.nodb.mods import Ash

if __name__ == "__main__":
    ash = Ash.getInstance('/geodata/weppcloud_runs/2aa3e70e-769b-4e1b-959c-54c8c7c4f2e6/')
    ash.get_annual_water_transport(22)