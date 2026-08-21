FROM rocker/r-ver:4.3.2@sha256:4e32addfc4da3e660f6e0d05ce5e43d3eceb9db58a60b9a142e0dde9a654ead1

ARG ARROW_APT_SOURCE_URL=https://apache.jfrog.io/artifactory/arrow/ubuntu/apache-arrow-apt-source-latest-jammy.deb
ARG ARROW_APT_SOURCE_SHA256=9ef1afbcca1705ddd6f358672deb5ba4f858b248144ef6356d4b8f4788ac1fda
ARG APP_UID=1000
ARG APP_GID=993

ENV RENV_CONFIG_CACHE_SYMLINKS=FALSE \
    RENVMGR_PATHS_CACHE=/opt/weppcloudr/renv/cache \
    RENV_PATHS_CACHE=/opt/weppcloudr/renv/cache \
    PORT=8000 \
    # Pin the RSPM snapshot date so package resolution is reproducible.
    # Base image is Ubuntu Jammy.
    RSPM=https://packagemanager.posit.co/cran/__linux__/jammy/2026-04-17

# Add prerequisites for adding the Arrow repository
RUN apt-get update && apt-get install -y --no-install-recommends \
    lsb-release \
    wget \
    gpg \
    ca-certificates \
    curl \
    gpg \
    lsb-release

RUN curl -fsSL "${ARROW_APT_SOURCE_URL}" -o /tmp/apache-arrow-apt-source.deb && \
    echo "${ARROW_APT_SOURCE_SHA256}  /tmp/apache-arrow-apt-source.deb" | sha256sum -c -

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
        python3 \
    && rm -rf /var/lib/apt/lists/*

# Install R packages directly from RSPM. The current pak release no longer
# loads on R 4.3.2 during image builds because its embedded cli expects
# R_getVarEx, which is not present in this R runtime.
RUN R -q -e "options(repos = c(CRAN = Sys.getenv('RSPM'))); install.packages(c( \
          'arrow', \
          'plumber','rmarkdown','duckdb','jsonlite','glue','logger','tidyverse', \
          'cleanrmd','plotly','furrr','janitor','htmltools','echarts4r','DT', \
          'leaflet','data.table','leafsync','crosstalk','reshape2','sf', \
          'ggthemes','viridis','lubridate','readr' \
        ))"

WORKDIR /srv/weppcloudr

COPY weppcloudR/plumber.R weppcloudR/docker-entrypoint.R weppcloudR/render-compose-request.R weppcloudR/render-request-v1.R weppcloudR/publish_fenced.py /srv/weppcloudr/
RUN chmod 0555 /srv/weppcloudr/publish_fenced.py
COPY weppcloudR/templates /srv/weppcloudr/templates

RUN groupadd --gid "${APP_GID}" weppcloudr && \
    useradd --uid "${APP_UID}" --gid "${APP_GID}" --no-create-home --shell /usr/sbin/nologin weppcloudr && \
    mkdir -p /opt/weppcloudr/renv/cache && \
    chown -R "${APP_UID}:${APP_GID}" /srv/weppcloudr /opt/weppcloudr

EXPOSE 80

USER ${APP_UID}:${APP_GID}
ENTRYPOINT ["Rscript", "/srv/weppcloudr/docker-entrypoint.R"]
