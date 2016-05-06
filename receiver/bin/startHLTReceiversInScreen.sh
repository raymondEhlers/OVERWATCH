#!/usr/bin/env bash

# The receiver seems to die (ie fail to receiver) from time to time, so we can use this script to restart it every 24 hours using crom

# Determine current location of file
# From: http://stackoverflow.com/a/246128 
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration and shared functions
source "$currentLocation/hltReceiverConfiguration.sh"

# Log the date
echoInfo "Starting HLT receivers at $(date)"

# Kill the previous instance
# PGID = Process Group ID
previousPGID=$(ps -e -o user,pid,pgid,args | grep "[b]ash ./startReceivers.sh" | awk '{print $3}')
#previousPID=$(ps aux | grep "[b]ash ./startReceivers.sh" | awk '{print $2}')
if [[ $previousPGID -ne 0 ]];
then
    echoInfo "Killing process group ID $previousPGID"
    # The - before the PGID sends the signal to all processes in the group
    kill -INT -$previousPGID
    sleep 1
fi

# Start the receiver up again
# Test from: https://stackoverflow.com/a/11092727
screenName="receivers"
if screen -ls | awk '{print $1}' | grep -q $screenName;
then
    echoInfo "Screen session $screenName exists"
else
    echoInfo "Screen session $screenName does not exists"
    echoInfo "Creating screen session $screenName"
    # Have to use bash to create a bash session to be certain that it persists after detachment.
    # See: https://serverfault.com/a/104670
    screen -S $screenName -d -m bash -c "exec bash"
fi

# Inject the command into the screen session
# stuff is the buffer on the screen
# \n is needed so that the command is actually started
#screen -S $screenName -X stuff "cd /data1/emcalTriggerData; pwd; date +%s\n"
echoInfo "Starting ZMQ HLT Receivers in screen"
screen -S $screenName -X stuff "cd $currentLocation; pwd\n"
#screen -S $screenName -X stuff "cd $currentLocation; ./startHLTReceivers.sh\n"
