"""Rebuild the CLIGEN station SQLite catalogs from collections of `.par` files."""

from os.path import exists as _exists
from os.path import split as _split
from os.path import join as _join
import os
import sys
import sqlite3
import zipfile
import shutil
import glob

from wepppy.climates.cligen import Station

from pathlib import Path


def isfloat(v):
    """Return 1 when a value can be coerced to float, otherwise 0."""
    try:
        float(v)
        return 1
    except:
        return 0


def _p(line):
    """Normalize a `.par` line by stripping non-numeric tokens."""
    line = line.replace('TP5', '')
    line = line.replace('TP6', '')
    line = ''.join([v for v in line if v in ' -.0123456789'])
    return line.split()


def get_state(par_path):
    """Infer the station's state/region code from its `.par` filename."""
    state = Path(par_path).stem.upper()
    state = ''.join([c for c in state if not isfloat(c)])
    state = state.replace("_", "")
    if ','  in state:
        state = state.split(',')[0]
    return state

all_state_codes = None
state_descriptions = None

def readpar(par):
    """Read a `.par` file and return the metadata tuple written to SQLite."""
    global all_state_codes, state_descriptions
    with open(par) as fid:
        desc = fid.readline().strip()
        state = get_state(par)
        print(state, par)
        
        all_state_codes.add(state)
        if state not in state_descriptions:
            state_descriptions[state] = []
            
        state_descriptions[state].append(desc)

        line1 = _p(fid.readline())
        assert len(line1) == 4
        latitude, longitude, years, type = line1

        line2 = _p(fid.readline())
        assert len(line2) == 3, str(line2)
        elevation, tp5, tp6 = line2
    
    station = Station(par)
    annual_ppt = sum(ppt*nwd for ppt, nwd in zip(station.ppts, station.nwds))

    return '"%s"' % state, '"%s"' % desc.replace('"', ''), '"%s"' % _split(par)[-1], latitude, longitude, years, type, elevation, tp5, tp6, str(annual_ppt)


def get_state_name(state_code: str, state_code_wildcards: dict):
    """Return the human-friendly state/region name for a given code."""
    for state_code_wildcard, state_name in state_code_wildcards.items():
        if state_code.startswith(state_code_wildcard):
            return state_name
    return None


def build_db(db_fn, par_dir, state_code_wildcards):
    """Scan `.par` files and store their metadata in a SQLite database."""
    global all_state_codes, state_descriptions
    all_state_codes = set()
    state_descriptions = dict()
    
    if _exists(db_fn):
        os.remove(db_fn)

    conn = sqlite3.connect(db_fn)
    c = conn.cursor()
    c.execute('''CREATE TABLE stations
                (state text, desc text, par text, latitude real, longitude real, years real, type integer, elevation real, tp5 real, tp6 real, annual_ppt real)''')
    
    par_files = glob.glob(_join(par_dir, "**/*.par"), recursive=True)
    par_files += glob.glob(_join(par_dir, "**/*.PAR"), recursive=True)

    par_stems = set()
    filtered_pars = []
    for par in par_files:
        if par not in par_stems:
            filtered_pars.append(par)
            par_stems = Path(par).stem

    for par in filtered_pars:
        print(par)
        line = ','.join(readpar(par))
        print(line)
        c.execute("INSERT INTO stations VALUES (%s)" % line)

    print(len(par_files))
    
    #  build state table, two letter state_code text, state_name text
    c.execute('''CREATE TABLE states
                (state_code text, state_name text)''')
    
    for state_code in all_state_codes:
        print('state_code', state_code)
        state_name = get_state_name(state_code, state_code_wildcards)
        
        assert state_name is not None, state_code
        if state_name:
            c.execute("INSERT INTO states VALUES ('%s', '%s')" % (state_code, state_name))

    conn.commit()
    conn.close()
    
    os.chmod(db_fn, 0o755)

chile_state_code_wildcards = {
    "NUEVAALDEA": "Chile"
}

