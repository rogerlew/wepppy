from math import cos, pi
from wepppy.climates.cligen import CligenStationsManager

station_manager = CligenStationsManager()

offsets = (('o',   (   0,    0)),
           ('N',  (   0,  800)),
           ('NE', ( 800,  800)),
           ('E',  ( 800,    0)),
           ('SE', ( 800, -800)),
           ('S',  (   0, -800)),
           ('SW', (-800, -800)),
           ('W',  (-800,    0)),
           ('NW', (-800,  800)))


def lnglat_offset(lon, lat, de, dn):
    """
    offset lng and lat by de and dn in meters
    """
    # https://gis.stackexchange.com/a/2980

    # Earth’s radius, sphere
    R = 6378137

    # Coordinate offsets in radians
    dLat = dn / R
    dLon = de / (R * cos(pi * lat / 180.0))

    # OffsetPosition, decimal degrees
    lat_offset = lat + dLat * 180.0/pi
    lon_offset = lon + dLon * 180.0/pi 

    return lon_offset, lat_offset

def prism_surrounding(name, lng, lat):
    global station_manager, offsets

    station_meta = station_manager.get_closest_station((lng, lat))

    for direction, (de, dn) in offsets:
        station = station_meta.get_station()
        _lng, _lat = lnglat_offset(lng, lat, de, dn)
        localized = station.localize(_lng, _lat, 
                                     p_mean='prism', p_std=None, p_skew=None, 
                                     tmax='prism', tmin='prism', solrad=None, 
                                     dewpoint=None, interp_method='nearest')

        localized.write(f'{name}_{direction}.par')

if __name__ == "__main__":
    prism_surrounding('1_Steuben Co NY', -77.33, 42.33)

