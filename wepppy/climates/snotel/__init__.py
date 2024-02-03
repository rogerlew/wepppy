import requests

target_url = "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/daily/{}:SNTL%7Cid=%22%22%7Cname/POR_BEGIN,POR_END/WTEQ::value,PREC::value,TMAX::value,TMIN::value,TAVG::value,PRCP::value"

def download_snotel_data(station_id, output_file):
    url = target_url.format(station_id.replace('_', ':'))

    response = requests.get(url)
    csv = response.content.decode('utf-8')
    with open(output_file, 'w') as f:
        f.write(csv)

    return response.content


if __name__ == "__main__":

    import pandas as pd

    stations = pd.read_csv('/workdir/wepppy/wepppy/climates/validation/snotel_locations.csv')
    
    for key, row in stations.iterrows():
        snotel_lat = row.lat
        snotel_lng = row.long
        snotel_id = row.SNTL_stations

        print(snotel_id)

        download_snotel_data(snotel_id, f'historic/{snotel_id}.csv')