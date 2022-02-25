from subprocess import Popen, PIPE
from osgeo import gdal, osr
from os.path import exists as _exists
from wepppy.all_your_base.geo import get_utm_zone, utm_srid
import cv2

class RoadDEM(object):
    def __init__(self, dem_fn):
        self.dem_fn = dem_fn

        # open the dataset
        ds = gdal.Open(dem_fn)

        # read and verify the num_cols and num_rows
        num_cols = ds.RasterXSize
        num_rows = ds.RasterYSize

        if num_cols <= 0 or num_rows <= 0:
            raise Exception('input is empty')

        # read and verify the _transform
        _transform = ds.GetGeoTransform()

        if abs(_transform[1]) != abs(_transform[5]):
            raise Exception('input cells are not square')

        cellsize = abs(_transform[1])
        ul_x = int(round(_transform[0]))
        ul_y = int(round(_transform[3]))

        lr_x = ul_x + cellsize * num_cols
        lr_y = ul_y - cellsize * num_rows

        ll_x = int(ul_x)
        ll_y = int(lr_y)

        # read the projection and verify dataset is in utm
        srs = osr.SpatialReference()
        srs.ImportFromWkt(ds.GetProjectionRef())

        datum, utm_zone, hemisphere = get_utm_zone(srs)
        if utm_zone is None:
            raise Exception('input is not in utm')

        # get band
        band = ds.GetRasterBand(1)
        self.z = np.array(band.ReadAsArray(), dtype=np.float32).T

        # get band dtype
        dtype = gdal.GetDataTypeName(band.DataType)

        if 'float' not in dtype.lower():
            raise Exception('dem dtype does not contain float data')

        # extract min and max elevation
        stats = band.GetStatistics(True, True)
        minimum_elevation = stats[0]
        maximum_elevation = stats[1]

        # store the relevant variables to the class
        self.transform = _transform
        self.num_cols = num_cols
        self.num_rows = num_rows
        self.cellsize = cellsize
        self.ul_x = ul_x
        self.ul_y = ul_y
        self.lr_x = lr_x
        self.lr_y = lr_y
        self.ll_x = ll_x
        self.ll_y = ll_y
        self.datum = datum
        self.hemisphere = hemisphere
        self.epsg = utm_srid(utm_zone, hemisphere == 'N')
        self.utm_zone = utm_zone
        self.srs_proj4 = srs.ExportToProj4()
        srs.MorphToESRI()
        self.srs_wkt = srs.ExportToWkt()
        self.minimum_elevation = minimum_elevation
        self.maximum_elevation = maximum_elevation

        del ds

    def _rasterize(self, road_fn, dilation, dst_fn, z_offset=-0.1):
        cmd = ['gdal_rasterize', '-burn', 1, '-a_nodata', '0',
               '-a_srs', 'epsg:{}'.format(self.epsg), 
               '-te', self.ul_x, self.lr_y, self.lr_x, self.ul_y,
               '-tr', self.cellsize, self.cellsize,
               '-ot', 'UInt16', road_fn, dst_fn]
        cmd = [str(v) for v in cmd]
        print(' '.join(cmd))

        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        p.wait()
        assert _exists(dst_fn)
    
        mask, _transform, _proj = read_raster(dst_fn)
        kernel = np.ones((dilation, dilation), dtype=np.uint8)
        dilated_mask = cv2.dilate(mask, kernel)
        
        new_z = self.z + dilated_mask * z_offset
        return new_z
        
