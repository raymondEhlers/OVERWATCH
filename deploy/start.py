#!/usr/bin/env python

from __future__ import print_function

import os
import signal
import logging
import argparse
import subprocess
import sys
import time
import yaml

logger = logging.getLogger("")

# Convenience
import pprint

def checkForProcessPID(processIdentifier):
    """ Check for a process by a process identifier string via pgrep.

    Args:
        processIdentifier(str): String passed to pgrep to identify the process.
    Returns:
        list: PID(s) from pgrep
        """
    try:
        res = subprocess.check_output(["pgrep", "-f", "{0}".format(processIdentifier)])
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            logger.info("Process identifier \"{0}\" not found".format(processIdentifier))
            return None
        else:
            logger.critical("Unknown return code of \"{0}\" for command \"{1}\", with output \"{2}".format(e.returncode, e.cmd, e.output))
            sys.exit(e.returncode)
    # Convert from bytes to string when returning
    # Each entry is on a new line (and we must check for empty lines)
    pids = res.decode("utf-8").split("\n")
    pids = [int(pid) for pid in pids if pid != ""]
    if len(pids) > 1:
        logger.warning("Multiple PIDs associated with this receiver!")
    return pids
    # sshProcesses=$(pgrep -f "autossh -L ${internalReceiverPorts[n]}")

def killExistingProcess(pidList, processType, processIdentifier, sig = signal.SIGINT):
    """ Kill processes by PID. The kill signal will be sent to the entire process group.

    Args:
        pidList (list): List of PIDs to be killed.
        processType (str): Name of the processes being killed.
        processIdentifier (str): String used to identify the processes that are being killed.
        sig (int): Signal to be sent to the processes. Default: signal.SIGINT
    Returns:
        list: PID(s) left after killing the processes. Note that any list which is not None will throw a fatal error
    """
    logger.debug("Killing existing {0} processes with PID(s) {1}".format(processType, pidList))
    for pid in pidList:
        # TODO: Check if -1 is needed (I think killpg handles sending the signal to the entire process group)
        logger.debug("Killing process {0}".format(pid))
        # TODO: killpg doesn't work. It claims that the process doesn't exist. Investigate this further...
        os.kill(pid, sig)

    # Check that killing the process was successful
    # If not, throw an error
    pidList = checkForProcessPID(processIdentifier)
    logger.debug("PIDs left after killing processes: {0}".format(pidList))
    if not pidList is None:
        logger.critical("Requested to kill existing \"{0}\" processes, but found PIDs {0} after killing the processes. Please investigate!", processType, pidList)
        sys.exit(2)

    return pidList

def startProcessWithLog(args, name, logFilename):
    with open(logFilename, "wb") as logFile:
        logger.debug("Starting \"{0}\" with args: {1}".format(name, args))
        process = subprocess.Popen(args, stdout=logFile, stderr=subprocess.STDOUT)

    return process

def tunnel(config, receiverConfig):
    """ Start tunnel """
    processExists = checkForProcessPID("autossh -L {0}".format(receiverConfig["localPort"]))

    if config["forceRestart"] or receiverConfig["forceRestartTunnel"]:
        processPIDs = killExistingProcess(processPIDs,
                                          processType = "{0} Receiver".format(receiver),
                                          processIdentifier = "autossh -L {0}".format(receiverConfig["localPort"]))
        # processPIDs will be None if the processes were killed successfully

    if processExists is None:
        # Create ssh tunnel
        # TODO: Check order of args on VM
        args = [
                "autossh",
                "-L ${localPort}:localhost:${hltPort}".format(localPort = receiverConfig["localPort"],
                                                              hltPort = receiverConfig["hltPort"]),
                "-o ServerAliveInterval 30", # Built-in ssh monitoring option
                "-o ServerAliveCountMax 3",  # Built in ssh monitoring
                "-p {0}".format(config["port"]),
                "-l {0}".format(config["username"]),
                "{0}".format(config["address"]),
                "-M 0",                      # Disable autossh built-in monitoring
                "-f",
                "-N"
                ]
        # Official: autossh -M ${monitorPorts[n]} -o ServerAliveInterval 30 -o ServerAliveCountMax 3 -p ${sshPorts[n]} -f -N -l zmq-tunnel  -L ${internalReceiverPorts[n]}:localhost:${externalReceiverPorts[n]} ${sshServerAddress}

