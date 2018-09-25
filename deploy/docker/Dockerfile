# Build portion
# Set the python version here so that we can use it to set the base image. Default to python 2.
ARG PYTHON_VERSION=2.7.15
FROM rehlers/overwatch-base:py${PYTHON_VERSION} as builder
LABEL maintainer="Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University"

# Make the python version available in the container.
ARG PYTHON_VERSION

# Setup directory structure
ENV SCRATCH /opt/scratch
RUN mkdir -p ${SCRATCH}

# Install XRootD
COPY buildScripts/buildXRootD.sh ${SCRATCH}/buildScripts/buildXRootD.sh

RUN mkdir -p ${SCRATCH}/xrootd && cd ${SCRATCH}/xrootd \
        && chmod +x ${SCRATCH}/buildScripts/buildXRootD.sh \
        && git clone https://github.com/xrootd/xrootd.git . \
        && git checkout tags/v4.8.4 \
        && mkdir build && cd build \
        && ${SCRATCH}/buildScripts/buildXRootD.sh ../ /opt/xrootd \
        && make -j2 install \
        && rm -r ${SCRATCH}/xrootd
# Remove src and build files to keep container size down (since we can't cache the build process
# to speed up later compilation). Someday docker might support such a volume build cache which
# would make this split into two docker files particularly useful

# Setup environment variables for the build type.
# For development, it would probably be best to be "RelWithDebInfo"
ARG ROOT_CMAKE_BUILD_TYPE
ENV CMAKE_BUILD_TYPE ${ROOT_CMAKE_BUILD_TYPE:-"MINSIZEREL"}

# Install ROOT
COPY buildScripts/buildRoot.sh ${SCRATCH}/buildScripts/buildRoot.sh

RUN mkdir -p ${SCRATCH}/root && cd ${SCRATCH}/root \
        && chmod +x ${SCRATCH}/buildScripts/buildRoot.sh \
        && git clone https://github.com/root-project/root.git src \
        && cd src && git checkout tags/v6-10-08 && cd .. \
        && mkdir build && cd build \
        && ${SCRATCH}/buildScripts/buildRoot.sh ../src /opt/root ${PYTHON_VERSION} \
        && make -j2 install \
        && rm -r ${SCRATCH}/root
# Remove src and build files to keep container size down (since we can't cache the build process
# to speed up later compilation). Someday docker might support such a volume build cache which
# would make this split into two docker files particularly useful

# TODO: Move to base...
RUN apt-get update && apt-get install -y \
        rsync \
    && rm -rf /var/lib/apt/lists/*
# AliEn Certs needed for EOS
COPY buildScripts/buildAlienCAs.sh /opt/scratch/buildScripts/buildAlienCAs.sh
RUN mkdir -p /opt/scratch/alienCAs && cd /opt/scratch/alienCAs \
        && git clone https://github.com/alisw/alien-cas.git . \
        && /opt/scratch/buildScripts/buildAlienCAs.sh /opt/scratch/alienCAs /opt/alienCAs \
        && rm -r /opt/scratch/alienCAs

# Standard image
FROM rehlers/overwatch-base:py${PYTHON_VERSION}

# Make the python version available in the container.
ARG PYTHON_VERSION

# Setup ENV for XRootD, Root, etc
ENV XROOTDSYS="/opt/xrootd"
ENV ROOTSYS="/opt/root"
ENV PATH="${XROOTDSYS}/bin:${ROOTSYS}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${XROOTDSYS}/lib:${ROOTSYS}/lib:${LD_LIBRARY_PATH}"
# Need the python x.y version (eg `2.7`) to determine the path to the site packages.
# We need to extract it this way because docker supports limited parameter extraction.
RUN PYTHON_VERSION_X_Y=$(python -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
ENV PYTHONPATH="${ROOTSYS}/lib:${XROOTDSYS}/lib/python${PYTHON_VERSION_X_Y}/site-packages/:${PYTHONPATH}"
# Make the AliEn CAs more easily accessible.
ENV X509_CERT_DIR="/opt/alienCAs"

# Copy the /opt directory from the build container which contains XRootD and Root.
COPY --from=builder /opt /opt

# Setup OVERWATCH
ENV OVERWATCH_ROOT /opt/overwatch
WORKDIR ${OVERWATCH_ROOT}
# Download OVERWATCH, setup the needed python packages, and compile the reciever
# Size increase here is mainly due to the numpy dependency
RUN git clone https://github.com/raymondEhlers/OVERWATCH.git . \
        && pip install --upgrade pip \
        && pip install git+https://github.com/SpotlightKid/flask-zodb.git \
        && pip install -e ".[tests, docs]" \
        && mkdir -p receiver/build && cd receiver/build \
        && cmake "../" -DCMAKE_INSTALL_PREFIX="/opt/receiver" -DZEROMQ="/usr" \
        && make install
# Add receiver to path
ENV PATH="/opt/receiver/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/receiver/lib:${LD_LIBRARY_PATH}"

# Add bower, polymer-bundler, Polymer, webcomponents, jsRoot for OVERWATCH
# bower is required for isntalling polymer packages (should move to yarn eventually).
# polymer-bundler is for combining polymer packages into one file for efficiency.
# n allows updates of nodejs, which is needed for polymer-bundler.
RUN npm install -g bower polymer-bundler n \
        && n lts \
        && cd overwatch/webApp/static \
        && bower --allow-root install \
        && cd /tmp && git clone https://github.com/root-project/jsroot.git \
        && mkdir -p ${OVERWATCH_ROOT}/overwatch/webApp/static/jsRoot/ \
        && cp -r jsroot/scripts ${OVERWATCH_ROOT}/overwatch/webApp/static/jsRoot/. && cp -r jsroot/style ${OVERWATCH_ROOT}/overwatch/webApp/static/jsRoot/. \
        && rm -r /tmp/jsroot

# Configure nginx
# Make NGINX run on the foreground and remove default site config
RUN echo "daemon off;" >> /etc/nginx/nginx.conf && rm /etc/nginx/sites-enabled/default

# Configure supervisord
# This launches the Overwatch configuration and parsing script
COPY supervisord.conf ${OVERWATCH_ROOT}

# Expose the ports for nginx and ZODB
EXPOSE 80 8090
CMD ["/usr/bin/supervisord"]

