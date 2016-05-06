# Contains the configuration files for the HLT receiver

aliceSoftwarePath=""
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
    echo "Mismatch in configuration array sizes! Exiting!"
    exit -1
fi
