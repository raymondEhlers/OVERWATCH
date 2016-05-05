#!/usr/bin/env bash

# Script to setup proxy

# Handle the user not passing the proper options
if [[ "$#" -ne 4 ]];
then
    echo "Did not define normal number of arguments. Gave $#, but expected 4"
    echo "Continuing using some defualt values."
fi

# Determine current location of file
# From: http://stackoverflow.com/a/246128 
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Add receiver to path
# This script should be located at the same path as the receiver, so we will use that path
echo "Adding ${currentLocation} to PATH for the zmqReceive executable!"
PATH="$currentLocation:$PATH"

echo "Loading configruation variables!"
source "$currentLocation/hltReceiverConfiguration.sh"

echo "Loading alice software from \"${aliceSoftwarePath}\""
. ${aliceSoftwarePath}/alice-env.sh -n 1 -q

echo "Moving to data directory: \"${dataLocation}\""
cd "${dataLocation}"

internalPort=${1:-40321}
externalPort=${2:-60321}
receiverType=${3:-"EMC"}
useSSHTunnel=${4:-true}

if [[ "$receiverType" == "HLT" ]];
then
    monitorPort=25006
else
    monitorPort=25005
fi

additionalOptions=""

echo -e "\nSettings:"
echo "internalPort: $internalPort"
echo "externalPort: $externalPort"
echo "receiverType: $receiverType"
echo "SSH Monitor Port: $monitorPort"
echo "Use SSH tunnel: $useSSHTunnel"
echo "additionalOptions: $additionalOptions"

# TEMP
exit 0

if [[ "${useSSHTunnel}" == true ]];
then
    # Find SSH process
    sshProcesses=$(pgrep -f "autossh -M $monitorPort")
    echo "autossh PID: $sshProcesses"

    # Determine if ssh tunnel is needed.
    # autossh should ensure that the connection never dies.
    if [[ -z "$sshProcesses" ]];
    then
        echo "Did not find necessary $receiverType autossh tunnel. Starting a new one!"
        autossh -M $monitorPort -f -N -L $internalPort:localhost:$externalPort emcalguest@lbnl5core.cern.ch
    else
        echo "$receiverType autossh tunnel already found with PID $sshProcesses. Not starting another one."
    fi
else
    echo "Not using an SSH tunnel!"
fi

echo "$PWD"

# select="" ensures that we get all histograms!
zmqReceive --in="REQ>tcp://localhost:$internalPort" --verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${receiverType}" ${additionalOptions}
