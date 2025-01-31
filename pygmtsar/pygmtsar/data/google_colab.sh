#!/bin/sh

# Install GMTSAR if needed
count=$(ls /usr/local | grep -c GMTSAR)
if [ "$count" -eq 0 ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update > /dev/null
    apt install -y csh autoconf gfortran \
        libtiff5-dev libhdf5-dev liblapack-dev libgmt-dev gmt > /dev/null
    # GMTSAR codes are not so good to be compiled by modern GCC
    apt install gcc-9 > /dev/null
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 10
    update-alternatives --config gcc
    gcc --version | head -n 1
    git config --global advice.detachedHead false
    cd /usr/local && git clone -q --branch master https://github.com/gmtsar/gmtsar GMTSAR
    # revert recent broken commit
    cd /usr/local/GMTSAR && git checkout e98ebc0f4164939a4780b1534bac186924d7c998 > /dev/null
    cd /usr/local/GMTSAR && autoconf > /dev/null
    cd /usr/local/GMTSAR && ./configure --with-orbits-dir=/tmp > /dev/null
    cd /usr/local/GMTSAR && make 1>/dev/null 2>/dev/null
    cd /usr/local/GMTSAR && make install >/dev/null
    # test one GMTSAR binary
    /usr/local/GMTSAR/bin/make_s1a_tops 2>&1 | head -n 2
fi

# Install virtual framebuffer for interactive 3D visualization
apt install -y xvfb > /dev/null
pip3 install -q pyvista xvfbwrapper jupyter_bokeh vtk panel
# jupyter_bokeh for panel interactive visualization backend blocks tqdm progressbar
# to prevent the issue wrap a Panel component in an IPywidget
# https://panel.holoviz.org/how_to/notebook/notebook.html
#import panel
#panel.extension(comms='ipywidgets')
#panel.extension('vtk')
