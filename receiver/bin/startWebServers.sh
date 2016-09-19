#!/usr/bin/env bash

# To trap a control-c during the log
# See: http://rimuhosting.com/knowledgebase/linux/misc/trapping-ctrl-c-in-bash
trap ctrl_c INT

function ctrl_c() {
# Return to the cursor position saved in printStatus
echo -e "\nClosing web servers"
kill $histServerPID
kill $webServerPID
exit
}

if [[ "$HOSTNAME" == "lbnl3core" ]];
then
    # Load the alice environment
    echo "Loading ALICE software"
    . /home/james/alice/alice-env.sh -n 1 -q
fi

# Move to the directory with the web servers
cd ..

# Start the flask application
python webApp.py &

histServerPID=$!

# Start the python web server for most of the files
if [[ "$HOSTNAME" == "lbnl3core" ]];
then
    cd "/data1/emcalTriggerData"
else
    cd "data"
fi

# From: http://stackoverflow.com/a/12269225
echo "Starting web server"
python -c 'import BaseHTTPServer as bhs, SimpleHTTPServer as shs; bhs.HTTPServer(("127.0.0.1", 8850), shs.SimpleHTTPRequestHandler).serve_forever()' &

webServerPID=$!

while [[ true ]];
do
    sleep 1
done
