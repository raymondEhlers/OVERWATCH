#!/usr/bin/env bash

# The receiver seems to die (ie fail to receiver) from time to time, so we can use this script to restart it every 24 hours using crom

# Log the date
date

# Kill the previous instance
# PGID = Process Group ID
previousPGID=$(ps -e -o user,pid,pgid,args | grep "[b]ash ./startReceivers.sh" | awk '{print $3}')
#previousPID=$(ps aux | grep "[b]ash ./startReceivers.sh" | awk '{print $2}')

if [[ $previousPGID -ne 0 ]];
then
    echo "Killing process group ID $previousPGID"
    # The - before the PGID sends the signal to all processes in the group
    kill -INT -$previousPGID
    sleep 1
fi

# Start the receiver up again
# Test from: https://stackoverflow.com/a/11092727
screenName="receivers"
if screen -ls | awk '{print $1}' | grep -q $screenName;
then
    echo "Screen session $screenName exists"
else
    echo "Screen session $screenName does not exists"
    echo "Creating screen session $screenName"
    # Have to use bash to create a bash session to be certain that it persists after detachment.
    # See: https://serverfault.com/a/104670
    screen -S $screenName -d -m bash -c "exec bash"
fi

# Inject the command into the screen session
# stuff is the buffer on the screen
# \n is needed so that the command is actually started
#screen -S $screenName -X stuff "cd /data1/emcalTriggerData; pwd; date +%s\n"
echo "Starting receivers"
screen -S $screenName -X stuff "cd /data1/emcalTriggerData; ./startReceivers.sh\n"
