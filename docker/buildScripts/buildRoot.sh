#!/usr/bin/env bash
# ROOT

SRC=$1
INST=$2

cmake "$SRC"                                                  \
    -DCMAKE_BUILD_TYPE="$CMAKE_BUILD_TYPE"                    \
    -DCMAKE_INSTALL_PREFIX="$INST"                            \
    -Dcxx11=ON                                                \
    -Dfreetype=ON                                             \
    -Dbuiltin_freetype=OFF                                    \
    -Dpcre=ON                                                 \
    -DCMAKE_CXX_COMPILER=g++                                  \
    -DCMAKE_C_COMPILER=gcc                                    \
    -DCMAKE_F_COMPILER=gfortran                               \
    -Dpgsql=OFF                                               \
    -Dminuit2=ON                                              \
    -Dpythia6_nolink=ON                                       \
    -Droofit=OFF                                              \
    -Dhttp=ON                                                 \
    -Dsoversion=ON                                            \
    -Dshadowpw=OFF                                            \
    -Dvdt=ON                                                  \
    -DXROOTD_ROOT_DIR="/opt/xrootd"
