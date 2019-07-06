import requests
import seleniumrequests

from wepppy.all_your_base import isfloat

from bs4 import BeautifulSoup
from seleniumrequests import PhantomJS

def run_ermit(top_slope, avg_slope, toe_slope, length_ft,
              cli_fn, severity, soil_type,
              vegetation, pct_grass=None, pct_shrub=None):

    assert 0 <= top_slope <= 100
    assert 0 <= avg_slope <= 100
    assert 0 <= toe_slope <= 100

    assert length_ft >= 0

    if length_ft > 300.0:
        length_ft = 300.0

    assert severity in ['l', 'm', 'h', 'u']
    assert soil_type in ['clay', 'silt', 'sand', 'loam']
    assert vegetation in ['forest', 'range', 'chap']

    if vegetation == 'forest':
        pct_grass = ''
        pct_shrub = ''
        pct_bare = ''
    else:
        assert isfloat(pct_grass)
        assert isfloat(pct_shrub)
        assert 0 <= pct_grass <= 100.0
        assert 0 <= pct_shrub <= 100.0
        assert 0 <= pct_shrub + pct_grass <= 100.0
        pct_bare = 100.0 - pct_shrub - pct_grass

    data = dict(achtung='Run+WEPP',
            actionw='Running+ERMiT...',
            top_slope=top_slope,
            avg_slope=avg_slope,
            toe_slope=toe_slope,
            Climate='../climates/' + cli_fn,
            climate_name='',
            debug='',
            length=length_ft,
            me='',
            pct_bare=pct_bare,
            pct_grass=pct_grass,
            pct_shrub=pct_shrub,
            rfg=20,
            severity=severity,
            SoilType=soil_type,
            units='ft',
            Units='m',
            vegetation=vegetation)

    url = 'https://forest.moscowfsl.wsu.edu/cgi-bin/fswepp/ermit/erm.pl'
    #r = requests.post(url, data)
    #resp = r.text

    #with open('output.htm', 'w') as fp:
    #    fp.write(resp)

    driver = PhantomJS()
    response = driver.request('POST', url, data=data)
    print(driver.page_source)

    soup = BeautifulSoup(response.text, 'html.parser')
    # class "postText" is not defined in the source code
    tag = soup.find("span", {"id": "sediment_cl3"})
    print(tag.text)


if __name__ == "__main__":
    run_ermit(top_slope=0, avg_slope=50, toe_slope=30, length_ft=290,
              cli_fn='ca045983', severity='h', soil_type='clay',
              vegetation='forest', pct_grass=None, pct_shrub=None)
