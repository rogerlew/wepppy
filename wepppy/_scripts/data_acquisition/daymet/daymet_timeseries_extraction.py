from os.path import join as _join
import netCDF4

prcp_dir = '/geodata/daymet/prcp/'

ds = netCDF4.Dataset(_join(prcp_dir, 'daymet_v3_prcp_1980_na.nc4'))

# determine transform
v = ds.variables['lambert_conformal_conic']
x = [ds.variables['x'][0],
     ds.variables['x'][1],
     ds.variables['x'][-1]]
y = [ds.variables['y'][0],
     ds.variables['y'][1],
     ds.variables['y'][-1]]
transform = [x[0], x[1] - x[0], 0.0, y[0], 0.0, y[1] - y[0]]

print(v)