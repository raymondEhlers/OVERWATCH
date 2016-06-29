#!/usr/bin/env bash

# Exit safely regardless of using ./ or source.
# Requires "return $?" after the call to the function to complete the process
# The return after the safeExit() call is required because return in safeExit() gets used by the function!!
safeExit() {
    if [[ -z "$1" ]];
    then
        returnCode=1
    else
        returnCode="$1"
    fi

    if [[ "$sourcedScript" == true ]];
    then
        echo "return"
        return "$returnCode"
    else
        echo "exit"
        exit "$returnCode"
    fi
}

# Determine if the script was run or sourced.
# See: https://stackoverflow.com/a/2684300
sourcedScript=false
if [[ "${BASH_SOURCE[0]}" != "${0}" ]];
then
    echo "INFO: Script is being sourced!"
    sourcedScript=true
fi

calledFromSystemd=false
if [[ -n "$1" && ("$1" == "systemd" || "$1" == "upstart") ]];
then
    echo "INFO: Script was called by $1!"
    calledFromSystemd=true
fi

# Determine variables
if [[ $HOSTNAME == *"pdsf"* || $HOSTNAME == *"sgn"* ]];
then
    # Define necessary variables
    projectPath="/project/projectdirs/alice/aliprodweb/overwatch"
    rootSysPath="/project/projectdirs/alice/aliprodweb/ROOT/"
    virtualEnvPath="/project/projectdirs/alice/aliprodweb/virtualenv/python_2_7_11/bin/activate"
    location="PDSF"
    buildType="root"
    role="server"

    # Additional settings
    # Sets the library path for both python and libffi
    export LD_LIBRARY_PATH="/project/projectdirs/alice/aliprodweb/python_bin/v2.7.11/lib:/project/projectdirs/alice/aliprodweb/essentials/install/lib64:$LD_LIBRARY_PATH"
elif [[ "$HOSTNAME" == "aliceoverwatch" ]];
then
    # Define necessary variables
    projectPath="/opt/www/aliceoverwatch"
    rootSysPath="/opt/aliceSW/root/alice_v5-34-30/inst/"
    virtualEnvPath="/opt/www/aliceoverwatch/.env/bin/activate"
    location="Yale"
    buildType="root"
    role="server"

    # Additional settings
    # None!
elif [[ "$HOSTNAME" == "lbnl5core" ]];
then
    # Define necessary variables
    projectPath="/home/emcalguest/overwatch"
    virtualEnvPath="/home/emcalguest/overwatch/.env/bin/activate"
    location="lbnl5"
    buildType="aliBuild"
    role="processing"
    # Not meaningful when using aliBuild
    rootSysPath=""

    # Additional settings
    # None here, but more below (ie PYTHONPATH)
elif [[ "$HOSTNAME" == "lbnl3core" ]];
then
    # Define necessary variables
    projectPath="/home/rehlers/overwatch"
    virtualEnvPath="/home/rehlers/overwatch/.env/bin/activate"
    location="lbnl3"
    buildType="alice-env"
    role="processing"
    rootSysPath="/home/james/alice/"

    # Additional settings
    # None here, but more below (ie PYTHONPATH)
else
    echo "ERROR: Cannot run on hostname $HOSTNAME. You need to define the necessary variables."
    safeExit 1
    return $?
fi

echo "INFO: Running at $location"

# Source virtualenv
echo "INFO: Loading virtualenv"
source "$virtualEnvPath"

# Setup ROOT
echo "INFO: Loading ROOT"
if [[ "$buildType" == "root" ]];
then
    # Setup ROOT using thisroot.sh
    cd "$rootSysPath"
    source bin/thisroot.sh

    # Return to the project directory
    cd "$projectPath"
elif [[ "$buildType" == "aliBuild" ]];
then
    # Setup ROOT using aliBuild
    # Setup aliBuild helper
    eval "`alienv shell-helper`"

    eval "$(alienv load AliRoot/latest-aliMaster)"

    # Setup python in root
    export PYTHONPATH="$ROOTSYS/lib"
elif [[ "$buildType" == "alice-env" ]];
then
    # Load the alice environment
    source "$rootSysPath"/alice-env.sh -n 1 -q
else
    echo "ERROR: Unrecognized build type $buildType! Exiting"
    safeExit 1
    return $?
fi

if [[ "$sourcedScript" == true ]];
then
    echo "INFO: Environment ready for use!"
else
    if [[ "$role" == "server" ]];
    then
        # Start web server
        echo "INFO: Starting uwsgi with config at $projectPath/config/wsgi${location}.ini"
        if [[ "$calledFromSystemd" == true ]];
        then
            uwsgi "$projectPath/config/wsgi${location}.ini" &> "$projectPath/app.log"
        else
            nohup uwsgi "$projectPath/config/wsgi${location}.ini" &> "$projectPath/app.log" &
        fi
    elif [[ "$role" == "processing" ]];
    then
        if [[ "$calledFromSystemd" == true ]];
        then
            echo "ERROR: Processing should not be started from $1! Exiting"
            safeExit 1
            return $?
        fi

        # Check for lockout file
        # Determine current location of file
        # From: http://stackoverflow.com/a/246128
        currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

        # Only process if we are not locked out.
        # Locking out allows changes to processing (for example, reprocessing) without having to disable the crontab
        echo "INFO: Checking for lockOut file."
        if [[ -e "${currentLocation}/lockOut" ]];
        then
            echo "WARNING: Processing locked out! Remove \"lockOut\" file to resume processing with this script! Exiting"
            safeExit 1
            return $?
        fi

        cd "$projectPath"
        # -b for batch mode (ie no graphics)
        echo "INFO: Starting processing"
        python processRuns.py -b
    else
        echo "ERROR: Role $role not recognized. Exiting"
        safeExit 1
        return $?
    fi
fi
