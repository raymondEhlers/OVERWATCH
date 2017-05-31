#!/usr/bin/env python

from __future__ import print_function

import argparse
import subprocess
import sys

import yaml

# Convenience
import pprint

def checkForProcessPID(processIdentifier):
    """ Check for a process by a process identifier string via pgrep.

    Args:
        processIdentifier(str): String passed to pgrep to identify the process.
    Returns:
        int: PID from pgrep
        """
    try:
        res = subprocess.check_output(["pgrep", "-f", "{0}".format(processIdentifier)])
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("Process identifier \"{0}\" not found! It will be created.".format(processIdentifier))
            return None
        else:
            print("Unknown return code of \"{0}\" for command \"{1}\", with output \"{2}".format(e.returncode, e.cmd, e.output))
            sys.exit(e.returncode)
    # Convert from bytes to string when returning
    # Each entry is on a new line (and we must check for empty lines)
    pids = res.decode("utf-8").split("\n")
    pids = [int(pid) for pid in pids if pid != ""]
    if len(pids) > 1:
        print("WARNING: Multiple PIDs associated with this receiver!")
    return pids
    # sshProcesses=$(pgrep -f "autossh -L ${internalReceiverPorts[n]}")

def tunnel(config):
    """ Start tunnel """
    processExists = checkForProcessPID("autossh -L {0}".format(config["localPort"]))

    if processExists is None:
        # Create ssh tunnel
        pass

def receiver(config):
    """ Start receivers """
    for receiver, receiverConfig in config["receiver"].items():
        print("receiver name: {0}, config: {1}".format(receiver, receiverConfig))
        if len(receiver) != 3:
            print("Skipping entry \"{0}\" in the receiver config, as it it doesn't correspond to a detector".format(receiver))
            continue
        # Ensure that the detector name is upper case
        receiver = receiver.upper()

        processExists = checkForProcessPID("/Users/re239/code/alice/overwatch/receiver/bin/zmqReceive --subsystem={0}".format(receiver))
        print("processExists: {0}".format(processExists))

        # Check whether we should kill the receivers

        if processExists is None:
            # Start reciever
            args = [
                    "/Users/re239/code/alice/overwatch/receiver/bin/zmqReceive",
                    "--subsystem={0}".format(receiver),
                    "--in=REQ>tcp://localhost:{0}".format(receiverConfig["localPort"]),
                    "--verbose=1",
                    "--sleep=60",
                    "--timeout=100",
                    "--select={0}".format(receiverConfig.get("select",""))
                    ]
            if "additionalOptions" in config:
                args = args + config["additionalOptions"]
            with open("{0}ReceiverTest.log".format(receiver), "wb") as logFile:
                print("Starting receiver with args: {0}".format(args))
                process = subprocess.Popen(args, stdout=logFile, stderr=subprocess.STDOUT)
                #--verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${subsystems[n]}" ${additionalOptions}

                # From official script:
                # zmqReceive --in=REQ>tcp://localhost:60323 --verbose=1 --sleep=60 --timeout=100 --select= --subsystem=TPC
                # From this script:
                # zmqReceive --subsystem=EMC --in=REQ>tcp://localhost:60321 --verbose=1 --sleep=60 --timeout=100 --select=
                #
                # --> Don't need to escape most quotes!
        else:
            print("Skipping receiver \"{0}\" since it already exists!".format(receiver))

def processing(config):
    """ Start processing. """
    pass

def webApp(config):
    """ Start web app. """
    pass

def webAppSetup(config):
    """ Setup web app, such as installing bower components, polymerizer, minify, etc.
    
    Maybe this can all be handled by WebAssets?? """
    pass

def startOverwatch(filename):
    """ Start the various parts of Overwatch.
    
    Components are only started if they are included in the configuration. """
    # Define config
    with open(filename, "rb") as f:
        config = yaml.load(f)

    print("Config:")
    pprint.pprint(config)

    if "receiver" in config and config["receiver"]["enabled"]:
        # Start the tunnel(s) if necessary
        #if "tunnel" in config:
        #    tunnel(config["reciever"])

        # Start the receiver(s)
        receiver(config)

    if "processing" in config and config["processing"]["enabled"]:
        processing(config)

    if "webApp" in config and config["processing"]["enabled"]:
        if "setup" in config["webApp"]:
            webAppSetup(config)
        webApp(config)

if __name__ == "__main__":
    # Setup command line parser
    parser = argparse.ArgumentParser(description = "Start Overwatch")
    parser.add_argument("-c", "--config", metavar="configFile",
                        type=str, default="deployConfig.yaml",
                        help="Path to config filename")

    # Parse arguments
    args = parser.parse_args()

    startOverwatch(args.config)
