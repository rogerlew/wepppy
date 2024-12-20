from wepppy.climates.cligen import CligenStationsManager

stationManager = CligenStationsManager(bbox=[-120, 47, -115, 42])

assert len(stationManager.stations) > 0, 'No stations found in the bounding box'

# Export to GeoJSON
stationManager.export_to_geojson('stations.geojson')

print(stationManager.states['KS'])