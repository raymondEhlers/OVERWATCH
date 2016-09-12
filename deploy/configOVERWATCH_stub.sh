# Configuration file for the HLT receiver

# Option to kill any existing receivers, and start new receivers
forceRestart=false

# Using SSH tunnel
useSSHTunnel=false

# Values are paired together
subsystems=( "EMC" "TPC" "HLT" )
# These are the port values that we pass to the receiver
internalReceiverPorts=( 11 12 13)
# These are the port values at the other host
externalReceiverPorts=( 21 22 23)

# Ensure the sizes of the variables above are the same!
# Otherwise, throw error and exti!
if [[ ${#subsystems[@]} -ne ${#internalReceiverPorts[@]} || ${#subsystems[@]} -ne ${#externalReceiverPorts[@]} ]];
then
    echo -e "\n\nERROR: Mismatch in configuration array sizes! Exiting!\n"
    exit -1
fi

# Determine config variables, based on which machine we are running on

projectPath=""
softwarePath=""
virtualEnvPath=""
location=""
buildType=""
# If alibuild is used, must specify name
alibuildName="latest-aliMaster"
role=""

if [[ "${docker}" == true ]];
then
    projectPath="/overwatch"
    softwarePath="/alice/sw"
    virtualEnvPath=""
    location="docker"
    buildType="aliBuild"
    role="server"

    # Additional settings
    # None!

# Add additional systems here!
else
    echoErrorEscaped "Cannot run on hostname $HOSTNAME. You need to define the necessary variables."
    safeExit 1
    return $?
fi
