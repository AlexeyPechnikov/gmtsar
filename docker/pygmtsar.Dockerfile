# https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html
# https://github.com/jupyter/docker-stacks/blob/main/base-notebook/Dockerfile
# https://hub.docker.com/repository/docker/mobigroup/pygmtsar
# host platform compilation:
# docker build . -f pygmtsar.Dockerfile -t mobigroup/pygmtsar:latest --no-cache
# cross-compilation:
# docker buildx build . -f pygmtsar.Dockerfile -t mobigroup/pygmtsar:latest --no-cache --platform linux/amd64 --load
FROM quay.io/jupyter/scipy-notebook:ubuntu-24.04

USER root

# grant passwordless sudo rights
RUN echo "${NB_USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# install command-line tools
RUN apt-get -y update && apt-get -y upgrade && apt-get -y install \
    git subversion curl jq csh zip htop mc netcdf-bin \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

##########################################################################################
# Install GMTSAR
##########################################################################################
# install dependencies
RUN apt-get -y update && apt-get -y install \
    autoconf make gfortran \
    gdal-bin libgdal-dev \
    libtiff5-dev \
    libhdf5-dev \
    liblapack-dev \
    gmt libgmt-dev \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

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
&&  make install \
&&  make clean

# system cleanup
RUN apt-get -y remove --purge \
    libgdal-dev autoconf make gfortran \
    libtiff5-dev libhdf5-dev liblapack-dev libgmt-dev \
&&  apt-get autoremove -y --purge

##########################################################################################
# Install VTK
##########################################################################################
# install dependencies
RUN apt-get -y update && apt-get -y install \
    libopengl0 mesa-utils \
    libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev \
    cmake ninja-build python3-dev build-essential \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install python vtk library
RUN git clone https://gitlab.kitware.com/vtk/vtk.git \
&&  cd vtk \
&&  git checkout v9.3.1 \
&&  mkdir build && cd build \
&&  cmake ../ \
  -GNinja \
  -DCMAKE_BUILD_TYPE=Release \
  -DVTK_DEFAULT_RENDER_WINDOW_OFFSCREEN=ON \
  -DVTK_OPENGL_HAS_EGL=ON \
  -DVTK_OPENGL_HAS_OSMESA=OFF \
  -DVTK_USE_X=OFF \
  -DCMAKE_INSTALL_PREFIX=/opt/conda \
  -DVTK_WRAP_PYTHON=ON \
  -DVTK_PYTHON_VERSION=3 \
&&  ninja -j$(nproc) \
&&  ninja install \
&&  cd ../.. \
&&  rm -fr vtk

# system cleanup
RUN apt-get -y remove --purge \
    libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev \
    cmake ninja-build python3-dev build-essential \
&&  apt-get autoremove -y --purge

##########################################################################################
# Install PyGMTSAR
##########################################################################################
# install dependencies to build rasterio
RUN apt-get -y update && apt-get -y install \
    libgdal-dev build-essential \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install PyGMTSAR and visualization libraries
RUN /opt/conda/bin/pip3 install --no-cache-dir \
    ipywidgets \
    ipyleaflet \
    xvfbwrapper \
    jupyter_bokeh \
    jupyter-leaflet \
    panel \
    trame trame-vtk trame-client trame-server
RUN /opt/conda/bin/pip3 install --no-cache-dir git+https://github.com/mobigroup/gmtsar.git@pygmtsar2#subdirectory=pygmtsar

# install recent pyvista with invalid dependencies specification
RUN /opt/conda/bin/pip3 install --no-cache-dir matplotlib pillow pooch scooby typing-extensions \
&&  /opt/conda/bin/pip3 install --no-cache-dir --no-deps pyvista

# system cleanup
RUN apt-get -y remove --purge \
    libgdal-dev build-essential \
&&  apt-get autoremove -y --purge

##########################################################################################
# Install Virtual Frame Buffer for PyVista
##########################################################################################
# install dependencies to compile
RUN apt-get -y update && apt-get -y install \
    xvfb \
&&  apt-get clean \
&&  rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# modify start-notebook.py to start Xvfb
RUN sed -i '/import sys/a \
# Start Xvfb\n\
import xvfbwrapper\n\
display = xvfbwrapper.Xvfb(width=1280, height=1024)\n\
display.start()' /usr/local/bin/start-notebook.py

##########################################################################################
# Install PyGMTSAR examples
##########################################################################################

# switch user
USER    ${NB_UID}
WORKDIR "${HOME}"

# Clone only the pygmtsar2 branch
RUN git config --global http.postBuffer 524288000 \
&& git clone --depth=1 --branch pygmtsar2 --single-branch https://github.com/AlexeyPechnikov/pygmtsar.git \
&& mv pygmtsar/notebooks ./notebooks \
&& mv pygmtsar/README.md ./ \
&& rm -rf pygmtsar work