ghcn_state_code_wildcards = {
  "IT": "Italy",
  "NL": "Netherlands",
  "MX": "Mexico",
  "USAL": "Alabama",
  "USAK": "Alaska",
  "USAZ": "Arizona",
  "USAR": "Arkansas",
  "USCA": "California",
  "USCO": "Colorado",
  "USCT": "Connecticut",
  "USDE": "Delaware",
  "USFL": "Florida",
  "USGA": "Georgia",
  "USHI": "Hawaii",
  "USID": "Idaho",
  "USIL": "Illinois",
  "USIN": "Indiana",
  "USIA": "Iowa",
  "USKS": "Kansas",
  "USKY": "Kentucky",
  "USLA": "Louisiana",
  "USME": "Maine",
  "USMD": "Maryland",
  "LUE": "Luxembourg",
  "MI": "Malawi",
  "MP": "Mauritius",
  "USMA": "Massachusetts",
  "USMI": "Michigan",
  "USMN": "Minnesota",
  "USMS": "Mississippi",
  "USMO": "Missouri",
  "USMT": "Montana",
  "USNE": "Nebraska",
  "USNV": "Nevada",
  "USNH": "New Hampshire",
  "USNJ": "New Jersey",
  "USNM": "New Mexico",
  "USNY": "New York",
  "USNC": "North Carolina",
  "USND": "North Dakota",
  "USOH": "Ohio",
  "USOK": "Oklahoma",
  "USOR": "Oregon",
  "USPA": "Pennsylvania",
  "USRI": "Rhode Island",
  "USSC": "South Carolina",
  "USSD": "South Dakota",
  "USTN": "Tennessee",
  "USTX": "Texas",
  "USUT": "Utah",
  "USVT": "Vermont",
  "USVA": "Virginia",
  "USWA": "Washington",
  "USWV": "West Virginia",
  "USWI": "Wisconsin",
  "USWY": "Wyoming",
  "USDC": "District of Columbia",
  "USPR": "Puerto Rico",
  "USVI": "U.S. Virgin Islands",
  "SZ": "Swaziland",
  "CY": "Cyprus",
  "GR": "Greece",
  "EN": "England",
  "FR": "France",
  "SPE": "Spain",
  "LH": "Liechtenstein",
  "HR": "Croatia",
  "EZE": "Ecuador",
  "UKE": "United Kingdom (England specific)",
  "NOE": "Norway",
  "ASN": "Asia",
  "SU": "Soviet Union (historic)",
  "UK": "United Kingdom",
  "AM": "Armenia",
  "IS": "Iceland",
  "GB": "Great Britain",
  "NO": "Norway",
  "TI": "Tajikistan",
  "SV": "El Salvador",
  "FI": "Finland",
  "KZ": "Kazakhstan",
  "JA": "Japan",
  "MY": "Malaysia",
  "IC": "Iceland",
  "SP": "Spain",
  "CA": "Canada",
  "IN": "India",
  "ROE": "Romania",
  "FRM": "France",
  "BR": "Brazil",
  "IC": "Iceland",
  "JAM": "Jamaica",
  "GV": "Guinea",
  "SNM": "Senegal",
  "HRE": "Zimbabwe (Harare)",
  "ALE": "Aleutian Islands (Alaska, U.S.)",
  "TSM": "Tasmania (Australia)",
  "IC": "Iceland",
  "FRE": "France",
  "GMM": "Gambia",
  "SWE": "Sweden",
  "WUKARINRA": "Nigeria, Wukari",
  "UZM": "Uzbekistan",
  "VMM": "Vietnam",
  "SW": "Sweden",
  "SI": "Slovenia",
  "LOE": "Slovakia",
  "HUE": "Hungary",
  "GM": "Germany",
  "GLE": "Greenland, Denmark",
  "GGM": "Georgia",
  "DA": "Denmark",
  "JNM": "Jan Mayen, Norway",
  "IRM": "IRM",
  "SF": "South Africa",
  "RS": "Russia",
  "RIE": "Serbia",
  "RQC": "Puerto Rico",
  "AJ": "Azerbaijan",
  "BKM": "Bosnia and Herzegovina, Sarajevo",
  "BOM": "Belarus",
  "BUM": "Bulgaria",
  "CD": "Chad",
  "CHM": "China",
  "CT": "Central African Republic",
  "FP": "French Polynesia",
  "GP": " Guadeloupe, France",
  "PLM": "Poland",
  "POE": "Portugal",
  "PP": "Papua New Guinea",
  "UPM": "Ukraine",
  "ZA": "Zambia",
  "US": "United States"
}

us_state_code_wildcards = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "PR": "Puerto Rico",
    "VI": "U.S. Virgin Islands",
    "PI": "Pacific Islands"
}

australia_state_code_wildcards = {
    "AU": "Australia"
}

database_defs = [
    # dict(
    #    db_fn= '2015_stations.db',
    #    par_dir= '../2015_par_files/',
    #    state_code_wildcards=us_state_code_wildcards
    # ),
    # dict(
    #     db_fn= 'au_stations.db',
    #     par_dir= '../au_par_files/',
    #     state_code_wildcards=australia_state_code_wildcards
    # ),
    # dict(
    #     db_fn= 'stations.db',
    #     par_dir= '../stations/',
    #     state_code_wildcards=us_state_code_wildcards
    # ),
    # dict(
    #     db_fn= 'ghcn_stations.db',
    #     par_dir= '../GHCN_Intl_Stations/',
    #     state_code_wildcards=ghcn_state_code_wildcards
    # ),
    dict(
       db_fn= 'chile.db',
       par_dir= os.path.abspath('../chile/'),
       state_code_wildcards=chile_state_code_wildcards
    ),
]

def main() -> int:
    """Entry point for building station databases from PAR files."""
    state_codes = None
    for db_def in database_defs:
        build_db(**db_def)
        state_codes = db_def['state_code_wildcards']

    if state_codes is None:
        return 0

    # All this is code to build the state_code_wildcards dictionaries
    filtered_states = set()
    for state in all_state_codes:
        found = 0
        for state_code, _ in state_codes.items():
            if state.startswith(state_code):
                found = 1
                break

        if not found:
            filtered_states.add(state)

    for j, state in enumerate(sorted(filtered_states)):
        print(state)
        for i, desc in enumerate(state_descriptions[state]):
            print('  ', desc)
            if i > 10:
                break

        print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
