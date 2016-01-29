#!/usr/bin/env bash

# If one of these names is in the hostname, then do not run, since it will not work
if [[ $HOSTNAME != *"pdsf"* && $HOSTNAME != *"sgn"* ]];
then
    echo "Cannot run outside PDSF. Exiting!"
    # Closes the script if it was sourced
    return 0
    echo "You can ignore this error about returning a value! Actually exiting now!"
    # Only get here if the script was executed instead of sourced.
    # Still need to exit.
    exit 0
fi

# Source virtualenv
echo "Loading virtualenv"
# Sets the library path for both python and libffi
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/project/projectdirs/alice/aliprodweb/python_bin/v2.7.11/lib:/project/projectdirs/alice/aliprodweb/essentials/install/lib64"
source /project/projectdirs/alice/aliprodweb/virtualenv/python_2_7_11/bin/activate

# Setup ROOT
echo "Loading ROOT"
cd /project/projectdirs/alice/aliprodweb/ROOT
source bin/thisroot.sh

# Start web server
cd /project/projectdirs/alice/aliprodweb/aliemcalmonitor
#nohup uwsgi /project/projectdirs/alice/aliprodweb/aliemcalmonitor/config/wsgiConfig.ini &> project/projectdirs/alice/aliprodweb/aliemcalmonitor/app.log &
#nohup python /project/projectdirs/alice/aliprodweb/aliemcalmonitor/serveHists.py &> project/projectdirs/alice/aliprodweb/aliemcalmonitor/app.log &
