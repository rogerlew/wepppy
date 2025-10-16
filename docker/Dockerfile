# syntax=docker/dockerfile:1

FROM node:20-alpine AS static-builder
WORKDIR /app
COPY wepppy/weppcloud/static-src/package.json wepppy/weppcloud/static-src/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY wepppy/weppcloud/static-src/ ./
RUN npm run build

FROM python:3.10-slim AS base

LABEL org.opencontainers.image.source="https://github.com/rogerlew/wepppy"

ARG DEBIAN_FRONTEND=noninteractive
ARG DOCKER_CLI_VERSION=26.1.4

# Allow enforcing a non-root runtime user at build time.
ARG APP_USER=wepp
ARG APP_GROUP=wepp
ARG APP_UID=1000
ARG APP_GID=1000

# External repositories that historically lived beside the working tree.
ARG F_ESRI_REPO=https://github.com/rogerlew/f-esri.git
ARG F_ESRI_REF=main
ARG WBT_REPO=https://github.com/rogerlew/weppcloud-wbt.git
ARG WBT_REF=master
ARG WEPPCLOUD2_REPO=https://github.com/wepp-in-the-woods/weppcloud2.git
ARG WEPPCLOUD2_REF=main
ARG WEPPPY2_REPO=https://github.com/wepp-in-the-woods/wepppy2.git
ARG WEPPPY2_REF=main
ARG WEPPPYO3_REPO=https://github.com/wepp-in-the-woods/wepppyo3.git
ARG WEPPPYO3_REF=main

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        git-lfs \
        gfortran \
        pkg-config \
        cmake \
        gdal-bin \
        libgdal-dev \
        libproj-dev \
        proj-bin \
        libgeos-dev \
        libhdf5-dev \
        libnetcdf-dev \
        libopenblas-dev \
        liblapack-dev \
        libcurl4-openssl-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libwebp-dev \
        libzip-dev \
        libbz2-dev \
        liblzma-dev \
        zlib1g-dev \
        ca-certificates && \
    git lfs install --system && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" -o /tmp/docker.tgz && \
    tar -xzf /tmp/docker.tgz -C /tmp && \
    mv /tmp/docker/docker /usr/local/bin/docker && \
    chmod +x /usr/local/bin/docker && \
    rm -rf /tmp/docker /tmp/docker.tgz

ENV UV_SKIP_UPDATE_CHECK=1

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Resolve Python dependencies with uv inside a dedicated virtual environment.
COPY docker/requirements-uv.txt /tmp/requirements-uv.txt
RUN uv venv /opt/venv && \
    source /opt/venv/bin/activate && \
    uv pip install --requirement /tmp/requirements-uv.txt

# Install and load DuckDB's spatial extension using the venv's python.
RUN /opt/venv/bin/python -c "import duckdb; \
               con = duckdb.connect(); \
               con.execute('SET home_directory=\'/tmp\''); \
               con.execute('INSTALL spatial;'); \
               con.execute('LOAD spatial;'); \
               con.close()"

# Vendor Rosetta directly from GitHub into site-packages, including LFS assets.
RUN git clone --depth=1 https://github.com/rogerlew/rosetta /tmp/rosetta && \
    pushd /tmp/rosetta >/dev/null && \
    git lfs pull && \
    popd >/dev/null && \
    rm -rf /tmp/rosetta/.git && \
    mv /tmp/rosetta /opt/venv/lib/python3.10/site-packages/rosetta

# Prepare filesystem layout that historically lived at /workdir.
RUN mkdir -p /workdir /opt/vendor /var/log/wepppy /var/lib/wepppy && \
    chown -R root:root /workdir /opt/vendor /var/log/wepppy /var/lib/wepppy

# Bring the application source into the image.
COPY . /workdir/wepppy

# Copy pre-built static vendor assets generated in the Node stage.
COPY --from=static-builder /app/dist/vendor/ /workdir/wepppy/wepppy/weppcloud/static/vendor/

