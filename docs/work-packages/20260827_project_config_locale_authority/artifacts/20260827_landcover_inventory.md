# WP12B Exact Landcover Inventory

This appendix is part of inventory revision `WP12B-INVENTORY-1`. It enumerates
every landcover runtime value in the canonical runtime catalog plus additional
values referenced by shipped top-level configs. Stable IDs use lowercase ASCII
letters, digits, and hyphens. Duplicate runtime values reused by a regional
catalog retain one stable ID. Any source value absent from this table fails the
inventory gate.

The executable provider boundary contains 163 unique values. The eMapR source
uses `range(2017, 1983, -1)`, so 1984 is the last included year; 1983 is not a
provider value.

| Stable ID | Runtime value | Current support state | Source |
| --- | --- | --- | --- |
| `nlcd-ever-forest-2024` | `nlcd/ever_forest/2024` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2023` | `nlcd/ever_forest/2023` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2022` | `nlcd/ever_forest/2022` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2021` | `nlcd/ever_forest/2021` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2020` | `nlcd/ever_forest/2020` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2019` | `nlcd/ever_forest/2019` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2018` | `nlcd/ever_forest/2018` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2017` | `nlcd/ever_forest/2017` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2016` | `nlcd/ever_forest/2016` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2015` | `nlcd/ever_forest/2015` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2014` | `nlcd/ever_forest/2014` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2013` | `nlcd/ever_forest/2013` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2012` | `nlcd/ever_forest/2012` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2011` | `nlcd/ever_forest/2011` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2010` | `nlcd/ever_forest/2010` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2009` | `nlcd/ever_forest/2009` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2008` | `nlcd/ever_forest/2008` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2007` | `nlcd/ever_forest/2007` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2006` | `nlcd/ever_forest/2006` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2005` | `nlcd/ever_forest/2005` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2004` | `nlcd/ever_forest/2004` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2003` | `nlcd/ever_forest/2003` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2002` | `nlcd/ever_forest/2002` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2001` | `nlcd/ever_forest/2001` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-2000` | `nlcd/ever_forest/2000` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1999` | `nlcd/ever_forest/1999` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1998` | `nlcd/ever_forest/1998` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1997` | `nlcd/ever_forest/1997` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1996` | `nlcd/ever_forest/1996` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1995` | `nlcd/ever_forest/1995` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1994` | `nlcd/ever_forest/1994` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1993` | `nlcd/ever_forest/1993` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1992` | `nlcd/ever_forest/1992` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1991` | `nlcd/ever_forest/1991` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1990` | `nlcd/ever_forest/1990` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1989` | `nlcd/ever_forest/1989` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1988` | `nlcd/ever_forest/1988` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1987` | `nlcd/ever_forest/1987` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1986` | `nlcd/ever_forest/1986` | `supported_non_builder` | default catalog |
| `nlcd-ever-forest-1985` | `nlcd/ever_forest/1985` | `supported_non_builder` | default catalog |
| `nlcd-2024` | `nlcd/2024` | `supported_non_builder` | default catalog |
| `nlcd-2023` | `nlcd/2023` | `supported_non_builder` | default catalog |
| `nlcd-2022` | `nlcd/2022` | `supported_non_builder` | default catalog |
| `nlcd-2021` | `nlcd/2021` | `supported_non_builder` | default catalog |
| `nlcd-2020` | `nlcd/2020` | `supported_non_builder` | default catalog |
| `nlcd-2019` | `nlcd/2019` | `builder_exposed` | default catalog |
| `nlcd-2018` | `nlcd/2018` | `supported_non_builder` | default catalog |
| `nlcd-2017` | `nlcd/2017` | `supported_non_builder` | default catalog |
| `nlcd-2016` | `nlcd/2016` | `supported_non_builder` | default catalog |
| `nlcd-2015` | `nlcd/2015` | `supported_non_builder` | default catalog |
| `nlcd-2014` | `nlcd/2014` | `supported_non_builder` | default catalog |
| `nlcd-2013` | `nlcd/2013` | `supported_non_builder` | default catalog |
| `nlcd-2012` | `nlcd/2012` | `supported_non_builder` | default catalog |
| `nlcd-2011` | `nlcd/2011` | `supported_non_builder` | default catalog |
| `nlcd-2010` | `nlcd/2010` | `supported_non_builder` | default catalog |
| `nlcd-2009` | `nlcd/2009` | `supported_non_builder` | default catalog |
| `nlcd-2008` | `nlcd/2008` | `supported_non_builder` | default catalog |
| `nlcd-2007` | `nlcd/2007` | `supported_non_builder` | default catalog |
| `nlcd-2006` | `nlcd/2006` | `supported_non_builder` | default catalog |
| `nlcd-2005` | `nlcd/2005` | `supported_non_builder` | default catalog |
| `nlcd-2004` | `nlcd/2004` | `supported_non_builder` | default catalog |
| `nlcd-2003` | `nlcd/2003` | `supported_non_builder` | default catalog |
| `nlcd-2002` | `nlcd/2002` | `supported_non_builder` | default catalog |
| `nlcd-2001` | `nlcd/2001` | `supported_non_builder` | default catalog |
| `nlcd-2000` | `nlcd/2000` | `supported_non_builder` | default catalog |
| `nlcd-1999` | `nlcd/1999` | `supported_non_builder` | default catalog |
| `nlcd-1998` | `nlcd/1998` | `supported_non_builder` | default catalog |
| `nlcd-1997` | `nlcd/1997` | `supported_non_builder` | default catalog |
| `nlcd-1996` | `nlcd/1996` | `supported_non_builder` | default catalog |
| `nlcd-1995` | `nlcd/1995` | `supported_non_builder` | default catalog |
| `nlcd-1994` | `nlcd/1994` | `supported_non_builder` | default catalog |
| `nlcd-1993` | `nlcd/1993` | `supported_non_builder` | default catalog |
| `nlcd-1992` | `nlcd/1992` | `supported_non_builder` | default catalog |
| `nlcd-1991` | `nlcd/1991` | `supported_non_builder` | default catalog |
| `nlcd-1990` | `nlcd/1990` | `supported_non_builder` | default catalog |
| `nlcd-1989` | `nlcd/1989` | `supported_non_builder` | default catalog |
| `nlcd-1988` | `nlcd/1988` | `supported_non_builder` | default catalog |
| `nlcd-1987` | `nlcd/1987` | `supported_non_builder` | default catalog |
| `nlcd-1986` | `nlcd/1986` | `supported_non_builder` | default catalog |
| `nlcd-1985` | `nlcd/1985` | `supported_non_builder` | default catalog |
| `emapr-vote-2017` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2017` | `supported_non_builder` | default catalog |
| `emapr-vote-2016` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2016` | `supported_non_builder` | default catalog |
| `emapr-vote-2015` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2015` | `supported_non_builder` | default catalog |
| `emapr-vote-2014` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2014` | `supported_non_builder` | default catalog |
| `emapr-vote-2013` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2013` | `supported_non_builder` | default catalog |
| `emapr-vote-2012` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2012` | `supported_non_builder` | default catalog |
| `emapr-vote-2011` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2011` | `supported_non_builder` | default catalog |
| `emapr-vote-2010` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2010` | `supported_non_builder` | default catalog |
| `emapr-vote-2009` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2009` | `supported_non_builder` | default catalog |
| `emapr-vote-2008` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2008` | `supported_non_builder` | default catalog |
| `emapr-vote-2007` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2007` | `supported_non_builder` | default catalog |
| `emapr-vote-2006` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2006` | `supported_non_builder` | default catalog |
| `emapr-vote-2005` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2005` | `supported_non_builder` | default catalog |
| `emapr-vote-2004` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2004` | `supported_non_builder` | default catalog |
| `emapr-vote-2003` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2003` | `supported_non_builder` | default catalog |
| `emapr-vote-2002` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2002` | `supported_non_builder` | default catalog |
| `emapr-vote-2001` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2001` | `supported_non_builder` | default catalog |
| `emapr-vote-2000` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/2000` | `supported_non_builder` | default catalog |
| `emapr-vote-1999` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1999` | `supported_non_builder` | default catalog |
| `emapr-vote-1998` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1998` | `supported_non_builder` | default catalog |
| `emapr-vote-1997` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1997` | `supported_non_builder` | default catalog |
| `emapr-vote-1996` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1996` | `supported_non_builder` | default catalog |
| `emapr-vote-1995` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1995` | `supported_non_builder` | default catalog |
| `emapr-vote-1994` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1994` | `supported_non_builder` | default catalog |
| `emapr-vote-1993` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1993` | `supported_non_builder` | default catalog |
| `emapr-vote-1992` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1992` | `supported_non_builder` | default catalog |
| `emapr-vote-1991` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1991` | `supported_non_builder` | default catalog |
| `emapr-vote-1990` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1990` | `supported_non_builder` | default catalog |
| `emapr-vote-1989` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1989` | `supported_non_builder` | default catalog |
| `emapr-vote-1988` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1988` | `supported_non_builder` | default catalog |
| `emapr-vote-1987` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1987` | `supported_non_builder` | default catalog |
| `emapr-vote-1986` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1986` | `supported_non_builder` | default catalog |
| `emapr-vote-1985` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1985` | `supported_non_builder` | default catalog |
| `emapr-vote-1984` | `islay.ceoas.oregonstate.edu/v1/landcover/vote/1984` | `supported_non_builder` | default catalog |
| `chile-cayumanque-landuse` | `locales/ChileCayumanque/landuse` | `supported_non_builder` | Chile Cayumanque |
| `alaska-nlcd-2001` | `alaska/nlcd/2001` | `supported_non_builder` | Alaska |
| `alaska-nlcd-2011` | `alaska/nlcd/2011` | `supported_non_builder` | Alaska |
| `alaska-nlcd-2016` | `alaska/nlcd/2016` | `supported_non_builder` | Alaska |
| `usvi-landcover-2018` | `locales/virgin_islands/landcover` | `supported_non_builder` | US Virgin Islands |
| `usvi-landcover-2023` | `locales/virgin_islands/landcover/2023` | `supported_non_builder` | US Virgin Islands |
| `hawaii-nlcd-wepp-31131a7` | `hawaii/nlcd/wepp_31131a7` | `supported_non_builder` | shipped config |
| `canada-landcover-2020` | `ca/canadalandcover2020` | `supported_non_builder` | shipped config |
| `portland-nlcd` | `portland/nlcd` | `supported_non_builder` | shipped config |
| `oyster-creek-1993` | `locales/oyster-creek/landuse/1993` | `supported_non_builder` | Oyster Creek |
| `oyster-creek-1982` | `locales/oyster-creek/landuse/1982` | `supported_non_builder` | Oyster Creek |
| `oyster-creek-1975` | `locales/oyster-creek/landuse/1975` | `supported_non_builder` | Oyster Creek |
| `oyster-creek-1970` | `locales/oyster-creek/landuse/1970` | `supported_non_builder` | Oyster Creek |
| `oyster-creek-1964` | `locales/oyster-creek/landuse/1964` | `supported_non_builder` | Oyster Creek |
| `oyster-creek-1959` | `locales/oyster-creek/landuse/1959` | `supported_non_builder` | Oyster Creek |
| `corine-1990` | `eu/CORINE_LandCover/1990` | `supported_non_builder` | Europe |
| `corine-2000` | `eu/CORINE_LandCover/2000` | `supported_non_builder` | Europe |
| `corine-2006` | `eu/CORINE_LandCover/2006` | `supported_non_builder` | Europe |
| `corine-2012` | `eu/CORINE_LandCover/2012` | `supported_non_builder` | Europe |
| `corine-2018` | `eu/CORINE_LandCover/2018` | `supported_non_builder` | Europe |
| `c3s-landcover-2020` | `locales/earth/C3Slandcover/2020` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2019` | `locales/earth/C3Slandcover/2019` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2018` | `locales/earth/C3Slandcover/2018` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2017` | `locales/earth/C3Slandcover/2017` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2016` | `locales/earth/C3Slandcover/2016` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2015` | `locales/earth/C3Slandcover/2015` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2014` | `locales/earth/C3Slandcover/2014` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2013` | `locales/earth/C3Slandcover/2013` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2012` | `locales/earth/C3Slandcover/2012` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2011` | `locales/earth/C3Slandcover/2011` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2010` | `locales/earth/C3Slandcover/2010` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2009` | `locales/earth/C3Slandcover/2009` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2008` | `locales/earth/C3Slandcover/2008` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2007` | `locales/earth/C3Slandcover/2007` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2006` | `locales/earth/C3Slandcover/2006` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2005` | `locales/earth/C3Slandcover/2005` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2004` | `locales/earth/C3Slandcover/2004` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2003` | `locales/earth/C3Slandcover/2003` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2002` | `locales/earth/C3Slandcover/2002` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2001` | `locales/earth/C3Slandcover/2001` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-2000` | `locales/earth/C3Slandcover/2000` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1999` | `locales/earth/C3Slandcover/1999` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1998` | `locales/earth/C3Slandcover/1998` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1997` | `locales/earth/C3Slandcover/1997` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1996` | `locales/earth/C3Slandcover/1996` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1995` | `locales/earth/C3Slandcover/1995` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1994` | `locales/earth/C3Slandcover/1994` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1993` | `locales/earth/C3Slandcover/1993` | `supported_non_builder` | Earth/Nigeria |
| `c3s-landcover-1992` | `locales/earth/C3Slandcover/1992` | `supported_non_builder` | Earth/Nigeria |

The Australia catalog is explicitly empty. It is represented as an unresolved
profile dependency rather than as an omitted dataset. `nlcd-2019` is the only
currently `builder_exposed` landcover value; every other row is explicitly
`supported_non_builder` until its profile/provider evidence is accepted.
