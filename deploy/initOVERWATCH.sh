#!/usr/bin/env bash

# This script loads the OVERWATCH environment, and either (1) if run on a processing
# machine: starts the receivers (if necessary) and runs processing, or (2) if run on a server
# machine: starts the wsgi server.
# If the script is sourced rather than executed, only the environment is loaded.

# Script exits if a var is unset
#set -o nounset
# Script exists if an statement returns a non-zero value
# This causes problem if the script is sourced, so this should probably not be enabled!
#set -o errexit

# Determine current location of file
# From: http://stackoverflow.com/a/246128
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Move the directory of the script to ensure that the other files can be found
cd "$currentLocation"

# Load shared functions
source "sharedFunctions.sh"

# Determine docker information
docker=""
if [[ -n "${1:-}" && ("$1" == *"docker"* )  ]];
then
    #export dockerDeploymentOption="$docker"
    # Defaults to deployment
    if [[ -n "$deploymentOption" && "$deploymentOption" == *"devel"* ]];
    then
        # Matches to the options in the uwsgi config
        docker="devel"
    else
        docker="deploy"
    fi

    echoInfoEscaped "Running docker with option ${docker}!"
fi

# Load configuration and shared functions
if [[ ! -e "configOVERWATCH.sh" ]];
then
    echoErrorEscaped "Must create configOVERWATCH.sh!!"
    safeExit 1
    return $?
fi
source "configOVERWATCH.sh"

# Determine if the script was run or sourced.
# See: https://stackoverflow.com/a/2684300
sourcedScript=false
if [[ "${BASH_SOURCE[0]}" != "${0}" ]];
then
    echoInfoEscaped "Script is being sourced!"
    sourcedScript=true
    scriptName=$(basename ${BASH_SOURCE[0]})
else
    scriptName=$(basename "$0")
fi

echoInfoEscaped "Running ${scriptName} at $(date) in \"$PWD\""

# Determine if called from systemd
calledFromSystemd=false
if [[ -n "${1:-}" && ("$1" == "systemd" || "$1" == "upstart") ]];
then
    echoInfoEscaped "Script was called by $1!"
    calledFromSystemd=true
fi

echoInfoEscaped "Running at $location"

# Source virtualenv
echoInfoEscaped "Loading virtualenv"
if [[ -n "$virtualEnvPath" ]];
then
    source "$virtualEnvPath"
fi

# Setup ROOT
echoInfoEscaped "Loading ROOT"
if [[ "$buildType" == "root" ]];
then
    # Setup ROOT using thisroot.sh
    cd "$softwarePath"
    source bin/thisroot.sh

    # Return to the project directory
    cd "$projectPath"
elif [[ "$buildType" == "aliBuild" ]];
then
    # Setup ROOT using aliBuild
    # Setup aliBuild helper
    if [[ -n "$softwarePath" ]];
    then
        export ALICE_WORK_DIR="$softwarePath"
    fi
    eval "`alienv shell-helper`"

    #if [[ "$sourcedScript" == true ]];
    #then
        alienv load "$alibuildName"
    #else
    #    eval "$(alienv load AliRoot/latest-aliMaster)"
    #fi

    # List modules
    alienv list

    # Setup python in root
    # Only set the path if ROOTSYS haven't already been added
    if [[ ! "$PYTHONPATH" == *"$ROOTSYS"* ]];
    then
        export PYTHONPATH="$ROOTSYS/lib:$PYTHONPATH"
    fi
elif [[ "$buildType" == "alice-env" ]];
then
    # Load the alice environment
    source "$softwarePath"/alice-env.sh -n 1 -q
else
    echoErrorEscaped "Unrecognized build type $buildType! Exiting"
    safeExit 1
    return $?
fi

if [[ "$sourcedScript" == true ]];
then
    echoInfoEscaped "Environment ready for use!"
    # Return to the project directory to get started
    cd "$projectPath"