# Seed sibling repositories that were previously mounted via .pth files.
RUN set -euxo pipefail; \
    clone_repo() { \
        local repo_ref="$1" repo_url="$2" dest="$3"; \
        git clone --depth=1 --branch "${repo_ref}" "${repo_url}" "${dest}" || { \
            git clone --depth=1 "${repo_url}" "${dest}"; \
            pushd "${dest}" >/dev/null; \
            git fetch --depth=1 origin "${repo_ref}"; \
            git checkout "${repo_ref}"; \
            popd >/dev/null; \
        }; \
        pushd "${dest}" >/dev/null; \
        git lfs pull || true; \
        popd >/dev/null; \
        rm -rf "${dest}/.git"; \
    }; \
    clone_repo "${WEPPPY2_REF}" "${WEPPPY2_REPO}" /opt/vendor/wepppy2; \
    clone_repo "${WEPPCLOUD2_REF}" "${WEPPCLOUD2_REPO}" /opt/vendor/weppcloud2; \
    clone_repo "${F_ESRI_REF}" "${F_ESRI_REPO}" /opt/vendor/f-esri; \
    clone_repo "${WBT_REF}" "${WBT_REPO}" /opt/vendor/whitebox-tools; \
    clone_repo "${WEPPPYO3_REF}" "${WEPPPYO3_REPO}" /opt/vendor/wepppyo3; \
    rm -rf /workdir/wepppy2 /workdir/weppcloud2 /workdir/f-esri /workdir/whitebox-tools /workdir/wepppyo3; \
    ln -s /opt/vendor/wepppy2 /workdir/wepppy2; \
    ln -s /opt/vendor/weppcloud2 /workdir/weppcloud2; \
    ln -s /opt/vendor/f-esri /workdir/f-esri; \
    ln -s /opt/vendor/whitebox-tools /workdir/whitebox-tools; \
    ln -s /opt/vendor/wepppyo3 /workdir/wepppyo3

# Stage the prebuilt wepppyo3 release into site-packages for runtime imports.
RUN set -euxo pipefail; \
    SITE_PACKAGES=$(/opt/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'); \
    mkdir -p "${SITE_PACKAGES}/wepppyo3"; \
    cp -a /opt/vendor/wepppyo3/release/linux/py310-wepppy310-env/wepppyo3/. "${SITE_PACKAGES}/wepppyo3/"

# Generate equivalent .pth injections inside the virtual environment.
RUN set -euxo pipefail; \
    SITE_PACKAGES=$(/opt/venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'); \
    printf "/workdir/wepppy/\n" > "${SITE_PACKAGES}/wepppy.pth"; \
    printf "/workdir/wepppy2/\n" > "${SITE_PACKAGES}/wepp_runner.pth"; \
    printf "/workdir/weppcloud2/\n" > "${SITE_PACKAGES}/weppcloud2.pth"; \
    printf "/workdir/whitebox-tools/WBT/\n" > "${SITE_PACKAGES}/wbt.pth"; \
    printf "/workdir/f-esri/\n" > "${SITE_PACKAGES}/f_esri.pth"; \
    printf "/workdir/wepppyo3/release/linux/py310-wepppy310-env/\n" > "${SITE_PACKAGES}/wepppyo3.pth"

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PROJ_LIB=/usr/share/proj
ENV GDAL_DATA=/usr/share/gdal
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/matplotlib

RUN set -euxo pipefail; \
    GROUP_NAME="${APP_GROUP}"; \
    if getent group "${APP_GID}" >/dev/null; then \
        GROUP_NAME="$(getent group "${APP_GID}" | cut -d: -f1)"; \
    elif getent group "${APP_GROUP}" >/dev/null; then \
        groupmod -g "${APP_GID}" "${APP_GROUP}"; \
    else \
        groupadd -g "${APP_GID}" "${APP_GROUP}"; \
    fi; \
    if id -u "${APP_USER}" >/dev/null 2>&1; then \
        usermod -g "${GROUP_NAME}" -u "${APP_UID}" "${APP_USER}"; \
    else \
        useradd --no-log-init -r -g "${GROUP_NAME}" -u "${APP_UID}" -m "${APP_USER}"; \
    fi; \
    chown -R "${APP_USER}:${GROUP_NAME}" /workdir /opt/vendor /opt/venv /var/log/wepppy /var/lib/wepppy /tmp

USER ${APP_USER}

WORKDIR /workdir/wepppy

EXPOSE 8000

CMD ["gunicorn", "--workers", "4", "--threads", "2", "--timeout", "1800", "--bind", "0.0.0.0:8000", "--log-level", "info", "wepppy.weppcloud.app:app"]
