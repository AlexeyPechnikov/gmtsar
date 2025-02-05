# https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html
# https://github.com/jupyter/docker-stacks/blob/main/base-notebook/Dockerfile
# https://hub.docker.com/repository/docker/mobigroup/pygmtsar
# host platform compilation:
# docker build . -f pygmtsar.Dockerfile -t mobigroup/pygmtsar:latest --no-cache
# cross-compilation:
# docker buildx build . -f pygmtsar.Dockerfile -t mobigroup/pygmtsar:latest --no-cache --platform linux/amd64 --load
FROM jupyter/scipy-notebook:ubuntu-22.04

USER root

# install GMTSAR dependencies and some helpful command-line tools
RUN apt-get -y update \
&&  apt-get -y install git gdal-bin libgdal-dev subversion curl jq \
&&  apt-get -y install csh autoconf make gfortran \
&&  apt-get -y install libtiff5-dev libhdf5-dev liblapack-dev libgmt-dev gmt \
&&  apt-get -y install zip htop mc netcdf-bin \
&&  apt-get clean && rm -rf /var/lib/apt/lists/*

# define installation and binaries search paths
ARG GMTSAR=/usr/local/GMTSAR
ARG ORBITS=/usr/local/orbits
ENV PATH=${GMTSAR}/bin:$PATH

# install GMTSAR from git
RUN cd $(dirname ${GMTSAR}) \
&&  git config --global advice.detachedHead false \
&&  git clone --branch master https://github.com/gmtsar/gmtsar GMTSAR \
&&  cd ${GMTSAR} \
&&  git checkout e98ebc0f4164939a4780b1534bac186924d7c998 \
&&  autoconf \
&&  ./configure --with-orbits-dir=${ORBITS} CFLAGS='-z muldefs' LDFLAGS='-z muldefs' \
&&  make \
&&  make install

# install PyGMTSAR and additional libraries
RUN apt-get -y update \
&&  apt-get -y install xvfb libegl1-mesa libgdal-dev gdal-bin \
&&  apt-get clean && rm -rf /var/lib/apt/lists/*
RUN conda install -y -c conda-forge vtk panel xvfbwrapper pyvista
# magick fix for the library
RUN pip3 uninstall -y h5py
# use requirements.sh to build the installation command
RUN pip3 install \
    asf_search==7.0.4 \
    h5netcdf==1.3.0 \
    h5py==3.10.0 \
    rasterio==1.3.11 \
    ipywidgets==8.1.1 \
    ipyleaflet==0.19.1 \
    remotezip==0.12.2 \
    jupyter_bokeh \
    pygmtsar \
&& jupyter lab build \
&& jupyter labextension install jupyter-leaflet \
&& jupyter labextension list

# modify start-notebook.py to start Xvfb
RUN sed -i '/import sys/a \
# Start Xvfb\n\
import xvfbwrapper\n\
display = xvfbwrapper.Xvfb(width=1280, height=1024)\n\
display.start()' /usr/local/bin/start-notebook.py

# grant passwordless sudo rights
RUN echo "${NB_USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# switch user
USER    ${NB_UID}
WORKDIR "${HOME}"

# Clone only the pygmtsar2 branch
RUN git config --global http.postBuffer 524288000 \
&& git clone --branch pygmtsar2 --single-branch https://github.com/AlexeyPechnikov/pygmtsar.git \
&& mv pygmtsar/notebooks ./notebooks \
&& mv pygmtsar/README.md ./ \
&& rm -rf pygmtsar work


