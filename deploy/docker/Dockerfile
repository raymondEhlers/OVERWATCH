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
    && rm -rf /var/lib/apt/lists/*
        # Can't use gsl because the version is incompatible
        # We delete the intermediate apt-get files once we are done

# Setup ROOT via aliBuild
RUN pip install aliBuild==1.4.0.rc1 \
        && mkdir /alice \
        && cd /alice \
        && aliBuild analytics off \
        && aliBuild -z root6 --defaults root6 init ROOT \
        && cd root6
        #&& aliBuild -z root6 --defaults root6 init

# Run on it's own since it's very slow
RUN cd /alice/root6 && aliBuild -z -w ../sw --defaults root6 build ROOT

# Remove the ROOT source and build files to save space!
RUN rm -r /alice/sw/BUILD && rm -r /alice/root6

# Add the patch to properly set the python path with root
#copy rootPythonPath.patch /alice/root6/.
#
## Apply the patch and build root
#run cd /alice/root6/alidist \
#        && git config --global user.name "Raymond Ehlers" && git config --global user.email "raymond.ehlers@cern.ch" \
#        && git am ../rootPythonPath.patch \
#        && cd /alice/root6 
#        && aliBuild -z -w ../sw --defaults root6 build ROOT

# TEMP
# Merge everything except for vim into the above apt-get!
RUN apt-get update && apt-get install -y vim environment-modules

# Setup OVERWATCH
# Download OVERWATCH and setup the needed python packages
RUN git clone https://github.com/raymondEhlers/OVERWATCH.git /overwatch \
        && cd /overwatch/deploy && cd .. \
        && git checkout -b jsRoot origin/jsRoot \
        && pip install -r /overwatch/requirements.txt
        # TODO: Go back to master once jsRoot is merged!

# Configure nginx
# Make NGINX run on the foreground and remove default site config
# Need -f since the file may not exist!
RUN echo "daemon off;" >> /etc/nginx/nginx.conf && rm /etc/nginx/sites-enabled/default
# Copy in nginx and gzip config
COPY nginxConf/*.conf /etc/nginx/conf.d/
COPY nginx.conf /etc/nginx/sites-enabled/.

# Redirect logs to mounted volume!

# Configure OVERWATCH
# TODO: Improve how this is configured!
COPY serverParams.py /overwatch/config/.
# Ensure that the proper configuration file is setup. The values should already be in the file!
RUN cp /overwatch/deploy/configOVERWATCH_stub.sh /overwatch/deploy/configOVERWATCH.sh

# Redirect logs!

# Configure supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80
CMD ["/usr/bin/supervisord"]
