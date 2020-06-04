import csv
from os.path import exists

bad_mukeys = set()
fp = open('soil_lookup.csv')
fp2 = open('soil_lookup_checked.csv', 'w')

fp2.write('AFFGEOID,MUKEY,source,lng,lat\n')

rdr = csv.DictReader(fp)

for row in rdr:
    key = row['AFFGEOID']
    mukey = row['MUKEY']
    source = row['source']
    lng = row['lng']
    lat = row['lat']

    if mukey == 'None':
        continue

    if not exists('soils/{}.sol'.format(mukey)):
        bad_mukeys.add(int(mukey))

        fp2.write('{AFFGEOID},None,None,None,None\n'
                  .format(AFFGEOID=key))
    else:
        fp2.write('{AFFGEOID},{mukey},{source},{lng},{lat}\n'
                  .format(AFFGEOID=key, mukey=mukey, source=source, lng=lng, lat=lat))

print(bad_mukeys)
