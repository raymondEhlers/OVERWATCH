#!/bin/bash -e
# From: https://github.com/alisw/alidist/blob/master/alien-cas.sh
SOURCEDIR="$1"
DEST="$2"
mkdir -p "$DEST"

for D in $SOURCEDIR/*; do
    [[ ! -d "$D"  ]] && continue
    rsync -a "$D/" "$DEST/"
done