def receiver(config):
    """ Start receivers """
    # Add receiver to path
    receiverPath = config["receiver"].get("receiverPath", "/opt/receiver")
    receiverPath = os.path.expandvars(receiverPath)
    logger.debug("Adding receiver path \"{0}\" to PATH".format(receiverPath))
    os.environ["PATH"] += os.pathsep + receiverPath

    for receiver, receiverConfig in config["receiver"].items():
        if len(receiver) != 3:
            #logger.debug("Skipping entry \"{0}\" in the receiver config, as it it doesn't correspond to a detector".format(receiver))
            continue

        logger.debug("receiver name: {0}, config: {1}".format(receiver, receiverConfig))

        # Ensure that the detector name is upper case
        receiver = receiver.upper()
        processIdentifier = "zmqReceive --subsystem={0}".format(receiver)

        # Start tunnel if requested
        if receiverConfig["tunnel"]:
            tunnel(config = config["tunnel"], receiverConfig = receiverConfig)

        processPIDs = checkForProcessPID(processIdentifier)
        logger.debug("Found processPIDs: {0}".format(processPIDs))

        # Check whether we should kill the receivers
        if not processPIDs is None and (config["receiver"].get("forceRestart", None) or receiverConfig.get("forceRestart", None)):
            logger.debug("Found processPIDs: {0}".format(processPIDs))
            processPIDs = killExistingProcess(processPIDs,
                                              processType = "{0} Receiver".format(receiver),
                                              processIdentifier = processIdentifier)
            # processPIDs will be None if the processes were killed successfully

        if processPIDs is None:
            # Start receiver
            args = [
                    "zmqReceive",
                    "--subsystem={0}".format(receiver),
                    "--in=REQ>tcp://localhost:{0}".format(receiverConfig["localPort"]),
                    "--verbose=1",
                    "--sleep=60",
                    "--timeout=100",
                    "--select={0}".format(receiverConfig.get("select",""))
                    ]
            if "additionalOptions" in receiverConfig:
                args.append(receiverConfig["additionalOptions"])
            process = startProcessWithLog(args = args, name = "Receiver", logFilename = "{0}Receiver.log".format(receiver))
            #--verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${subsystems[n]}" ${additionalOptions}

            # From official script:
            # zmqReceive --in=REQ>tcp://localhost:60323 --verbose=1 --sleep=60 --timeout=100 --select= --subsystem=TPC
            # From this script:
            # zmqReceive --subsystem=EMC --in=REQ>tcp://localhost:60321 --verbose=1 --sleep=60 --timeout=100 --select=
            #
            # --> Don't need to escape most quotes!

            # Check for receiver to ensure that it didn't just die immediately due to bad arguments, etc.

            logger.info("Check that the process launched successfully...")
            time.sleep(1.5)
            processPIDs = checkForProcessPID(processIdentifier)
            if processPIDs is None:
                logger.critical("No process found corresponding to the just launched receiver! Check the log files!")
                sys.exit(2)
            else:
                logger.info("Success!")
        else:
            logger.info("Skipping receiver \"{0}\" since it already exists!".format(receiver))

def database(config):
    """ Start the database on it's own. """
    zeoConfigFile = """
<zeo>
    address {ipAddress}:{port}
</zeo>

<filestorage>
    path {databasePath}
</filestorage>

<eventlog>
    <logfile>
        path {logFile}
        format {logFormat}
    </logfile>
</eventlog>
    """.format(ipAddress = config["ipAddress"],
               port = config["port"],
               databasePath = config["databasePath"],
               logFile = config["logFile"],
               logFormat = config.get("logFormat", "%(asctime)s %(message)s")
               )

    # Write config
    with open("zeoGenerated.conf", "wb") as f:
        f.write(zeoConfigFile)

    # Start zeo with the config file
    processPIDs = checkForProcessPID("runzeo -C zeoGenerated.conf".format(receiver))
    logger.debug("processPIDs: {0}".format(processPIDs))

    if processPIDs is None:
        # Start database
        pass

def processing(config):
    """ Start processing. """
    # Write out config options as necessary
    # TODO: Transition configuration files!

    # Start the processing
    args = [
            "python",
            "../runProcessRuns.py",
            "-b",   # Run in batch processing mode to suppress ROOT graphics
            ]

    process = startProcessWithLog(args = args, name = "Process Runs", logFilename = "processRuns.log")

def webApp(config):
    """ Start web app. """
    # Handle both renning locally for development, as well as starting uwsgi when required
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

    logger.info("Config:")
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
    parser.add_argument("-l", "--logLevel", metavar="level",
                        type=str, default="DEBUG",
                        help="Set the log leve.")

    # Parse arguments
    args = parser.parse_args()

    # Setup logger
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    # Set log level
    level = args.logLevel.upper()
    logger.setLevel(level)

    startOverwatch(args.config)
