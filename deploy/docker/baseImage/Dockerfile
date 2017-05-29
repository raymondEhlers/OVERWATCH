# Docker file for the OVERWATCH web app
FROM ubuntu:latest
MAINTAINER raymond.ehlers@cern.ch

# Installed neede packages
# ROOT dependencies start from libncurses
run apt-get update && apt-get install -y \
        build-essential \
        git \
        python-dev \
        python-pip \
        nginx \
        ufw \
        supervisor \
        libncurses5-dev \
        gfortran \
        libperl-dev \
        libbz2-dev \
        libbison-dev \
        libssl-dev \
        byacc \
        flex \
        curl \
        swig \
        libglu1-mesa-dev \
        autotools-dev \
        autoconf \
        texinfo \
        pkg-config \
        autopoint \
        libtool-bin \
        cmake \
        libxml2-dev \
        zlib1g-dev \
        libfreetype6-dev \
        libxft-dev \
        libxpm-dev \
        environment-modules \
        npm \
    && rm -rf /var/lib/apt/lists/*
        # Can't use gsl because the version is incompatible
        # We delete the intermediate apt-get files once we are done
        # npm is for bower - see below

# TODO: Set c, cxx flags, and CMAKE_BUILD_TYPE
# TODO: Copy build scripts

# Install XRootD
RUN mkdir -p /opt/scratch && cd /opt/scratch \
        && git clone https://github.com/xrootd/xrootd.git \
        && mkdir -p xrootd/build && cd xrootd/build \
        && ./buildXRootD.sh ../ /opt/xrootd \
        && make -j2 install \
        && rm -r /opt/scratch/xrootd
# Remove src and build files

# Install ROOT
RUN mkdir -p /opt/scratch/root && cd /opt/sratch/root \
        && git clone https://github.com/root-project/root.git src \
        && mkdir build && cd build \
        && ./buildRoot.sh ../src /opt/root \
        && make -j2 install
        && rm -r /opt/scratch/root
# Remove src and build files

# Eventually add ZMQ helpers

# Setup ROOT via aliBuild
# WARNING: This is a slow step - it has to clone and build root and all of it's dependencies!
# Remove the ROOT source and build files to save space!
#RUN pip install aliBuild==1.4.0.rc1 \
#        && mkdir /alice \
#        && cd /alice \
#        && aliBuild analytics off \
#        && aliBuild -z root6 --defaults root6 init ROOT \
#        && cd /alice/root6 && aliBuild -z -w ../sw --defaults root6 -d build ROOT \
#        && cd /alice \
#        && rm -r /alice/sw/BUILD \
#        && rm -r /alice/sw/INSTALLROOT \
#        && rm -r /alice/sw/MIRROR \
#        && rm -r /alice/sw/SOURCES \
#        && rm -r /alice/sw/SPECS \
#        && rm -r /alice/sw/TARS \
#        && rm -r /alice/root6

# Nothing further is configured here since this is just a base image!
CMD ["/bin/bash"]
