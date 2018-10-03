#!/usr/bin/env bash
# XRootD

SRC=$1
INST=$2
# It will fail to find the python3 executable if this is omitted.
# For py2, it will work fine either way.
PYTHON_VERSION=$3

cmake "${SRC}" \
    -DCMAKE_INSTALL_PREFIX="${INST}" \
    -DENABLE_KRB5=TRUE \
    -DXRD_PYTHON_REQ_VERSION="${PYTHON_VERSION}"
