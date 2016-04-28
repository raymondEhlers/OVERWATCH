#!/usr/bin/env bash

# Script to connect to HLT proxy, and restart it every 30 minutes

if [[ "$#" -ne 3 ]];
then
    echo "Did not define normal number of arguments. Gave $#, but expected 3"
    echo "Continuing using some defualt values."
fi

echo "Loading alice software"
. /home/james/alice/alice-env.sh -n 1 -q

internalPort=${1:-40321}
externalPort=${2:-60321}
receiverType=${3:-"EMC"}

if [[ "$receiverType" == "HLT" ]];
then
    monitorPort=25006
    additionalOptions="-otherHists"
else
    monitorPort=25005
    additionalOptions=""
fi

echo -e "\nSettings:"
echo "internalPort: $internalPort"
echo "externalPort: $externalPort"
echo "receiverType: $receiverType"
echo "monitorPort: $monitorPort"
echo "additionalOptions: $additionalOptions"

# Find process
#sshProcesses=$(pgrep -f "$internalPort:localhost")
sshProcesses=$(pgrep -f "autossh -M $monitorPort")
echo "sshProcesses: $sshProcesses"

# Determine if ssh tunnel is needed.
# autossh should ensure that the connection never dies.
if [[ -z "$sshProcesses" ]];
then
    echo "Did not find necessary $receiverType autossh tunnel. Starting a new one!"
    autossh -M $monitorPort -f -N -L $internalPort:localhost:$externalPort emcalguest@lbnl5core.cern.ch
else
    echo "$receiverType autossh tunnel already found with PID $sshProcesses. Not starting another one."
fi

echo "$PWD"

# select="" ensures that we get all histograms!
ZMQhistViewer in="REQ>tcp://localhost:$internalPort" Verbose sleep=60 timeout=1000 -drawoptions="colzlogy" select="" ${additionalOptions}
