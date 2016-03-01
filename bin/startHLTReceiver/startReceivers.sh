#!/usr/bin/env bash

# To trap a control-c during the log
# See: http://rimuhosting.com/knowledgebase/linux/misc/trapping-ctrl-c-in-bash
trap ctrl_c INT

function ctrl_c() {
# Return to the cursor position saved in printStatus
echo "Closing HLT receivers"
kill $emcReceiver
kill $hltReceiver
exit
}

echo $PWD

# EMC receiver
#./runREQ.sh $internalPort $externalPort $receiverType
./runREQ.sh 40321 60321 "EMC" &
emcReceiver=$!

# Ensure that the output is still readable and that the EMC is able to start.
sleep 1

# HLT receiver
#./runREQ.sh $internalPort $externalPort $receiverType
./runREQ.sh 40322 60322 "HLT" &
hltReceiver=$!

while [[ true ]];
do
    sleep 1
done
