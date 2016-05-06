#!/usr/bin/env bash

# To use with crontab, use line:
# * * * * * /home/rehlers/yaleDev/EMCalDev/qa/HLT/processFiles/startProcessRootFile.sh > /home/rehlers/yaleDev/EMCalDev/qa/HLT/processFiles/processRootFile.log 2>&1

# Determine current location of file
# From: http://stackoverflow.com/a/246128
currentLocation="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Only process if we are not locked out.
# Locking out allows changes to processing (for example, reprocessing) without having to disable the crontab
if [[ -e "${currentLocation}/lockOut" ]];
then
    echo "ATTENTION: Processing locked out! Remove \"lockOut\" file to resume processing with this script!"
    echo "Exiting..."
    exit 0
fi

#echo "$PWD"

# Load the alice environment
. /home/james/alice/alice-env.sh -n 1 -q

# http://stackoverflow.com/a/246128 
DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#echo "$DIR"
# Need to get out of the receiver/bin/ directory
cd $DIR/../..

#echo "$PWD"

# Start virtualenv
source .env/bin/activate

# Start the processing in batch mode
python processRuns.py -b
