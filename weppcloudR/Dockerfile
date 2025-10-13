FROM rocker/r-ver:4.3.2

ENV RENV_CONFIG_CACHE_SYMLINKS=FALSE \
    RENVMGR_PATHS_CACHE=/opt/weppcloudr/renv/cache \
    RENV_PATHS_CACHE=/opt/weppcloudr/renv/cache \
    PORT=8000 \
    # Use the OS-specific URL for binaries. rocker/r-ver:4.3.2 is Debian Bookworm.
    RSPM=https://packagemanager.posit.co/cran/__linux__/jammy/latest

# Add prerequisites for adding the Arrow repository
RUN apt-get update && apt-get install -y --no-install-recommends \
    lsb-release \
    wget \
    gpg \
    ca-certificates \
    curl \
    gpg \
    lsb-release

RUN curl -sS https://apache.jfrog.io/artifactory/arrow/$(lsb_release --id --short | tr 'A-Z' 'a-z')/apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb -o /tmp/apache-arrow-apt-source.deb

RUN apt-get install -y /tmp/apache-arrow-apt-source.deb && \
    rm /tmp/apache-arrow-apt-source.deb

# Install Arrow's C++ library AND your other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        libarrow-dev \
        libparquet-dev \
        libicu-dev \
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

# Install all R packages at once using pak
RUN R -q -e "options(repos = c(CRAN = Sys.getenv('RSPM'))); install.packages('pak', dependencies = TRUE)" \
    && R -q -e "options(repos = c(CRAN = Sys.getenv('RSPM'))); pak::pkg_install(c( \
          'arrow', \
          'plumber','rmarkdown','duckdb','jsonlite','glue','logger','tidyverse', \
          'cleanrmd','plotly','furrr','janitor','htmltools','echarts4r','DT', \
          'leaflet','data.table','leafsync','crosstalk','reshape2','sf', \
          'ggthemes','viridis','lubridate','readr' \
        ))"

WORKDIR /srv/weppcloudr

COPY weppcloudR/plumber.R weppcloudR/docker-entrypoint.R /srv/weppcloudr/
COPY weppcloudR/templates /srv/weppcloudr/templates

EXPOSE 80

ENTRYPOINT ["Rscript", "/srv/weppcloudr/docker-entrypoint.R"]
