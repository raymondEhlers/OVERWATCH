#!/usr/bin/env bash

echo $PWD

# Setup
python /opt/overwatch/deploy/start.py -e config
# Run supervisord to handle signals
/usr/bin/supervisord -c ../supervisord.conf
