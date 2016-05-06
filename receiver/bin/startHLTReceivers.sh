#!/usr/bin/env bash

#############################
# Start desired ZMQ HLT receivers
#############################

# Determine current location of file
# From: http://stackoverflow.com/a/246128
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load configuration and shared functions
source "$currentLocation/hltReceiverConfiguration.sh"

# Move the directory of the script to ensure that the other files can be found
cd "$currentLocation"
echoInfoEscaped "Runnig `basename "$0"` at $(date) in \"$PWD\""

# If the PID files exist, then attempt to kill them
if [[ -e ".receiverPIDFile" ]];
then
    echo #EMPTY
    echoInfoEscaped "Closing ZMQ HLT receivers:"
    numberOfPIDs=$(awk 'END{print NR}' .receiverPIDFile)
    for (( i = 1; "$i" <= "$numberOfPIDs"; i++ ));
    do
        # awk number startings from 1!
        pid=$(awk -v i=$i 'NR==i {print $1}' .receiverPIDFile)
        # Gets the command associated with the PID
        # See: https://superuser.com/a/632987
        command=$(ps -p $pid -o command=)
        #echo "command: $command"
        # Checks if PID is actually associated with runHLTReceiver.sh
        if [[ "$command" =~ "runHLTReceiver.sh" ]];
        then
            # Last argument is the subsystem. Defined in call to "runHLTReceiver.sh" below
            # NOTE: The logging and backgrounding does not count towards the number of fields in awk
            # For last argument, see: https://stackoverflow.com/a/2096526
            subsystem=$(echo "$command" | awk '{print $(NF)}')
            #echo "subsystem: $subsystem"

            # Check that the pid corresponds to some receiver and get the subsystem
            echoInfoEscaped "Killing ${subsystem} receiver with PID ${pid}."
            kill -INT ${pid}
        else
            echoInfoEscaped "PID $pid does not seem to correspond to a receiver. Skipping this PID!"
        fi
    done

    # Remove file when done!
    echoInfoEscaped "Removing old PID file"
    rm ".receiverPIDFile"
fi

# To contain the created PIDs
receiverPIDs=()

# Start the receiver for each subsystem and save the PID so that it can be killed later
for (( i = 0; i < ${#subsystems[@]}; i++ ));
do
    echo #EMPTY
    echoInfoEscaped "Starting receiver for ${subsystems[i]}!"
    # Start receiver for the subsystem and log the results
    nohup ./runHLTReceiver.sh ${internalReceiverPorts[i]} ${externalReceiverPorts[i]} ${subsystems[i]} > ${subsystems[i]}Receiver.log 2>&1 &
    # Save PID to kill the receivers later
    receiverPIDs+=( $! ) 
    echoInfoEscaped "${subsystems[i]} PID: ${receiverPIDs[i]}"

    # Ensure that the output is still readable and that the receiver is able to start.
    sleep 1
done

# Write PIDs to file so that they can be killed later
# See: https://stackoverflow.com/a/20243503
echoInfoEscaped "Saving PIDs to .receiverPIDFile"
printf "%s\n" "${receiverPIDs[@]}" > .receiverPIDFile

echo #EMPTY
echoInfoEscaped "Finished starting receivers!"

