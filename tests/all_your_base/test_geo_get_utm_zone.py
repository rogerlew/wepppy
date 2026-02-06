import pytest

osr = pytest.importorskip("osgeo.osr")

from wepppy.all_your_base.geo.geo import get_utm_zone


pytestmark = pytest.mark.unit


def test_get_utm_zone_from_wkt_with_epsg_32610() -> None:
    wkt = (
        'PROJCRS["WGS_1984_Transverse_Mercator",'
        'BASEGEOGCRS["WGS 84",'
        'DATUM["World Geodetic System 1984",'
        'ELLIPSOID["WGS 84",6378137,298.257223563,'
        'LENGTHUNIT["metre",1]]],'
        'PRIMEM["Greenwich",0,'
        'ANGLEUNIT["degree",0.0174532925199433]],'
        'ID["EPSG",4326]],'
        'CONVERSION["Transverse Mercator",'
        'METHOD["Transverse Mercator",'
        'ID["EPSG",9807]],'
        'PARAMETER["Latitude of natural origin",0,'
        'ANGLEUNIT["degree",0.0174532925199433],'
        'ID["EPSG",8801]],'
        'PARAMETER["Longitude of natural origin",-123,'
        'ANGLEUNIT["degree",0.0174532925199433],'
        'ID["EPSG",8802]],'
        'PARAMETER["Scale factor at natural origin",0.9996,'
        'SCALEUNIT["unity",1],'
        'ID["EPSG",8805]],'
        'PARAMETER["False easting",500000,'
        'LENGTHUNIT["metre",1],'
        'ID["EPSG",8806]],'
        'PARAMETER["False northing",0,'
        'LENGTHUNIT["metre",1],'
        'ID["EPSG",8807]]],'
        'CS[Cartesian,2],'
        'AXIS["easting",east,ORDER[1],LENGTHUNIT["metre",1]],'
        'AXIS["northing",north,ORDER[2],LENGTHUNIT["metre",1]],'
        'ID["EPSG",32610]]'
    )

    srs = osr.SpatialReference()
    assert srs.ImportFromWkt(wkt) == 0

    projcs_name = (srs.GetAttrValue("projcs") or "")
    assert "UTM" not in projcs_name

    datum, zone, hemisphere = get_utm_zone(srs)
    assert datum == "WGS84"
    assert zone == 10
    assert hemisphere == "N"
