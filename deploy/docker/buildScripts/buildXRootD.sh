#!/usr/bin/env bash
# XRootD

SRC=$1
INST=$2

cmake "$SRC" \
    -DCMAKE_INSTALL_PREFIX="$INST"
