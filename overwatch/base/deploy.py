#!/usr/bin/env python

from __future__ import print_function

import os
import stat
import signal
import logging
import argparse
import subprocess
import sys
import time
import ruamel.yaml as yaml
import collections

logger = logging.getLogger("")

# Convenience
import pprint

# Utility function to handle expanding environmental variables from YAML
def expandEnvironmentalVars(loader, node):
    val = loader.construct_scalar(node)
    # Need to strip "\n" due to it being inserted when variables are expanded
    val = os.path.expandvars(val).replace("\n", "")
    return str(val)

yaml.SafeLoader.add_constructor('!expandVars', expandEnvironmentalVars)

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

def startProcessWithLog(args, name, logFilename, supervisord = False, shortExecutionTime = False):
    if supervisord:
        process = """
[program:{name}]
command={command}
redirect_stderr=true
# 5 MB log file with 10 backup files
stdout_logfile_maxbytes=500000
stdout_logfile_backups=10"""

        if shortExecutionTime:
            process += """
autorestart=false
startsecs=0
"""
        else:
            process += "\n"

        # Using logFilename to ensure that the name is more descriptive
        process = process.format(name = logFilename,
                                 command = " ".join(args))
        # Write the particular config
        with open("supervisord.conf", "ab") as f:
            f.write(process)
        # process is not meaningful here, so it won't be launched until the end
        process = None
    else:
        with open("{0}.log".format(logFilename), "wb") as logFile:
            logger.debug("Starting \"{0}\" with args: {1}".format(name, args))
            process = subprocess.Popen(args, stdout=logFile, stderr=subprocess.STDOUT)

    return process

