#!/usr/bin/env bash
# AliRoot

# Setup environment
export ROOTSYS=/opt/root
export PATH=$PATH:/opt/root/bin

SRC=$1
INST=$2

cmake "$SRC" \
    -DCMAKE_INSTALL_PREFIX="$INST" \
    -DCMAKE_C_COMPILER=`root-config --cc` \
    -DCMAKE_CXX_COMPILER=`root-config --cxx` \
    -DCMAKE_Fortran_COMPILER=`root-config --f77` \
    -DCMAKE_MODULE_LINKER_FLAGS='-Wl,--no-as-needed' \
    -DCMAKE_SHARED_LINKER_FLAGS='-Wl,--no-as-needed' \
    -DCMAKE_EXE_LINKER_FLAGS='-Wl,--no-as-needed' \
    -DROOTSYS="$ROOTSYS" \
    -DCMAKE_BUILD_TYPE=RELWITHDEBINFO
