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

if [[ $HOSTNAME == *"pdsf"* || $HOSTNAME == *"sgn"* ]];
then
    # Define necessary variables
    projectPath="/project/projectdirs/alice/aliprodweb/overwatch"
    softwarePath="/project/projectdirs/alice/aliprodweb/ROOT/"
    virtualEnvPath="/project/projectdirs/alice/aliprodweb/virtualenv/python_2_7_11/bin/activate"
    location="PDSF"
    buildType="root"
    role="server"

    # Additional settings
    # Sets the library path for both python and libffi
    export LD_LIBRARY_PATH="/project/projectdirs/alice/aliprodweb/python_bin/v2.7.11/lib:/project/projectdirs/alice/aliprodweb/essentials/install/lib64:$LD_LIBRARY_PATH"
elif [[ $(hostname -f) == *"aliceoverwatch"* && $(hostname -f) == *"yale"* ]];
then
    # Define necessary variables
    projectPath="/opt/www/aliceoverwatch"
    softwarePath="/opt/aliceSW/root/alice_v5-34-30/inst/"
    virtualEnvPath="/opt/www/aliceoverwatch/.env/bin/activate"
    location="Yale"
    buildType="root"
    role="server"

    # Additional settings
    # None!
elif [[ $(hostname -f) == *"aliceoverwatch"* && $(hostname -f) == *"cern"* ]];
then
    # Define necessary variables
    projectPath="/home/emcal/overwatch"
    softwarePath="/home/emcal/alice/sw"
    virtualEnvPath="/home/emcal/overwatch/.env/bin/activate"
    location="overwatchCERN"
    buildType="aliBuild"
    role="processing"

    # Additional settings
    # None!
elif [[ "${docker}" == true ]];
then
    projectPath="/overwatch"
    softwarePath="/alice/sw"
    virtualEnvPath=""
    location="docker"
    buildType="aliBuild"
    role="server"

    # Additional settings
    # None!
elif [[ $(hostname -f) == *"ray-MBP"* ]];
then
    # TEMP!
    projectPath="$HOME/code/alice/overwatch"
    softwarePath="$HOME/alice/sw"
    virtualEnvPath="$projectPath/.env/bin/activate"
    location="ray-MBP"
    buildType="aliBuild"
    role="processing"

else
    echoErrorEscaped "Cannot run on hostname $HOSTNAME. You need to define the necessary variables."
    safeExit 1
    return $?
fi
