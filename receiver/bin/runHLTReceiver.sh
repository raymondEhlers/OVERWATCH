#!/usr/bin/env bash

# Script to setup ZMQ receiver

# Determine current location of file
# From: http://stackoverflow.com/a/246128
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration and shared functions
if [[ ! -e "$currentLocation/hltReceiverConfiguration.sh" ]];
then
    echo "Must create hltReceiverConfiguration.sh!!"
fi
source "$currentLocation/hltReceiverConfiguration.sh"

# Handle the user not passing the proper options
if [[ "$#" -ne 3 ]];
then
    echoWarnEscaped "Did not define normal number of arguments. Gave $#, but expected 3"
    echoWarnEscaped "Continuing using some defualt values."
fi

# Setup for running receiver
# Add receiver to path
# This script should be located at the same path as the receiver, so we will use that path
echoInfoEscaped "Adding ${currentLocation} to PATH for the zmqReceive executable!"
PATH="$currentLocation:$PATH"

# Variable defined in hltReceiverConfiguration
echoInfoEscaped "Loading alice software"
if [[ "$buildType" == "aliBuild" ]];
then
    # Setup ROOT using aliBuild
    # Need virtualenv
    echoInfoEscaped "Loading virtualenv"
    source "$virtualEnvPath"

    # Setup aliBuild helper
    eval "`alienv shell-helper`"

    echoInfoEscaped "Loading AliRoot from AliBuild"
    alienv load AliRoot/latest-aliMaster

    # Setup python in root
    export PYTHONPATH="$ROOTSYS/lib"
elif [[ "$buildType" == "alice-env" ]];
then
    # Load the alice environment
    echoInfoEscaped "Loading alice software from \"${aliceSoftwarePath}\""
    source "$aliceSoftwarePath"/alice-env.sh -n 1 -q
else
    echo "ERROR: Unrecognized build type $buildType! Exiting"
    exit 1
fi

# Variable defined in hltReceiverConfiguration
echoInfoEscaped "Moving to data directory: \"${dataLocation}\""
cd "${dataLocation}"
echoInfoEscaped "Now in directory: \"$PWD\""

internalPort=${1:-40321}
externalPort=${2:-60321}
subsystem=${3:-"EMC"}

if [[ "$subsystem" == "HLT" ]];
then
    monitorPort=25006
else
    monitorPort=25005
fi

additionalOptions=""

echoInfoEscaped "Receiver Settings:"
echoPropertiesEscaped "Subsystem: $subsystem"
echoPropertiesEscaped "Receiver (interal) Port: $internalPort"
echoPropertiesEscaped "Use SSH tunnel: $useSSHTunnel"
echoPropertiesEscaped "Tunnel (external) Port: $externalPort"
echoPropertiesEscaped "SSH Monitor Port: $monitorPort"
echoPropertiesEscaped "Additional Options: $additionalOptions"

if [[ "${useSSHTunnel}" == true ]];
then
    # Find SSH process
    sshProcesses=$(pgrep -f "autossh -M $monitorPort")
    echoInfoEscaped "autossh PID: $sshProcesses"

    # Determine if ssh tunnel is needed.
    # autossh should ensure that the connection never dies.
    if [[ -z "$sshProcesses" ]];
    then
        echoInfoEscaped "Did not find necessary $subsystem autossh tunnel. Starting a new one!"
        autossh -M $monitorPort -f -N -L $internalPort:localhost:$externalPort emcalguest@lbnl5core.cern.ch
    else
        echoInfoEscaped "$subsystem autossh tunnel already found with PID $sshProcesses. Not starting another one."
    fi
else
    echoInfoEscaped "Not using a SSH tunnel!"
fi

# select="" ensures that we get all histograms(?)
zmqReceive --in="REQ>tcp://localhost:$internalPort" --verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${subsystem}" ${additionalOptions}
