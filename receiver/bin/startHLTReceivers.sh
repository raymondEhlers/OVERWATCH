#!/usr/bin/env bash

#############################
# Start desired ZMQ HLT receivers
#############################

# Determine current location of file
# From: http://stackoverflow.com/a/246128 
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration and shared functions
source "$currentLocation/hltReceiverConfiguration.sh"

# To trap a control-c during the log
# See: http://rimuhosting.com/knowledgebase/linux/misc/trapping-ctrl-c-in-bash
trap ctrl_c INT

function ctrl_c() {
echoInfo "\nClosing ZMQ HLT receivers:"
for (( i = 0; i < ${#subsystems[@]}; i++ ));
do
    echoInfo "Killing ${subsystems[i]} with PID ${receiverPIDs[i]}."
    kill -INT ${receiverPIDs[i]}
done
exit
}

# Move the directory of the script to ensure that the other files can be found
cd "$currentLocation"
echoInfo "Runnig `basename "$0"` in \"$PWD\""

# To contain the created PIDs
receiverPIDs=()

# Start the receiver for each subsystem and save the PID so that it can be killed later
for (( i = 0; i < ${#subsystems[@]}; i++ ));
do
    echo #EMPTY
    echoInfo "Starting receiver for ${subsystems[i]}!"
    # Start receiver for the subsystem
    ./runHLTReceiver.sh ${internalReceiverPorts[i]} ${externalReceiverPorts[i]} ${subsystems[i]} &
    # Save PID to kill the receiver later
    receiverPIDs+=( $! ) 
    echoInfo "${subsystems[i]} PID: ${receiverPIDs[i]}"

    # Ensure that the output is still readable and that the receiver is able to start.
    sleep 1
done

echo #EMPTY
echoInfo "Finished starting receivers!"

# Keep the script open so that it can kill the receivers later
while [[ true ]];
do
    sleep 1
done
