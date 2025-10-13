FROM rocker/r-ver:4.3.2

ENV RENV_CONFIG_CACHE_SYMLINKS=FALSE \
    RENVMGR_PATHS_CACHE=/opt/weppcloudr/renv/cache \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        make \
        g++ \
        cmake \
        libssl-dev \
        libcurl4-openssl-dev \
        libxml2-dev \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        libudunits2-dev \
        libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN R -q -e "install.packages('pak', repos='https://cloud.r-project.org')" \
    && R -q -e "pak::pkg_install(c( \
          'plumber','rmarkdown','duckdb','jsonlite','glue','logger','tidyverse','cleanrmd','plotly','furrr','janitor','htmltools','echarts4r','DT','leaflet','data.table','leafsync','crosstalk','reshape2','sf','ggthemes','viridis','lubridate','readr' \
        ))"

RUN R -q -e "install.packages('arrow', repos='https://cloud.r-project.org')"

WORKDIR /srv/weppcloudr

COPY weppcloudR/plumber.R weppcloudR/docker-entrypoint.R /srv/weppcloudr/
COPY weppcloudR/templates /srv/weppcloudr/templates

EXPOSE 8000

ENTRYPOINT ["Rscript", "/srv/weppcloudr/docker-entrypoint.R"]
