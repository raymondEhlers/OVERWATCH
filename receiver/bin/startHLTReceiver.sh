#!/usr/bin/env bash

# To trap a control-c during the log
# See: http://rimuhosting.com/knowledgebase/linux/misc/trapping-ctrl-c-in-bash
trap ctrl_c INT

function ctrl_c() {
# Return to the cursor position saved in printStatus
echo "Closing HLT receivers"
kill -INT $emcReceiver
kill -INT $hltReceiver
#echo $emcReceiver
#echo $hltReceiver
exit
}

echo $PWD

# EMC receiver
#./runReceiver.sh $internalPort $externalPort $receiverType
./runReceiver.sh 60321 60321 "EMC" &
#./runReceiver.sh 40321 60321 "EMC" &
emcReceiver=$!
echo "emcPID: $emcReceiver"

# Ensure that the output is still readable and that the EMC is able to start.
sleep 1

# HLT receiver
#./runReceiver.sh $internalPort $externalPort $receiverType
./runReceiver.sh 60322 60322 "HLT" &
#./runReceiver.sh 40322 60322 "HLT" &
hltReceiver=$!
echo "hltPID: $hltReceiver"

while [[ true ]];
do
    sleep 1
done
