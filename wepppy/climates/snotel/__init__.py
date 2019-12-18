from zeep import Client

client = Client('https://wcc.sc.egov.usda.gov/awdbWebService/services?WSDL')

stations = client.service.getStations(logicalAnd=True)

for station in stations:
    print(station)

client.service.getHourlyData(
    stationTriplets='302:OR:SNTL',
    elementCd='PREC',
    ordinal=1,
    beginDate='2000-01-01',
    endDate='2018-12-31')