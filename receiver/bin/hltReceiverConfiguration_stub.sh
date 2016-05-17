# Contains the configuration files for the HLT receiver
aliceSoftwarePath=""
virtualEnvPath=".env/bin/activate"
buildType="aliBuild"
dataLocation=""
useSSHTunnel=false

# Values are paired together
subsystems=( "EMC" "HLT" )
# These are the port values that we pass to the receiver
internalReceiverPorts=( 11 12 )
# These are the port values at the other host
externalReceiverPorts=( 21 22 )

# Ensure the sizes of the variables above are the same!
# Otherwise, throw error and exti!
if [[ ${#subsystems[@]} -ne ${#internalReceiverPorts[@]} || ${#subsystems[@]} -ne ${#externalReceiverPorts[@]} ]];
then
    echo -e "\n\nERROR: Mismatch in configuration array sizes! Exiting!\n"
    exit -1
fi

##################
# Shared functions
##################
# Print functions are adapted from docker-machine-nfs
# The substantially increase readability

# @info:    Prints error messages
# @args:    error-message
echoError ()
{
  printf "\033[0;31mFAIL\n\n$1 \033[0m\n"
}

# @info:    Prints warning messages
# @args:    warning-message
echoWarn ()
{
  printf "\033[0;33m$1 \033[0m\n"
}

# @info:    Prints success messages
# @args:    success-message
echoSuccess ()
{
  printf "\033[0;32m$1 \033[0m\n"
}

# @info:    Prints check messages
# @args:    success-message
echoInfo ()
{
  printf "\033[1;34m[INFO] \033[0m$1\n"
}

# @info:    Prints property messages
# @args:    property-message
echoProperties ()
{
  printf "\t\033[0;35m- %s \033[0m\n" "$@"
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoInfoEscaped ()
{
    # See: https://stackoverflow.com/a/911224
    if [[ -t 1 ]];
    then
        # Running interactively in a terminal
        echoInfo "$1"
    else
        # Logging to file
        echo "INFO: $1"
    fi
}
# @info:    Avoid printing color codes when logging to file
# @args:    message
echoWarnEscaped ()
{
    # See: https://stackoverflow.com/a/911224
    if [[ -t 1 ]];
    then
        # Running interactively in a terminal
        echoWarn "$1"
    else
        # Logging to file
        echo "WARNING: $1"
    fi
}
# @info:    Avoid printing color codes when logging to file
# @args:    message
echoPropertiesEscaped ()
{
    # See: https://stackoverflow.com/a/911224
    if [[ -t 1 ]];
    then
        # Running interactively in a terminal
        echoProperties "$1"
    else
        # Logging to file
        echo -e "\t$1"
    fi
}