else
    if [[ "$role" == "server" ]];
    then
        #############################
        # Start web server
        #############################

        if [[ -n "$docker" ]];
        then
            echoInfoEscaped "Starting uwsgi with config at $projectPath/deploy/docker/uwsgi.ini with deployment option $deploymentOption"
            uwsgi "$projectPath/deploy/docker/uwsgi.ini" &> "$projectPath/app.log"
        else
            echoInfoEscaped "Starting uwsgi with config at $projectPath/deploy/wsgi${location}.ini"
            if [[ "$calledFromSystemd" == true ]];
            then
                uwsgi "$projectPath/deploy/wsgi${location}.ini" &> "$projectPath/app.log"
            else
                nohup uwsgi "$projectPath/deploy/wsgi${location}.ini" &> "$projectPath/app.log" &
            fi
        fi
    elif [[ "$role" == "processing" ]];
    then
        # In this case, we will start the receivers (if necessary), and execute processing

        #############################
        # Check whether the ZMQ receivers are running, and if not, start them
        #############################
        echo #EMPTY
        echoInfoEscaped "Checking whether receivers exist, and starting them if not..."

        # get the zmq processing running, and create an array of relevant info (process name, subsystem, port, PID)
        arr=($(ps aux | awk '/[z]mqReceive/ {printf "%s %s %s %s\n", $11, $NF, $12, $2}'))

        if [[ ${forceRestart} == true ]]; then
          echoInfoEscaped "Force restart requested -- all previous receivers will be killed, and a new receiver will be started for each subsystem."
        fi

        if [[ $((${#arr[@]}/4)) -gt "${#subsystems[@]}" ]]; then
          echoWarnEscaped "There are more zmqReceivers running than there are subsystems! Forcing a re-start of all receivers at relevant ports..."
          forceRestart=true
        fi
        echo #EMPTY

        # Loop through subsystems, and re-start each receiver if appropriate
        for (( n=0; n<"${#subsystems[@]}"; n++ ))
        do
          subsystemLog="${currentLocation}/${subsystems[n]}Receiver.log"
          echoInfoEscaped "See ${currentLocation}/${subsystems[n]}Receiver.log for details."
          echoInfoEscaped "Checking for ${subsystems[n]} receiver..." > ${subsystemLog}

          foundReceiver=false
          startReceiver=true

          # loop through running processes (each process stores the 4 entries above)
          for (( i=0; i<${#arr[@]}; i=i+4 ))
          do
            processName_i=${arr[i]}
            subsystem_i=${arr[i+1]}
            port_i=${arr[i+2]}
            pid_i=${arr[i+3]}

            # check if subsystem and port and name match the process
            if [[ $(echo $subsystem_i | grep "${subsystems[n]}") ]]; then
              if [[ $(echo $port_i | grep "${internalReceiverPorts[n]}") ]]; then
                if [[ $(echo ${processName_i} | grep "zmqReceive") ]]; then
                  # We found a match
                  echoInfoEscaped "Found ${subsystems[n]} receiver!" >> ${subsystemLog}
                  foundReceiver=true
                  startReceiver=false

                  # If forceRestart is enabled, kill the receiver
                  if [[ ${forceRestart} == true ]]; then
                    kill ${pid_i}
                    echoInfoEscaped "Force restart is requested -- killed receiver ${subsystems[n]}" >> ${subsystemLog}
                    startReceiver=true
                  fi

                fi
              fi
            fi

          done

          if [[ ${foundReceiver} == false ]]; then
            echoInfoEscaped "No ${subsystems[n]} receiver found!" >> ${subsystemLog}
          fi

          # If we don't find a match, or if the receiver has been killed, we must start a receiver for this subsystem
          if [[ ${startReceiver} == true ]]; then

            echoInfoEscaped "Starting receiver for ${subsystems[n]}..." >> ${subsystemLog}

            # Move to data directory
            dataLocation="${projectPath}/data"
            echoInfoEscaped "Moving to data directory: \"${dataLocation}\"" >> ${subsystemLog}
            cd "${dataLocation}"

            if [[ "${subsystems[n]}" == "HLT" ]];
            then
              monitorPort=25006
            else
              monitorPort=25005
            fi

            additionalOptions=""

            echoInfoEscaped "Receiver Settings:" >> ${subsystemLog}
            echoPropertiesEscaped "Subsystem: ${subsystems[n]}" >> ${subsystemLog}
            echoPropertiesEscaped "Receiver (interal) Port: ${internalReceiverPorts[n]}" >> ${subsystemLog}
            echoPropertiesEscaped "Use SSH tunnel: $useSSHTunnel" >> ${subsystemLog}
            echoPropertiesEscaped "Tunnel (external) Port: ${externalReceiverPorts[n]}" >> ${subsystemLog}
            echoPropertiesEscaped "SSH Monitor Port: $monitorPort" >> ${subsystemLog}
            echoPropertiesEscaped "Additional Options: $additionalOptions" >> ${subsystemLog}

            # TODO: update this to connect to HLT
            if [[ "${useSSHTunnel}" == true ]];
            then
              # Find SSH process
              sshProcesses=$(pgrep -f "autossh -M $monitorPort")
              echoInfoEscaped "autossh PID: $sshProcesses"

              # Determine if ssh tunnel is needed.
              # autossh should ensure that the connection never dies.
              if [[ -z "$sshProcesses" ]];
              then
                echoInfoEscaped "Did not find necessary ${subsystems[n]} autossh tunnel. Starting a new one!"
                autossh -M $monitorPort -f -N -L ${internalReceiverPorts[n]}:localhost:${externalReceiverPorts[n]} emcalguest@lbnl5core.cern.ch
              else
                echoInfoEscaped "${subsystems[n]} autossh tunnel already found with PID $sshProcesses. Not starting another one."
              fi
            else
              echoInfoEscaped "Not using a SSH tunnel!" >> ${subsystemLog}
            fi

            # select="" ensures that we get all histograms(?)
            receiverPath="${projectPath}/receiver/bin"
            nohup "${receiverPath}/zmqReceive" --in="REQ>tcp://localhost:${internalReceiverPorts[n]}" --verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${subsystems[n]}" ${additionalOptions} >> ${subsystemLog} 2>&1 &

            # Ensure that the output is still readable and that the receiver is able to start.
            sleep 1

            # Moving back to initOVERWATCH directory
            echoInfoEscaped "Moving back to deploy directory: \"$currentLocation\"" >> ${subsystemLog}
            cd "$currentLocation"

            echoInfoEscaped "Finished starting ${subsystems[n]} receiver!" >> ${subsystemLog}

          else
            echoInfoEscaped "No need to start new ${subsystems[n]} receiver." >> ${subsystemLog}
          fi

        done

        echo #EMPTY
        echoInfoEscaped "Done configuring receivers! All receivers are now running."
        echo #EMPTY

        #############################
        # Execute processing
        #############################

        if [[ "$calledFromSystemd" == true ]];
        then
          echoErrorEscaped "Processing should not be started from $1! Exiting"
          safeExit 1
          return $?
        fi

        # Check for lockout file
        # Determine current location of file
        # From: http://stackoverflow.com/a/246128
        currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

        # Only process if we are not locked out.
        # Locking out allows changes to processing (for example, reprocessing) without having to disable the crontab
        echoInfoEscaped "Checking for lockOut file."
        if [[ -e "${currentLocation}/lockOut" ]];
        then
            echoWarnEscaped "Processing locked out! Remove \"lockOut\" file to resume processing with this script! Exiting"
            safeExit 1
            return $?
        fi

        cd "$projectPath"
        # -b for batch mode (ie no graphics)
        echoInfoEscaped "Starting processing"
        python processRuns.py -b
    else
        echoErrorEscaped "Role $role not recognized. Exiting"
        safeExit 1
        return $?
    fi

fi