def tunnel(config, receiver, receiverConfig, supervisord):
    """ Start tunnel """
    processIdentifier = "autossh -L {0}".format(receiverConfig["localPort"])
    processExists = checkForProcessPID(processIdentifier)

    if config.get("forceRestart", False) or receiverConfig.get("forceRestartTunnel", False):
        processPIDs = killExistingProcess(processPIDs,
                                          processType = "{0} SSH Tunnel".format(receiver),
                                          processIdentifier = processIdentifier)
        # processPIDs will be None if the processes were killed successfully

    # Ensure that the known_hosts file is populated if it wasn't already
    knownHostsPath = os.path.expandvars(os.path.join("$HOME", ".ssh", "known_hosts")).replace("\n", "")
    logger.debug("Checking for known_hosts file at {}".format(knownHostsPath))
    if not os.path.exists(knownHostsPath):
        if not os.path.exists(os.path.dirname(knownHostsPath)):
            os.makedirs(os.path.dirname(knownHostsPath))
            # Set the proper permissions
            os.chmod(os.path.dirname(knownHostsPath), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        # ssh-keyscan -H {address}
        args = ["ssh-keyscan",
                "-p {0}".format(config["port"]),
                "-H",
                config["address"]
                ]
        with open(knownHostsPath, "wb") as logFile:
            logger.debug("Starting \"{0}\" with args: {1}".format("SSH Keyscan", args))
            process = subprocess.Popen(args, stdout=logFile)

    if processExists is None:
        # Create ssh tunnel
        args = [
                "autossh",
                "-L {localPort}:localhost:{hltPort}".format(localPort = receiverConfig["localPort"],
                                                              hltPort = receiverConfig["hltPort"]),
                "-o ServerAliveInterval=30", # Built-in ssh monitoring option
                "-o ServerAliveCountMax=3",  # Built-in ssh monitoring option
                "-p {0}".format(config["port"]),
                "-l {0}".format(config["username"]),
                "{0}".format(config["address"]),
                "-M 0",                      # Disable autossh built-in monitoring
                "-f",
                "-N"
                ]
        # Official: autossh -o ServerAliveInterval 30 -o ServerAliveCountMax 3 -p ${sshPorts[n]} -f -N -l zmq-tunnel  -L ${internalReceiverPorts[n]}:localhost:${externalReceiverPorts[n]} ${sshServerAddress}
        process = startProcessWithLog(args = args, name = "{0} SSH Tunnel".format(receiver), logFilename = "{}sshTunnel".format(receiver), supervisord = supervisord, shortExecutionTime = True)
        # We don't want to check the process status, since autossh will go to the background immediately

def writeSensitiveVariableToFile(config, name, prettyName, defaultWriteLocation):
    """ Write SSH key or certificate from environment variable to file. """
    # Check name value (also acts as proxy for the other values)
    if name != "sshKey" and name != "cert":
        raise ValueError("Name \"{}\" is unrecognized! Aborting")

    #sensitiveVariable = getSensitiveVariableConfigurationValues(config, name = name, prettyName = prettyName)
    logger.info("Writing {} from environment variable to file".format(prettyName))
    # Get variable from environment
    variableName = config[name].get("variableName", name)
    sensitiveVariable = os.environ[variableName]
    # Check that the variable is not empty
    if not sensitiveVariable:
        raise ValueError("Empty {} passed".format(prettyName))
    print("variableName: {}, {}: {}".format(variableName, prettyName, sensitiveVariable))

    # Write to file
    writeLocation = config[name].get("writeLocation", defaultWriteLocation)
    # Expand filename
    writeLocation = os.path.expanduser(os.path.expandvars(writeLocation))
    if not os.path.exists(os.path.dirname(writeLocation)):
        os.makedirs(os.path.dirname(writeLocation))

    # Ensure that we don't overwrite an existing file!
    if os.path.exists(writeLocation):
        raise IOError("File at {0} already exists and will not be overwritten!".format(writeLocation))
    with open(writeLocation, "wb") as f:
        f.write(sensitiveVariable)

    if name == "sshKey":
        # Set the file permissions to 600
        os.chmod(writeLocation, stat.S_IRUSR | stat.S_IWUSR)
        # Set the folder permissions to 700
        os.chmod(os.path.dirname(writeLocation), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    elif name == "cert":
        # Set the file permissions to 400
        os.chmod(writeLocation, stat.S_IRUSR)

def setupSupervisord(config):
    # Write to the supervisord config
    filename = "supervisord.conf"
    if not os.path.exists(filename):
        logger.info("Creating supervisord main config")
        # Write the main config
        # TODO: Automatically determine the logfile and childlodir paths so that it works anywhere
        mainConfig = """
[supervisord]
nodaemon=true
# Use the overwatch data directory
logfile=/opt/overwatch/data/supervisord.log
childlogdir=/opt/overwatch/data/
# 5 MB log file with 10 backup files
logfile_maxbytes=5000000
logfile_backups=10

[unix_http_server]
# (the path to the socket file)
file=/tmp/supervisor.sock
# socket file mode (default 0700)
chmod=0700

# the below section must remain in the config file for RPC
# (supervisorctl/web interface) to work, additional interfaces may be
# added by defining them in separate rpcinterface: sections
[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
# Use a unix:// URL  for a unix socket
serverurl = unix:///tmp/supervisor.sock
"""
        with open(filename, "wb+") as f:
            f.write(mainConfig)
    else:
        logger.info("Supervisord config already exists - skipping creation.")

def setupRoot(config):
    rootConfig = config["env"]["root"]

    if rootConfig["script"] and rootConfig["enabled"]:
        thisRootPath = os.path.join(rootConfig["script"], "bin", "thisroot.sh")
        # Run thisroot.sh, extract the environment, and then set the python environment to those values
        # See: https://stackoverflow.com/a/3505826
        command = ["bash", "-c", "source {}  && env".format(thisRootPath)]

        proc = subprocess.Popen(command, stdout = subprocess.PIPE)

        # Load into the environment
        # Note that this doesn't propagate to the shell where this was executed!
        for line in proc.stdout:
            (key, _, value) = line.partition("=")
            os.environ[key] = value

def setupEnv(config):
    if "root" in config["env"] and config["env"]["root"]["enabled"]:
        setupRoot(config)
        print(os.environ)

def dqmReceiver(config, receiver, receiverConfig):
    """ Start the DQM receiver """
    # Write out custom config
    writeCustomConfig(receiverConfig)

    if "uwsgi" in receiverConfig and receiverConfig["uwsgi"]["enabled"]:
        configFilename = "{0}Receiver.yaml".format(receiver.lower())
        processIdentifier = "uwsgi --yaml {configFile}".format(configFile = configFilename)

        # Handle nginx setup.
        # We would only want to start nginx if we are using uwsgi
        if "webServer" in receiverConfig and receiverConfig["webServer"]:
            # Configure nginx
            nginx(config, name = "dqmReceiver")

            # Start nginx
            startNginx(name = "nginx", logFilename = "nginx", supervisord = "supervisord" in config)

        # Write the uwsgi configuration
        uwsgi(config = config["receiver"], name = "DQM")

        args = [
                "uwsgi",
                "--yaml",
                configFilename
                ]
    else:
        processIdentifier = "overwatchDQMReciever"

        args = [
                "overwatchDQMReciever",
                ]

    processPIDs = checkForProcessPID(processIdentifier)

    # NOTE: This won't work properly with uwsgi!
    if not processPIDs is None and (config["receiver"].get("forceRestart", None) or receiverConfig.get("forceRestart", None)):
        logger.debug("Found processPIDs: {0}".format(processPIDs))
        processPIDs = killExistingProcess(processPIDs,
                                          processType = "{0} Receiver".format(receiver),
                                          processIdentifier = processIdentifier)
        # processPIDs will be None if the processes were killed successfully

    if not config["avoidNohup"]:
        # Only append "nohup" if it is _NOT_ called from systemd or supervisord
        args = ["nohup"] + args

    process = startProcessWithLog(args, name = "dqmReceiver", logFilename = "dqmReceiver", supervisord = "supervisord" in config)

    if process:
        logger.info("Check that the process launched successfully...")
        time.sleep(1.5)
        processPIDs = checkForProcessPID(processIdentifier)
        if processPIDs is None:
            logger.critical("No process found corresponding to the just launched receiver! Check the log files!")
            sys.exit(2)
        else:
            logger.info("Success!")

def zmqReceiver(config, receiver, receiverConfig, receiverPath):
    processIdentifier = "zmqReceive --subsystem={0}".format(receiver)

    # Start tunnel if requested
    if receiverConfig["tunnel"]:
        tunnel(config = config["tunnel"], receiver = receiver, receiverConfig = receiverConfig, supervisord = "supervisord" in config)

    processPIDs = checkForProcessPID(processIdentifier)
    #logger.debug("Found processPIDs: {0}".format(processPIDs))

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
                os.path.join(receiverPath, "zmqReceive"),
                "--subsystem={0}".format(receiver),
                "--in=REQ>tcp://localhost:{0}".format(receiverConfig["localPort"]),
                "--dataPath={0}".format(config["receiver"].get("dataPath", "data")),
                "--verbose=1",
                "--sleep=60",
                "--timeout=100",
                "--select={0}".format(receiverConfig.get("select",""))
                ]
        if "additionalOptions" in receiverConfig:
            args.append(receiverConfig["additionalOptions"])
        process = startProcessWithLog(args = args, name = "Receiver", logFilename = "{0}Receiver".format(receiver), supervisord = "supervisord" in config)
        #--verbose=1 --sleep=60 --timeout=100 --select="" --subsystem="${subsystems[n]}" ${additionalOptions}

        # From official script:
        # zmqReceive --in=REQ>tcp://localhost:60323 --verbose=1 --sleep=60 --timeout=100 --select= --subsystem=TPC
        # From this script:
        # zmqReceive --subsystem=EMC --in=REQ>tcp://localhost:60321 --verbose=1 --sleep=60 --timeout=100 --select=
        #
        # --> Don't need to escape most quotes!

        # Check for receiver to ensure that it didn't just die immediately due to bad arguments, etc.

        if process:
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

def receiver(config):
    """ Start receivers """
    # Add receiver to path
    # We also launch the executable with the path to be certain that it launches properly
    receiverPath = config["receiver"].get("receiverPath", "/opt/receiver/bin")
    # Need to strip "\n" due to it being inserted when variables are expanded
    receiverPath = os.path.expandvars(receiverPath).replace("\n", "")
    logger.debug("Adding receiver path \"{0}\" to PATH".format(receiverPath))
    # Also remove "\n" at the end of the path variable for clarity
    os.environ["PATH"] = os.environ["PATH"].rstrip() + os.pathsep + receiverPath

    for receiver, receiverConfig in config["receiver"].items():
        # Only use iterable collections (which should correspond to a particular receiver config)
        if not isinstance(receiver, collections.Iterable):
            #logger.debug("Skipping entry \"{0}\" in the receiver config, as it it doesn't correspond to a iterable detector configuration".format(receiver))
            continue
        # Backup check, but could be ignored in the future
        if len(receiver) != 3:
            #logger.debug("Skipping entry \"{0}\" in the receiver config, as it it doesn't correspond to a detector".format(receiver))
            continue

        logger.debug("receiver name: {0}, config: {1}".format(receiver, receiverConfig))

        # Ensure that the detector name is upper case
        receiver = receiver.upper()

        if receiver == "DQM":
            dqmReceiver(config = config, receiver = receiver, receiverConfig = receiverConfig)
        else:
            zmqReceiver(config = config, receiver = receiver, receiverConfig = receiverConfig, receiverPath = receiverPath)

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

    # Only start if not already running
    if processPIDs is None:
        # Start database
        args = [
                "runzeo",
                "-C zeoGenerated.conf"
                ]

        if not config["avoidNohup"]:
            # Only append "nohup" if it is _NOT_ called from systemd or supervisord
            args = ["nohup"] + args

        process = startProcessWithLog(args = args, name = "ZODB", logFilename = "ZODB")

        if process:
            logger.info("Check that the process launched successfully...")
            time.sleep(1.5)
            processPIDs = checkForProcessPID(processIdentifier)
            if processPIDs is None:
                logger.critical("No process found corresponding to the just launched ZODB database! Check the log files!")
                sys.exit(2)
            else:
                logger.info("Success!")

def writeCustomConfig(config, filename = "config.yaml"):
    if "customConfig" in config:
        if os.path.exists(filename):
            # Append if it already exists
            mode = "ab"
        else:
            mode = "wb"

        # Write out configuration
        with open(filename, mode) as f:
            yaml.dump(config["customConfig"], f, default_flow_style = False)

def processing(config):
    """ Start processing. """
    # Write out custom configuration
    writeCustomConfig(config["processing"])

    # Start the processing
    # Use the installed executable
    args = [
            "overwatchProcessing"
            ]

    if not config["avoidNohup"]:
        # Only append "nohup" if it is _NOT_ called from systemd or supervisord
        args = ["nohup"] + args

    process = startProcessWithLog(args = args, name = "Processing", logFilename = "processing")

    if process:
        logger.info("Check that the process launched successfully...")
        time.sleep(1.5)
        processPIDs = checkForProcessPID(processIdentifier)
        if processPIDs is None:
            logger.critical("No process found corresponding to the just launched processing! Check the log files!")
            sys.exit(2)
        else:
            logger.info("Success!")

def webApp(config):
    """ Setup and start web app.

    Handles running both locally for development, as well as starting uwsgi when required
    """
    webAppConfig = config["webApp"]

    # Write out custom configuration
    writeCustomConfig(config["webApp"])

    # Run webApp setup if necessary
    if "webAppSetup" in webAppConfig and webAppConfig["webAppSetup"]:
        webAppSetup(config)

    if "uwsgi" in webAppConfig and webAppConfig["uwsgi"]["enabled"]:
        configFilename = "{0}".format(webAppConfig.get("wsgiConfigFilename", "webApp.yaml"))
        processIdentifier = "uwsgi --yaml {0}".format(configFilename)

        # Handle nginx setup.
        # We would only want to start nginx if we are using uwsgi
        if "webServer" in webAppConfig and webAppConfig["webServer"]:
            # Configure nginx
            nginx(config, name = "webApp")

            # Start nginx
            startNginx(name = "nginx", logFilename = "nginx", supervisord = "supervisord" in config)

        # Configure uwsgi
        uwsgi(config, name = "webApp")

        args = [
                "uwsgi",
                "--yaml",
                configFilename
                ]
    else:
        # Use flask development server instead
        # Do not use in production!!
        processIdentifier = "overwatchWebApp"

        # Use the installed executable
        args = [
                "overwatchWebApp"
                ]

    processPIDs = checkForProcessPID(processIdentifier)

    # NOTE: This won't work properly with uwsgi!
    if not processPIDs is None and (config["receiver"].get("forceRestart", None) or receiverConfig.get("forceRestart", None)):
        logger.debug("Found processPIDs: {0}".format(processPIDs))
        processPIDs = killExistingProcess(processPIDs,
                                          processType = "{0} Receiver".format(receiver),
                                          processIdentifier = processIdentifier)
        # processPIDs will be None if the processes were killed successfully

    if not config["avoidNohup"]:
        # Only append "nohup" if it is _NOT_ called from systemd or supervisord
        args = ["nohup"] + args

    process = startProcessWithLog(args, name = "webApp", logFilename = "webApp", supervisord = "supervisord" in config)

    if process:
        logger.info("Check that the process launched successfully...")
        time.sleep(1.5)
        processPIDs = checkForProcessPID(processIdentifier)
        if processPIDs is None:
            logger.critical("No process found corresponding to the just launched webApp! Check the log files!")
            sys.exit(2)
        else:
            logger.info("Success!")

def uwsgi(config, name):
    """ Write out the configuration file. """
    # Get the uwsgi user options
    uwsgiConfigFile = config[name]["uwsgi"]
    # Not necessarily the same as "name". For example, the DQM receiver has name = "DQM"
    # and uwsgiName = "dqmReceiver"
    uwsgiName = uwsgiConfigFile.get("name", "{0}".format(name))

    if not "wsgi-file" in uwsgiConfigFile and not "module" in uwsgiConfigFile:
        raise KeyError("Must pass either \"wsgi-file\" or \"module\" for the uwsgi configuration!"
                       " \"wsgi-file\" corresponds to a path to a python file which contains the app."
                       " \"module\" is the python module path to a module containing the app.")

    if not uwsgiConfigFile["enabled"]:
        logger.warn("uwsgi configuration present for {0}, but not enabled".format(name))

    # This is the base configuration which sets the default values
    uwsgiConfig = {
        # Socket setup
        "socket" : "/tmp/{name}.sock",
        "vacuum" : True,
        # Stats
        "stats" : "/tmp/{name}Stats.sock",

        # Setup
        "chdir" : "/opt/overwatch",

        # App
        # Need either wsgi-file or module!
        "callable" : "app",

        # Instances
        # Number of processes
        "processes" : 4,
        # Number of threads
        "threads": 2,
        # Minimum number of workers to keep at all times
        "cheaper": 2,

        # Configure master
        "master" : True,
        "master-fifo" : "wsgiMasterFifo{name}"
    }

    # Add the custom configuration into the default configuration defined above
    uwsgiConfig.update(uwsgiConfigFile)

    # Inject name into the various values if needed
    for k, v in uwsgiConfig.iteritems():
        if isinstance(v, str):
            uwsgiConfig[k] = v.format(name = uwsgiConfigFile.get("name", "webApp"))

    # Put dict inside of "uwsgi" block for it to be read properly by uwsgi
    uwsgiConfig = { "uwsgi" : uwsgiConfig }

    filename = "{0}.yaml".format(uwsgiName)
    logger.info("Writing configuration file to {0}".format(filename))
    with open(filename, "wb") as f:
        yaml.dump(uwsgiConfig, f, default_flow_style = False)

def startNginx(name = "nginx", logFilename = "nginx", supervisord = False):
    args = [
            "/usr/sbin/nginx"
            ]
    startProcessWithLog(args = args, name = name, logFilename = logFilename, supervisord = supervisord)

def nginx(config, name):
    """ Setup and launch nginx. """
    mainNginxConfig = """
server {
    listen 80 default_server;
    # "_" is a wildcard for all possible server names
    server_name _;
    location / {
        include uwsgi_params;
        uwsgi_pass unix:///tmp/%(name)s.sock;
    }
}"""
    mainNginxConfig = mainNginxConfig % {"name": name}

    nginxBasePath = config["webServer"].get("basePath", "/etc/nginx")
    nginxConfigPath = os.path.join(nginxBasePath, config["webServer"].get("configPath", "conf.d"))
    nginxSitesPath = os.path.join(nginxBasePath, config["webServer"].get("sitesPath", "sites-enabled"))

    # Create folders that dont' exist
    # But don't mess with this if it's in /etc/nginx
    if nginxBasePath != "/etc/nginx":
        paths = [nginxBasePath, nginxConfigPath, nginxSitesPath]
        for path in paths:
            if not os.path.exists(path):
                os.makedirs(path)

    with open(os.path.join(nginxSitesPath, "{0}Nginx.conf".format(name)), "wb") as f:
        f.write(mainNginxConfig)

    gzipConfig = """
# GZip configuration
# Already setup in main config!
#gzip on;
#gzip_disable "msie6";

gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 16 8k;
gzip_http_version 1.1;
gzip_min_length 256;
gzip_types
    text/plain
    text/css
    application/json
    application/x-javascript
    text/xml
    application/xml
    application/xml+rss
    application/javascript
    text/javascript
    application/vnd.ms-fontobject
    application/x-font-ttf
    font/opentype
    image/svg+xml
    image/x-icon;
"""

    with open(os.path.join(nginxConfigPath, "gzip.conf"), "wb") as f:
        f.write(gzipConfig)

def webAppSetup(config):
    """ Setup web app by installing bower components (polymer) and jsroot.

    Polymerizer and minify is handled by webassets.
    """
    args = ["./installOverwatchExternalDependencies.sh"]
    startProcessWithLog(args, name = "Install Overwatch external dependencies", logFilename = "installExternals")

def startOverwatch(configFilename, fromEnvironment, avoidNohup = False):
    """ Start the various parts of Overwatch.
    
    Components are only started if they are included in the configuration. """
    # Get configuration
    if fromEnvironment:
        # From environment
        logger.info("Loading configuration from environment variable \"{}\"".format(fromEnvironment))
        config = yaml.load(os.environ[fromEnvironment], Loader=yaml.SafeLoader)
    else:
        # From file
        logger.info("Loading configuration from file \"{}\"".format(configFilename))
        with open(configFilename, "rb") as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)

    # Setup
    supervisord = "supervisord" in config
    if supervisord:
        logger.info("Setting up supervisord")

        # Setup
        setupSupervisord(config)

        # Must be avoided when using supervisord
        config["avoidNohup"] = True
    else:
        config["avoidNohup"] = avoidNohup

    logger.info("Config:")
    pprint.pprint(config)

    if "cert" in config and config["cert"]["enabled"]:
        # TODO: Update default location to "~/.globus/overwatchCert.pem" (?)
        writeSensitiveVariableToFile(config = config,
                                     name = "cert",
                                     prettyName = "certificate",
                                     defaultWriteLocation = "overwatchCert.pem")

    if "sshKey" in config and config["sshKey"]["enabled"]:
        # TODO: Update default write location to "~/ssh/id_rsa" (?)
        writeSensitiveVariableToFile(config = config,
                                     name = "sshKey",
                                     prettyName = "SSH key",
                                     defaultWriteLocation = "overwatch.id_rsa")

    # Setup environment
    if "env" in config and config["env"]["enabled"]:
        setupEnv(config)

    if "receiver" in config and config["receiver"]["enabled"]:
        # Start the receiver(s)
        receiver(config)

    if "processing" in config and config["processing"]["enabled"]:
        processing(config)

    if "webApp" in config and config["webApp"]["enabled"]:
        webApp(config)

    # Start supervisord
    if "supervisord" in config and config["supervisord"]:
        # Reload supervisor config
        process = subprocess.Popen(["supervisorctl", "update"])

def run():
    # Setup command line parser
    parser = argparse.ArgumentParser(description = "Start Overwatch")
    parser.add_argument("-c", "--config", metavar="configFile",
                        type=str, default="deployConfig.yaml",
                        help="Path to config filename")
    parser.add_argument("-e", "--fromEnvironment", metavar="envVariable",
                        type=str, default="",
                        help="Take config from environment.")
    parser.add_argument("-l", "--logLevel", metavar="level",
                        type=str, default="DEBUG",
                        help="Set the log level.")
    parser.add_argument("-a", "--avoidNohup",
                        action="store_true",
                        help="Pass this option to indicdate if nohup should be avoided (say, if systemd is calling the script)")

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

    startOverwatch(configFilename = args.config, fromEnvironment = args.fromEnvironment, avoidNohup = args.avoidNohup)

if __name__ == "__main__":
    run()
