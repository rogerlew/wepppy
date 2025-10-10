FROM adoptopenjdk:11-openj9-focal as builder
MAINTAINER asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source https://github.com/dbca-wa/gdal-grande

RUN apt-get update -y
RUN apt-get install -y --fix-missing --no-install-recommends \
            software-properties-common build-essential ca-certificates \
            git make cmake wget unzip libtool automake \
            zlib1g-dev libsqlite3-dev pkg-config sqlite3 \
            swig ant \
            python3-dev python3-numpy \
            libjpeg-dev libgeos-dev \
            curl libcurl4-gnutls-dev libexpat-dev libxerces-c-dev libtiff-dev \
            libwebp-dev \
            bash zip curl \
            libpq-dev libssl-dev \
            autoconf automake sqlite3 bash-completion \
            alien libaio1 \
            rsync ccache \
            libzstd-dev
ARG PROJ_INSTALL_PREFIX=/usr/local

# Build openjpeg
ARG OPENJPEG_VERSION=2.3.1
RUN if test "${OPENJPEG_VERSION}" != ""; then ( \
    wget -q https://github.com/uclouvain/openjpeg/archive/v${OPENJPEG_VERSION}.tar.gz \
    && tar xzf v${OPENJPEG_VERSION}.tar.gz \
    && rm -f v${OPENJPEG_VERSION}.tar.gz \
    && cd openjpeg-${OPENJPEG_VERSION} \
    && cmake . -DBUILD_SHARED_LIBS=ON  -DBUILD_STATIC_LIBS=OFF -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr \
    && make -j$(nproc) \
    && make install \
    && mkdir -p /build_thirdparty/usr/lib \
    && cp -P /usr/lib/libopenjp2*.so* /build_thirdparty/usr/lib \
    && for i in /build_thirdparty/usr/lib/*; do strip -s $i 2>/dev/null || /bin/true; done \
    && cd .. \
    && rm -rf openjpeg-${OPENJPEG_VERSION} \
    ); fi

ARG PROJ_DATUMGRID_LATEST_LAST_MODIFIED
RUN \
    mkdir -p /build_projgrids/${PROJ_INSTALL_PREFIX}/share/proj \
    && curl -LOs http://download.osgeo.org/proj/proj-datumgrid-latest.zip \
    && unzip -q -j -u -o proj-datumgrid-latest.zip  -d /build_projgrids/${PROJ_INSTALL_PREFIX}/share/proj \
    && rm -f *.zip

# Build PROJ
# NOTE: updating the Proj version past 8.2.1 would require refactoring the build system to use CMake.
# Reference: https://proj.org/community/rfc/rfc-7.html
ARG PROJ_VERSION=8.2.1
RUN mkdir proj \
    && wget -q https://github.com/OSGeo/PROJ/archive/refs/tags/${PROJ_VERSION}.tar.gz -O - | tar xz -C proj --strip-components=1 \
    && cd proj \
    && ./autogen.sh \
    && CFLAGS='-DPROJ_RENAME_SYMBOLS -O2' CXXFLAGS='-DPROJ_RENAME_SYMBOLS -O2' \
        ./configure --prefix=${PROJ_INSTALL_PREFIX} --disable-static \
    && make -j$(nproc) \
    && make install DESTDIR="/build" \
    && cd .. \
    && rm -rf proj \
    && PROJ_SO=$(readlink /build${PROJ_INSTALL_PREFIX}/lib/libproj.so | sed "s/libproj\.so\.//") \
    && PROJ_SO_FIRST=$(echo $PROJ_SO | awk 'BEGIN {FS="."} {print $1}') \
    && mv /build${PROJ_INSTALL_PREFIX}/lib/libproj.so.${PROJ_SO} /build${PROJ_INSTALL_PREFIX}/lib/libinternalproj.so.${PROJ_SO} \
    && ln -s libinternalproj.so.${PROJ_SO} /build${PROJ_INSTALL_PREFIX}/lib/libinternalproj.so.${PROJ_SO_FIRST} \
    && ln -s libinternalproj.so.${PROJ_SO} /build${PROJ_INSTALL_PREFIX}/lib/libinternalproj.so \
    && rm /build${PROJ_INSTALL_PREFIX}/lib/libproj.*  \
    && ln -s libinternalproj.so.${PROJ_SO} /build${PROJ_INSTALL_PREFIX}/lib/libproj.so.${PROJ_SO_FIRST} \
    && strip -s /build${PROJ_INSTALL_PREFIX}/lib/libinternalproj.so.${PROJ_SO} \
    && for i in /build${PROJ_INSTALL_PREFIX}/bin/*; do strip -s $i 2>/dev/null || /bin/true; done

# Build GDAL
ARG GDAL_VERSION=v3.0.0
ARG GDAL_RELEASE_DATE
ARG GDAL_BUILD_IS_RELEASE
RUN if test "${GDAL_VERSION}" = "master"; then \
        export GDAL_VERSION=$(curl -Ls https://api.github.com/repos/OSGeo/gdal/commits/HEAD -H "Accept: application/vnd.github.VERSION.sha"); \
        export GDAL_RELEASE_DATE=$(date "+%Y%m%d"); \
    fi \
    && if test "x${GDAL_BUILD_IS_RELEASE}" = "x"; then \
        export GDAL_SHA1SUM=${GDAL_VERSION}; \
    fi \
    && mkdir gdal \
    && mkdir /fgdb \
    && wget -q https://github.com/OSGeo/gdal/archive/${GDAL_VERSION}.tar.gz -O - \
        | tar xz -C gdal --strip-components=1 \
    && wget -q https://github.com/Esri/file-geodatabase-api/raw/master/FileGDB_API_1.5.1/FileGDB_API_1_5_1-64.tar.gz -O - \
        | tar xz -C /fgdb --strip-components=1 \
    && cd gdal/gdal \
    && export CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0" \
    && ./configure --prefix=/usr --without-libtool \
    --with-hide-internal-symbols \
    --with-jpeg12 \
    --with-java=/opt/java/openjdk \
    --with-fgdb=/fgdb \
    --with-webp --with-proj=/build${PROJ_INSTALL_PREFIX} \
    --with-libtiff=internal --with-rename-internal-libtiff-symbols \
    --with-geotiff=internal --with-rename-internal-libgeotiff-symbols \
    --with-oci=/usr/lib/oracle/${ORACLECLIENT_VERSION}/client64 \
    && make -j$(nproc) \
    && cd swig/java \
    && make -j$(nproc) \
    && cd ../.. \
    && make install DESTDIR="/build" \
    && mv swig/java /build/usr/share/gdal/libso \
    && cp /fgdb/lib/*.so /build/usr/share/gdal/libso \
    && cd ../.. \
    && rm -rf gdal \
    && mkdir -p /build_gdal_version_changing/usr/include \
    && mv /build/usr/lib                    /build_gdal_version_changing/usr \
    && mv /build/usr/include/gdal_version.h /build_gdal_version_changing/usr/include \
    && mv /build/usr/bin                    /build_gdal_version_changing/usr \
    && for i in /build_gdal_version_changing/usr/lib/*; do strip -s $i 2>/dev/null || /bin/true; done \
    && for i in /build_gdal_version_changing/usr/bin/*; do strip -s $i 2>/dev/null || /bin/true; done

FROM adoptopenjdk:11-openj9-focal as runner
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y --no-install-recommends libsqlite3-0 curl unzip

# GDAL dependencies
RUN apt-get install -y --no-install-recommends \
        python3-numpy libpython3.6 \
        libjpeg-turbo8 \
        libgeos-3.8.0 \
        libtiff5 \
        libgeos-c1v5 \
        libcurl4 libexpat1 \
        libxerces-c3.2 \
        libwebp6 \
        libzstd1 bash libpq5 libssl1.1

# Oracle install dependencies
RUN apt-get install -y --no-install-recommends \
        alien libaio1

# Order layers starting with less frequently varying ones
COPY --from=builder  /build_thirdparty/usr/ /usr/
COPY --from=builder  /build_projgrids/ /usr/

ARG PROJ_INSTALL_PREFIX=/usr/local
COPY --from=builder  /build${PROJ_INSTALL_PREFIX}/share/proj/ ${PROJ_INSTALL_PREFIX}/share/proj/
COPY --from=builder  /build${PROJ_INSTALL_PREFIX}/include/ ${PROJ_INSTALL_PREFIX}/include/
COPY --from=builder  /build${PROJ_INSTALL_PREFIX}/bin/ ${PROJ_INSTALL_PREFIX}/bin/
COPY --from=builder  /build${PROJ_INSTALL_PREFIX}/lib/ ${PROJ_INSTALL_PREFIX}/lib/

COPY --from=builder  /build/usr/share/gdal/ /usr/share/gdal/
COPY --from=builder  /build/usr/include/ /usr/include/
COPY --from=builder  /build_gdal_version_changing/usr/ /usr/
RUN (for so in /usr/share/gdal/libso/*.so; do ln -s $so /usr/lib/; done)

RUN ldconfig -v

# Remove unused libs
RUN apt-get remove alien -y && apt-get autoremove -y
