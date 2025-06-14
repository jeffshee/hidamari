#!/bin/sh
set -e
export TZ=UTC
./lint.sh
meson setup --reconfigure builddir
ninja -C builddir hidamari-pot