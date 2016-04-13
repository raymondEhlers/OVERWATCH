#!/usr/bin/env bash

# Determine if the script was run or sourced.
# See: https://stackoverflow.com/a/2684300
sourcedScript=false
if [[ "${BASH_SOURCE[0]}" != "${0}" ]];
then
    echo "Script is being sourced!"
    sourcedScript=true
fi

# Determine variables
if [[ $HOSTNAME == *"pdsf"* || $HOSTNAME == *"sgn"* ]];
then
    # Define necessary variables
    projectPath="/project/projectdirs/alice/aliprodweb/overwatch"
    rootSysPath="/project/projectdirs/alice/aliprodweb/ROOT/"
    virtualEnvPath="/project/projectdirs/alice/aliprodweb/virtualenv/python_2_7_11/bin/activate"
    location="PDSF"

    # Additional settings
    # Sets the library path for both python and libffi
    export LD_LIBRARY_PATH="/project/projectdirs/alice/aliprodweb/python_bin/v2.7.11/lib:/project/projectdirs/alice/aliprodweb/essentials/install/lib64:$LD_LIBRARY_PATH"
else
    if [[ "$HOSTNAME" == "aliceoverwatch" ]];
    then
        # Define necessary variables
        projectPath="/opt/www/aliceoverwatch"
        rootSysPath="/opt/aliceSW/root/alice_v5-34-30/inst/"
        virtualEnvPath="/opt/www/aliceoverwatch/.env/bin/activate"
        location="Yale"

        # Additional settings
        # None!
    else
        echo "Cannot run on hostname $HOSTNAME. You need to define the necessary variables."
        if [[ "$sourcedScript" == true ]];
        then
            return
        else
            exit 0
        fi
    fi
fi

# Source virtualenv
echo "Loading virtualenv"
source "$virtualEnvPath"

# Setup ROOT
echo "Loading ROOT"
cd "$rootSysPath"
source bin/thisroot.sh

# Return to the project directory
cd "$projectPath"

if [[ "$sourcedScript" == true ]];
then
    echo "Environment ready for use!"
else
    # Start web server
    echo "Starting uwsgi with config at $projectPath/config/wsgi${location}.ini"
    nohup uwsgi "$projectPath/config/wsgi${location}.ini" &> "$projectPath/app.log" &
fi
