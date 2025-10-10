# syntax=docker/dockerfile:1
FROM python:3.10-slim AS base

# Preinstall build toolchain and native libraries required by geospatial wheels.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        git-lfs \
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
        zlib1g-dev && \
    git lfs install --system && \
    rm -rf /var/lib/apt/lists/*

ENV UV_SKIP_UPDATE_CHECK=1

# Install the uv CLI from Astral.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Resolve Python dependencies with uv inside a dedicated virtual environment.
COPY docker/requirements-uv.txt ./requirements-uv.txt
COPY docker/wheels /tmp/wheels
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --requirement requirements-uv.txt

# Mirror historical conda .pth injections so sibling repos resolve in development.
COPY install/conda/*.pth /tmp/pth/
RUN for f in /tmp/pth/*.pth; do \
        cp "$f" /opt/venv/lib/python3.10/site-packages/; \
    done

# Vendor Rosetta directly from GitHub into site-packages, including LFS assets.
RUN git clone --depth=1 https://github.com/rogerlew/rosetta /tmp/rosetta && \
    cd /tmp/rosetta && \
    git lfs pull && \
    rm -rf .git && \
    mv /tmp/rosetta /opt/venv/lib/python3.10/site-packages/rosetta

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PROJ_LIB=/usr/share/proj
ENV GDAL_DATA=/usr/share/gdal

CMD ["bash"]
