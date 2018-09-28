#!/usr/bin/env python

""" Handles deployment and starting of Overwatch and related processes.

It can handle the configuration and execution of:

- ``autossh`` for SSH tunnels.
- ``ZODB`` for the Overwatch Database
- Overwatch ZMQ receiver
- Overwatch DQM receiver
    - Via ``uswgi``, ``uwsgi`` behind ``nginx`` or directly.
- Overwatch processing
- Overwatch web app
    - Via ``uswgi``, ``uwsgi`` behind ``nginx`` or directly.

It can also handle receiving SSH Keys and grid certificates passed in via
environment variables.

Usually, this module is executed directly in docker containers. All options
are configured via a YAML file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

from __future__ import print_function
from builtins import super
from future.utils import iteritems

import functools
import os
import stat
import signal
import logging
import argparse
import subprocess
import sys
import time
import warnings
import ruamel.yaml as yaml
# Help for handling string based configurations.
import inspect
try:
    # Python 3
    from configparser import ConfigParser
except ImportError:  # pragma: no cover . Py2 will cover this, but not p3. Either way, it's not interesting, so ignore it.
    # Python 2
    from ConfigParser import SafeConfigParser as ConfigParser

logger = logging.getLogger("")

# Convenience
import pprint

def expandEnvironmentalVars(loader, node):
    """ Expand the environment variables in a scalar (str) value while reading the YAML config.

    This plugs into the YAML loader that is responsible for loading the deployment information from
    the YAML configuration file.

    Args:
        loader (yaml.Loader): YAML loader which is parsing the configuration.
        node (SequenceNode): Node containing the list of the paths to join together.
    Returns:
        str: The scalar value (str) with any recognized environment variables expanded. The expansion
            is performed using ``os.path.expandvars``.
    """
    val = loader.construct_scalar(node)
    # Need to strip "\n" due to it being inserted when variables are expanded
    val = os.path.expandvars(val).replace("\n", "")
    return str(val)
# Add the plugin into the loader.
yaml.SafeLoader.add_constructor('!expandVars', expandEnvironmentalVars)

class executable(object):
    """ Base executable class.

    Note:
        Arguments after ``config`` are values which are set via the config.

    Args:
        name (str): Name of the process that we are starting. It doesn't need to be the executable name,
                as it's just used for informational purposes.
        description (str): Description of the process for clearer display, etc.
        args (list): List of arguments used to start the process.
        config (dict): Configuration for the executable.
        runInForeground (bool): True if the process should be run in the foreground. This means that process will
            be blocking. Note that this option is not meaningful if supervisord is being used. Default: False.
        enabled (bool): True if the task should actually be executed.
    Attributes:
        name (str): Name of the process that we are starting. It doesn't need to be the executable name,
                as it's just used for informational purposes.
        description (str): Description of the process for clearer display, etc.
        args (list): List of arguments to be executed.
        config (dict): Configuration for the executable.
        processIdentifier (str): A unique string which identifies the process (to be used to check if it already
            exists). It may need to include arguments to be unique, which will then depend on the order in which
            the process arguments are defined. It is determined by the fully formatted arguments.
        supervisord (bool): True if the process launching should be configured for ``supervisord``.
            This means that the process won't be started immediately. Note that this is a class variable, so
            we only need to set it once when starting the deployment.
        shortExecutionTime (bool): True if the executable executes and completes quickly. In this case, supervisord
            need special options to ensure that it doesn't think that the executable failed immediately and should be
            restarted.
        logFilename (str): Filename for the log file. Default: ``{name}.log``.
        runInForeground (bool): True if the process should be run in the foreground. This means that process will
            be blocking. Note that this option is not meaningful if supervisord is being used. Default: ``False``.
        executeTask (bool): Whether the executable should actually be executed. Set via the "enabled" field of
            the config. Default: ``False``.
    """
    # Avoid having to set this for every object given that it should be the same for (nearly) every one.
    supervisord = False

    def __init__(self, name, description, args, config):
        self.name = name
        self.description = description
        self.args = args
        self.config = config

        # Will be derived from the arguments once they have been fully formatting.
        self.processIdentifier = None

        # Additional options
        self.shortExecutionTime = False
        self.logFilename = "{name}.log".format(name = self.name)
        self.runInForeground = self.config.get("runInForeground", False)
        self.executeTask = self.config.get("enabled", False)

    def getProcessPID(self):
        """ Retrieve the process PID via ``pgrep`` for a process identifier by a given identifier.

        Note:
            Since the arguments should be unique, it is expected that only 0 or 1 PID can be returned.
            In the case of more than that, an exception is raised.

        Args:
            None.
        Returns:
            list: PID(s) from ``pgrep``.

        Raises:
            subprocess.CalledProcessError: If the process called returns a error code other than 0 (which indicates
                success) or 1 (which indicates that the process was not found).
            ValueError: If we return more than one PID for the given process identifier.
        """
        try:
            res = subprocess.check_output(["pgrep", "-f", self.processIdentifier], universal_newlines = True)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                logger.info("Process associated with identifier '{processIdentifier}' was not found".format(processIdentifier = self.processIdentifier))
                return []
            else:
                raise
        # Retrieve each PID as an entry in a list by strip out trailing "\n" (which is returned when
        # using `universal_newlines`), and then splitting on each new line.
        PIDs = res.strip("\n").split("\n")
        PIDs = [int(pid) for pid in PIDs if pid != ""]

        # We generally only expect one PID, so we should raise an issue clearly if we find more than one.
        # If multiple PIDs is fine, then we can add an option for when this can happen.
        if len(PIDs) > 1:
            raise ValueError("Multiple PIDs {PIDs} found for process with identifier {processIdentifier}!".format(PIDs = PIDs, processIdentifier = self.processIdentifier))
        return PIDs

    def killExistingProcess(self, sig = signal.SIGINT):
        """ Kill processes by PID. The kill signal will be sent to the entire process group.

        Args:
            sig (signal.Signals): Signal to be sent to the processes. Default: signal.SIGINT
        Returns:
            int: Number of processes killed.

        Raises:
            RuntimeError: If the process identifier is found to still have an associated PID after attempting
                to kill the process.
        """
        PIDs = self.getProcessPID()
        logger.debug("Killing existing {description} processes with PID(s) {PIDs}".format(description = self.description, PIDs = PIDs))
        # If there are no PIDs, we can just return early
        if not PIDs:
            return 0

        nKilled = 0
        for pid in PIDs:
            logger.debug("Killing process with PID {pid}".format(pid = pid))
            # NOTE: It doesn't appear that we need to kill with ``-1`` to send the signal to the entire process group.
            # NOTE: For whatever reason, ``killpg`` doesn't appear to work. It claims that the process doesn't
            #       exist regardless of the input.
            os.kill(pid, sig)
            # Keep track of how many times we've called kill
            nKilled += 1

        # Check that killing the process was successful
        # If not, throw an error
        PIDs = self.getProcessPID()
        logger.debug("PIDs left after killing processes: {PIDs}".format(PIDs = PIDs))
        if PIDs:
            raise RuntimeError("Requested to kill existing '{description}' processes, but found PIDs {PIDs} after killing the processes. Please investigate!".format(description = self.description, PIDs = PIDs))

        return nKilled

    def startProcessWithLog(self):
        """ Start (or otherwise setup) the process with the given arguments and log the output.

        For a normal process, we configure it to log to the given filename and start it immediately. In the case that
        the process should be launched with ``supervisord``, the process won't be launched immediately.  Instead, the
        process and log information will be appended to the existing ``supervisord`` configuration.

        Args:
            None.
        Returns:
            subprocess.Popen or None: If the process is started immediately, then we return the ``Popen`` class
                associated with the started process. Otherwise, we return None.
        """
        if self.supervisord:
            # Use configparser to create the configuration from a dict.
            process = ConfigParser()
            programIdentifier = "program:{name}".format(name = self.name)
            options = {
                "command": " ".join(self.args),
                # Redirect the stderr into the stdout.
                "redirect_stderr": True,
                # 5 MB log file with 10 backup files.
                "stdout_logfile_maxbytes": 500000,
                "stdout_logfile_backups": 10,
            }

            # Prevents supervisord from immediately restarting a process which executes quickly.
            if self.shortExecutionTime:
                options.update({
                    "autorestart": False,
                    "startsecs": 0,
                })

            # Store the final configuration under the particular process identifier and write out the config.
            process[programIdentifier] = options
            # Append so that other processes can also be included.
            with open("supervisord.conf", "a") as f:
                process.write(f)

            # The return value is not really meaningful in this case, since it won't be launched until the end.
            process = None
        else:
            with open(self.logFilename, "w") as logFile:
                logger.debug("Starting '{name}' with args: {args}".format(name = self.name, args = self.args))
                # Redirect stderr to stdout so the information isn't lost.
                process = subprocess.Popen(self.args,
                                           stdout = logFile,
                                           stderr = subprocess.STDOUT)

        return process

    def setup(self):
        """ Prepare for calling the executable.

        Here we setup the arguments for the executable using values in the config and we determine the
        ``processIdentifier``.

        Args:
            None
        Returns:
            None
        """
        # Determine the function arguments based on the config and setup.
        self.formatMembers()
        # Since the arguments are now fully determine, we can now determine the process identifier.
        # In principle, this can overridden by the user by setting the attribute.
        if not self.processIdentifier:
            self.processIdentifier = " ".join(self.args)

    def formatMembers(self):
        """ Determine the description and arguments for the executable based on the given configuration.

        This formatting is done by generically providing all arguments in the config to the format each string.

        Note:
            This formatting will fail if a particular key doesn't exist!

        Args:
            None
        Returns:
            None. Modifies the ``name``, ``description``, ``args``, and ``logFilename`` member variables.
        """
        self.name = self.name.format(**self.config)
        self.description = self.description.format(**self.config)
        self.args = [arg.format(**self.config) for arg in self.args]
        self.logFilename = self.logFilename.format(**self.config)

    def run(self):
        """ Driver function for running executables.

        The options that are executed here depend heavily on the provided YAML config.
        TODO: Document options here...

        Args:
            None.
        Returns:
            None.
        """
        # Handle configuration, etc.
        self.setup()

        # Bail out immediately after task setup if the task is not supposed to be executed.
        if self.executeTask is False:
            return None

        # Check for existing process
        # TODO: Maybe only do this sometimes??
        #if config.get("forceRestart", False) or receiverConfig.get("forceRestartTunnel", False):
        if self.config.get("forceRestart", False):
            self.killExistingProcess()

        # If we are not using supervisord and we want to launch multiple process, they must be
        # launched with `nohup` so they run in the background.
        if self.supervisord is False or self.config["foreground"] is True:
            self.args = ["nohup"] + self.args

        # TODO: Perhaps we can skip this if it already exists and we don't want to force restart?
        # Actually execute the process
        process = self.startProcessWithLog()

        # Check the output to see if we've succeeded. If it was executed (ie. we are not using ``supervisord``),
        # process is not None, so we can use that as a proxy for whether to check for successful execution.
        # TODO: Maybe only do this sometimes?? Set via config?
        if process and self.shortExecutionTime is False:
            logger.info("Check that the {name} executable launched successfully...".format(name = self.name))
            time.sleep(1.5)
            PIDs = self.getProcessPID()
            if not PIDs:
                raise RuntimeError("Failed to find the executed process with identifier {processIdentifier}. It appears that it did not execute correctly or already completed.".format(processIdentifier = self.processIdentifier))

class sshKnownHostsExecutable(executable):
    """ Create a SSH ``known_hosts`` file with the SSH address in the configuration.

    Note:
        If the known_hosts file exists, it is assumed to have the address already and is not created! If this is
        problematic in the future, we could instead amend to the file. However, in that case, it will be important
        to check for duplicates.

    Note:
        Arguments after ``config`` are values which will be used for formatting and are required in the config.

    Args:
        config (dict): Configuration for the executable.
        port (int): SSH connection port.
        address (str): SSH connection address.

    Attributes:
        knownHostsPath (str): Path to the known hosts file. Assumed to be at ``$HOME/.ssh/known_hosts``.
    """
    def __init__(self, config):
        name = "ssh-keyscan"
        description = "Use ssh-keyscan to add addresses to the known_hosts file."
        args = [
            "ssh-keyscan",
            "-p {port}",
            "-H",
            "{address}",
        ]
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)
        # The information should stored be in the $HOME/.ssh/known_hosts
        self.knownHostsPath = os.path.expandvars(os.path.join("$HOME", ".ssh", "known_hosts")).replace("\n", "")
        # This will execute rather quickly.
        self.shortExecutionTime = True

    def setup(self):
        """ Setup creating the known_hosts file.

        In particular, the executable should only be run if the ``known_hosts`` file doesn't exist.
        """
        logger.debug("Checking for known_hosts file at {knownHostsPath}".format(knownHostsPath = self.knownHostsPath))
        if not os.path.exists(self.knownHostsPath):
            directoryName = os.path.dirname(self.knownHostsPath)
            if not os.path.exists(directoryName):
                os.makedirs(directoryName)
                # Set the proper permissions
                os.chmod(os.path.dirname(self.knownHostsPath), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            self.executeTask = True
        # Take advantage of the log file to write the process output to the known_hosts file.
        self.logFilename = self.knownHostsPath

class autossh(executable):
    """ Start ``autossh`` to create a SSH tunnel.

    Note:
        Arguments after ``config`` are values which will be used for formatting and are required in the config.

    Args:
        config (dict): Configuration for the executable.
        localPort (int): Port where the HLT data should be made available on the local system.
        hltPort (int): Port where the HLT data is available on the remote system.
        port (int): SSH connection port.
        username (str): SSH connection username.
        address (str): SSH connection address.
    """
    def __init__(self, config):
        name = "autossh_{receiver}"
        description = "{receiver} autossh tunnel"
        args = [
            "autossh",
            "-L {localPort}:localhost:{hltPort}",
            "-o ServerAliveInterval=30",  # Built-in ssh monitoring option
            "-o ServerAliveCountMax=3",   # Built-in ssh monitoring option
            "-p {port}",
            "-l {username}",
            "{address}",
            "-M 0",                       # Disable autossh built-in monitoring
            "-f",
            "-N",
        ]
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)

        # This will execute rather quickly.
        self.shortExecutionTime = True

    def setup(self):
        """ Setup the ``autossh`` tunnel by additionally setting up the known_hosts file. """
        # Call the base class setup first so that all of the variables are fully initialized and formatted.
        super().setup()
        # For the tunnel to be created successfully, we need to add the address of the SSH server
        # to the known_hosts file, so we create it here. In principle, this isn't safe if we're not in
        # a safe environment, but this should be fine for our purposes.
        knownHosts = sshKnownHostsExecutable(config = self.config)
        knownHosts.run()

class zmqReceiver(executable):
    """ Start the ZMQ receiver.

    Note:
        Arguments after ``config`` are values which will be used for formatting and are required in the config.

    Args:
        config (dict): Configuration for the executable.
        receiver (str): Three letter subsystem name. For example, ``EMC``.
        localPort (int): Port where the HLT data should be made available on the local system.
        dataPath (str): Path to where the data should be stored.
        select (str): Selection string for the receiver.
        additionalOptions (list): Additional options to be passed to the receiver.
        receiverPath (str): Path to directory which contains the receiver. Default: "receiver/bin".
    """
    def __init__(self, config):
        name = "zmqReceiver_{receiver}"
        description = "ZMQ Receiver for the {receiver} subsystem"
        # From official script:
        # zmqReceive --in=REQ>tcp://localhost:60323 --verbose=1 --sleep=60 --timeout=100 --select= --subsystem=TPC
        # From this script:
        # zmqReceive --subsystem=EMC --in=REQ>tcp://localhost:60321 --verbose=1 --sleep=60 --timeout=100 --select=
        #
        # NOTE: We don't need to escape most quotes!
        args = [
            "zmqReceive",
            "--subsystem={receiver}",
            "--in=REQ>tcp://localhost:{localPort}",
            "--dataPath={dataPath}",
            "--verbose=1",
            "--sleep=60",
            "--timeout=100",
            "--select={select}",
        ]
        # Ensure that the receiver is formatted properly
        receiverName = config["receiver"]
        # By making it upper case
        receiverName = receiverName.upper()
        # And ensure that it is the proper length.
        if len(receiverName) != 3:
            raise ValueError("Receiver name {receiverName} is not 3 letters long!".format(receiverName = receiverName))
        # Reassign the final result.
        config["receiver"] = receiverName

        # Add default values to the config if necessary
        config["dataPath"] = self.config.get("dataPath", "data")
        config["select"] = self.config.get("select", "")

        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)

    def setup(self):
        """ Setup required for the ZMQ receiver.

        In particular, we add any additionally requested receiver options from the configuration,
        as well as setting up the SSH tunnel.
        """
        # Call the base class setup first so that all of the variables are fully initialized and formatted.
        super().setup()

        # TODO: Do we want to use a class for adding this to the environment??
        # Add the executable location to the path if necessary.
        receiverPath = self.config.get("receiverPath", "receiver/bin")
        if receiverPath:
            # Could have environment vars, so we need to expand them.
            # Need to strip "\n" due to it being inserted when variables are expanded
            receiverPath = os.path.expandvars(receiverPath).replace("\n", "")
            logger.debug('Adding receiver path "{receiverPath}" to PATH'.format(receiverPath = receiverPath))
            # Also remove "\n" at the end of the path variable for clarity
            os.environ["PATH"] = os.environ["PATH"].rstrip() + os.pathsep + receiverPath

        # Append any additional options that might be defined in the config.
        # We do this after the base class setup so it doesn't pollute the process identifier since custom
        # options may vary from execution to execution.
        if "additionalOptions" in self.config:
            additionalOptions = self.config["additionalOptions"]
            logger.debug("Adding additional receiver options: {additionalOptions}".format(additionalOptions = additionalOptions))
            self.args.append(additionalOptions)

        # Setup the autossh tunnel if required.
        if self.config["tunnel"]:
            tunnel = autossh(config = self.config)
            tunnel.run()

        # Conditions for run?
        #if processPIDs is not None and (config["receiver"].get("forceRestart", None) or receiverConfig.get("forceRestart", None)):

class zodb(executable):
    """ Start the ZODB database.

    Note:
        Arguments after ``config`` are values which will be used for formatting and are required in the config.

    Args:
        config (dict): Configuration for the executable.
        address (str): IP address for the database.
        port (int): Port for the database.
        databasePath (str): Path to where the database file should be stored.
        logFile (str): Filename and full path to the log file.
        logFormat (str): Format of the log. Default: "%(asctime)s %(message)s"

    Attributes:
        configFilename (str): Location where the generated configuration file should be stored. Default: ...
    """
    def __init__(self, config):
        # TODO: Can we remove the log file here and just handle the log in supervisord?
        name = "zodb"
        description = "ZODB database"
        self.configFilename = "data/config/database.conf"
        args = [
            "runzeo",
            "-C {configFilename}".format(configFilename = self.configFilename),
        ]
        # Set the default log format in the config if not specified.
        if "logForamt" not in config:
            config["logFormat"] = "%(asctime)s %(message)s"
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)

    def setup(self):
        """ Setup required for the ZODB database. """
        # Call the base class setup first so that all of the variables are fully initialized and formatted.
        super().setup()

        # Create the main config. Unfortunately, the configuration file format is custom, so we cannot use
        # another module such as ``configparser`` to generate the config. Consequently, we just use a string.
        zeoConfig = """
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
        """
        # Fill in the values.
        zeoConfig = zeoConfig.format(**self.config)

        # Complete the process by cleaning up the config and writing it.
        # To cleanup the shared indentation of the above string, we use ``inspect.cleandoc()``.
        # This is preferred over ``textwrap.dedent()`` because it will still work even if there
        # is a string on the first line (which has a different indentation that we want to ignore).
        zeoConfig = inspect.cleandoc(zeoConfig)

        with open(self.configFilename, "w") as f:
            f.write(zeoConfig)

class overwatchExecutable(executable):
    """ Starts an Overwatch (ie python-based) based executable.

    In the config, it looks for:

    - additionalConfig (dict): Additional options to added to the YAML configuration.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add the filename so that it can be modified later if so desired.
        self.filename = "config.yaml"

    def setup(self):
        """ Setup required for Overwatch data handling and transfer.

        In particular, we write any passed custom configuration options out to an Overwatch YAML config file.
        """
        # Call the base class setup first so that all of the variables are fully initialized and formatted.
        super().setup()

        # Write out the custom config
        self.writeCustomConfig()

    def writeCustomConfig(self):
        """ Write out a custom Overwatch configuration file.

        First, we read in any existing configuration, and then we update that configuration
        with the newly provided one, rewriting the entire config file.

        As an example, for a ``config`` as

        .. code-block:: yaml

            option1: true
            myAdditionalOptions:
                opt2: true
                opt3: 3

        we would pass in the key name ``myAdditionalOptions``, and it would write ``opt2`` and ``opt3``
        to ``self.filename``.

        Args:
        Returns:
            None.
        """
        configToWrite = self.config.get("additionalOptions", {})
        # If the configuration is empty, we just won't do anything.
        if configToWrite:
            config = {}
            if os.path.exists(self.filename):
                with open(self.filename, "r") as f:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        config = yaml.load(f, Loader = yaml.SafeLoader)

            # Add our new options in.
            config.update(configToWrite)

            # Write out configuration.
            # We overwrite the previous config because we already loaded it in, so in effect we are appending
            # (but we reduplication of options)
            with open(self.filename, "w") as f:
                yaml.dump(config, f, default_flow_style = False)

class overwatchFlaskExecutable(overwatchExecutable):
    """ Start an Overwatch Flask executable.

    Used for starting the web app and the DQM receiver - both of these are flask based.

    In the config, it looks for:

    - additionalConfig (dict): Additional options to added to the YAML configuration.
    """
    def setup(self):
        """ Setup required for an Overwatch flask executable.

        In particular, we write any passed custom configuration options out to an Overwatch YAML config file,
        as well as potentially setup ``uwsgi`` and/or setup and run ``nginx``.
        """
        # Write custom configuration for the overwatch executable.
        self.writeCustomConfig()

        # Create an underlying uwsgi app to handle the setup and execution.
        if "nginx" in self.config:
            if self.config["nginx"]["enabled"] is True:
                server = nginx(self.config["nginx"])
                server.setup()
                server.run()

        # Create an underlying uwsgi app to handle the setup and execution.
        self = uwsgi.createObject(self)

        # We call this last here because we are going to update variables if we use uwsgi for execution.
        super().setup()

class supervisor(executable):
    """ Start ``supervisor`` (through ``supervisord``) to manage processes.

    We don't need options for this executable. It is either going to be launched or it isn't.

    Note:
        Don't use ``run()`` for this executable. Instead, the setup and execution steps should be
        performed separately because the basic config is needed at the beginning, while the final execution
        is needed at the end.

    Args:
        *args (list): Absorb extra arguments.
        **kwargs (dict): Absorb extra arguments.
    """
    def __init__(self, *args, **kwargs):
        name = "supervisord"
        description = "Supervisord"
        args = [
            "supervisorctl",
            "update",
        ]
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = {})

    def setup(self):
        """ Setup required for the ``supervisord`` executable.

        In particular, we need to write out the main configuration.
        """
        # Write to the supervisord config
        filename = "supervisord.conf"
        if not os.path.exists(filename):
            logger.info("Creating supervisord main config")
            # Write the main config
            config = ConfigParser()
            # Main supervisord configuration
            config["supervisord"] = {
                "nodaemon": True,
                # Take advantage of the overwatch data directory.
                "logfile": "data/logs/supervisord.log",
                "childlogdir": "data/logs",
                # 5 MB log file with 10 backup files
                "logfile_maxbytes": 5000000,
                "logfile_backups": 10,
            }
            # Unix http server monitoring options
            config["unix_http_server"] = {
                # Path to the socket file
                "file": "/tmp/sockets/supervisor.sock",
                # Socket file mode (default 0700)
                "chmod": "0700",
            }
            # These options section must remain in the config file for RPC
            # (supervisorctl/web interface) to work, additional interfaces may be
            # added by defining them in separate ``rpcinterface: sections``
            config["rpcinterface:supervisor"] = {
                "supervisor.rpcinterface_factory": "supervisor.rpcinterface:make_main_rpcinterface",
            }
            # supervisorctl options
            config["supervisorctl"] = {
                # Use a unix:// URL  for a unix socket
                "serverurl": "unix:///tmp/supervisor.sock",
            }

            # Write out the final config.
            with open(filename, "w+") as f:
                config.write(f)
        else:
            logger.info("Supervisord config already exists - skipping creation.")

    def run(self):
        """ We want to run in separate steps, so this function shouldn't be used. """
        raise NotImplementedError("The supervisord executable should be run in multiple steps.")

class nginx(executable):
    """ Start ``nginx`` to serve a ``uwsgi`` based web app.

    Note:
        Arguments after ``config`` are values which will be used for formatting and are required in the config.

    Note:
        It is generally recommended to run ``nginx`` in a separate container, but this option is maintained
        for situations where that is not possible. When run separately, we connect to the web app via an http socket,
        while When run together, we connect to the ``uwsgi`` web app via a socket.

    Args:
        config (dict): Configuration for the executable.
        name (str): Name of web app (especially the socket) which will be behind the ``nginx`` server.
        basePath (str): Path to the ``nginx`` settings and configuration directory. Default: "/etc/nginx".
        configPath (str): Path to the main ``nginx`` configuration directory. Default: "${basePath}/conf.d".
        sitesPath (str): Path to the ``nginx`` sites directory. Default: "${basePath}/sites-enabled".
    """
    def __init__(self, config):
        name = "nginx"
        description = "NGINX web server for a uwsgi web app"
        args = [
            "/usr/sbin/nginx",
        ]
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)

    def setup(self):
        """ Setup required for the ``nginx`` executable.

        In particular, we need to write out the main configuration (which directs to the socket to which traffic
        should be passed), as well as the ``gzip`` configuration.
        """
        mainNginxConfig = """
        server {
            listen 80 default_server;
            # "_" is a wildcard for all possible server names
            server_name _;
            location / {
                include uwsgi_params;
                uwsgi_pass unix:///tmp/sockets/%(name)s.sock;
            }
        }"""
        # Use "%" formatting because the `nginx` config uses curly brackets.
        mainNginxConfig = mainNginxConfig % {"name": self.name}
        mainNginxConfig = inspect.cleandoc(mainNginxConfig)

        # Determine the path to the main config file.
        nginxBasePath = self.config.get("basePath", "/etc/nginx")
        nginxConfigPath = os.path.join(nginxBasePath, self.config.get("configPath", "conf.d"))
        nginxSitesPath = os.path.join(nginxBasePath, self.config.get("sitesPath", "sites-enabled"))

        # Create folders that don't exist, but don't mess with this if it's in `/etc/nginx`.
        if nginxBasePath != "/etc/nginx":
            paths = [nginxBasePath, nginxConfigPath, nginxSitesPath]
            for path in paths:
                if not os.path.exists(path):
                    os.makedirs(path)

        with open(os.path.join(nginxSitesPath, "{0}Nginx.conf".format(self.name)), "w") as f:
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

        # Cleanup and write the gzip config.
        gzipConfig = inspect.cleandoc(gzipConfig)
        with open(os.path.join(nginxConfigPath, "gzip.conf"), "w") as f:
            f.write(gzipConfig)

class uwsgi(executable):
    """ Start a ``uwsgi`` executable.

    Note:
        We take the default initialization from the base class.
    """
    @classmethod
    def createObject(cls, obj):
        """ Create the underlying ``uwsgi`` object if requested in the given executable config.

        Note that this expects a ``uwsgi`` configuration block inside of the executable config.

        Args:
            cls (uwsgi): uwsgi class which will be used to create a uwsgi executable.
            obj (executable): Executable which may be run via uwsgi. Its configuration determines where it is
                utilized.
        Returns:
            executable: Updated executable object.

        Raises:
            KeyError: If the executable config doesn't contain an ``uwsgi`` configuration.
        """
        # Config validation
        if "uwsgi" not in obj.config:
            raise KeyError('Expected "uwsgi" block in the executable configuration, but none was found!')

        if obj.config["uwsgi"].get("enabled", False) is True:
            uwsgiApp = cls(name = obj.name,
                           description = obj.description,
                           args = None,
                           config = obj.config["uwsgi"])
            # This will create the necessary uwsgi config.
            uwsgiApp.setup()

            # Extract the newly defined arguments.
            obj.args = uwsgiApp.args

        # We want to return the object one way or another.
        return obj

    def setup(self):
        """ Setup required for executing a web app via ``uwsgi``.

        Raises:
            KeyError: If ``wsgi-file`` or ``module`` is not specific in the configuration, such that the ``uwsgi``
                executable cannot not be defined.
        """
        filename = "{name}.yaml".format(name = self.name)
        self.args = [
            "uwsgi",
            "--yaml",
            filename,
        ]

        # Once we have the arguments defined, we can move setup the base class.
        super().setup()

        # Define the uwsgi config
        if "wsgi-file" not in self.config and "module" not in self.config:
            raise KeyError('Must pass either "wsgi-file" or "module" in the uwsgi configuration!'
                           '"wsgi-file" corresponds to a path to a python file which contains the app.'
                           '"module" is the python module path to a module containing the app.')

        # This is the base configuration which sets the default values
        uwsgiConfig = {
            # Socket setup
            "socket": "/tmp/sockets/wsgi_{name}.sock",
            "vacuum": True,
            # Stats
            "stats": "/tmp/sockets/wsgi_{name}_stats.sock",

            # Setup
            "chdir": "/opt/overwatch",

            # App
            # Need either wsgi-file or module!
            "callable": "app",

            # Instances
            # Number of processes
            "processes": 4,
            # Number of threads
            "threads": 2,
            # Minimum number of workers to keep at all times
            "cheaper": 2,

            # Configure master fifo
            "master": True,
            "master-fifo": "wsgiMasterFifo{name}",
        }

        # Add the custom configuration into the default configuration defined above
        # Just in case "enabled" was stored in the config, remove it now so it's not added to the uwsgi config
        self.config.pop("enabled", None)
        uwsgiConfig.update(self.config)

        # Inject name into the various values if needed
        for k, v in iteritems(uwsgiConfig):
            if isinstance(v, str):
                uwsgiConfig[k] = v.format(name = self.name)

        # Put dict inside of "uwsgi" block for it to be read properly by uwsgi
        uwsgiConfig = {
            "uwsgi": uwsgiConfig
        }

        logger.info("Writing configuration file to {filename}".format(filename = filename))
        with open(filename, "w") as f:
            yaml.dump(uwsgiConfig, f, default_flow_style = False)

    def run(self):
        """ This should only be used to help configure another executable. """
        raise NotImplementedError("The uwsgi object should not be run directly.")

class enviornmentVariables():
    pass

class environment(executable):
    """ Setup and create the necessary environment for execution.

    Args:

    """
    def __init__(self, config):
        name = "environment"
        description = "Setup and create the necessary execution environment"
        args = []
        super().__init__(name = name,
                         description = description,
                         args = args,
                         config = config)

    def setup(self):
        """ Setup for creating the execution environment.

        In particular, we write our sensitive environment variables and configure ROOT.
        """
        super().setup()

        #if "cert" in config and config["cert"]["enabled"]:
        # TODO: Update default location to "~/.globus/overwatchCert.pem" (?)
        self.writeSensitiveVariableToFile(name = "cert",
                                          prettyName = "certificate",
                                          defaultWriteLocation = "overwatchCert.pem")

        #if "sshKey" in config and config["sshKey"]["enabled"]:
        # TODO: Update default write location to "~/ssh/id_rsa" (?)
        self.writeSensitiveVariableToFile(name = "sshKey",
                                          prettyName = "SSH key",
                                          defaultWriteLocation = "overwatch.id_rsa")

        # Setup environment
        self.setupRoot()
        self.setupEnvironmentVars()

    def writeSensitiveVariableToFile(self, name, prettyName, defaultWriteLocation):
        """ Write SSH key or certificate from environment variable to file. """
        # Check name value (also acts as proxy for the other values)
        if name != "sshKey" and name != "cert":
            raise ValueError("Name \"{}\" is unrecognized! Aborting")

        #sensitiveVariable = getSensitiveVariableConfigurationValues(config, name = name, prettyName = prettyName)
        logger.info("Writing {} from environment variable to file".format(prettyName))
        # Get variable from environment
        variableName = self.config[name].get("variableName", name)
        sensitiveVariable = os.environ[variableName]
        # Check that the variable is not empty
        if not sensitiveVariable:
            raise ValueError("Empty {} passed".format(prettyName))
        logger.debug("variableName: {}, {}: {}".format(variableName, prettyName, sensitiveVariable))

        # Write to file
        writeLocation = self.config[name].get("writeLocation", defaultWriteLocation)
        # Expand filename
        writeLocation = os.path.expanduser(os.path.expandvars(writeLocation))
        if not os.path.exists(os.path.dirname(writeLocation)):
            os.makedirs(os.path.dirname(writeLocation))

        # Ensure that we don't overwrite an existing file!
        if os.path.exists(writeLocation):
            raise IOError("File at {0} already exists and will not be overwritten!".format(writeLocation))
        with open(writeLocation, "w") as f:
            f.write(sensitiveVariable)

        if name == "sshKey":
            # Set the file permissions to 600
            os.chmod(writeLocation, stat.S_IRUSR | stat.S_IWUSR)
            # Set the folder permissions to 700
            os.chmod(os.path.dirname(writeLocation), stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        elif name == "cert":
            # Set the file permissions to 400
            os.chmod(writeLocation, stat.S_IRUSR)

    def setupRoot(self):
        """ Setup ROOT in our execution environment.

        This is done by executing ``thisroot.sh``, capturing the output, and then assigning the updated
        environment to our current environment variables.
        """
        # We only want to add ROOT to the path, etc, if it's not already setup.
        # If ``ROOTSYS`` is setup, it's a pretty good bet that everything else is setup.
        if "ROOTSYS" not in os.environ:
            thisRootPath = os.path.join(self.config["root"]["path"], "bin", "thisroot.sh")
            # Run thisroot.sh, extract the environment, and then set the python environment to those values
            # See: https://stackoverflow.com/a/3505826
            command = ["bash", "-c", "source {thisRootPath} && env".format(thisRootPath = thisRootPath)]

            proc = subprocess.Popen(command, stdout = subprocess.PIPE)

            # Load into the environment
            # Note that this doesn't propagate to the shell where this was executed!
            for line in proc.stdout:
                (key, _, value) = line.partition("=")
                os.environ[key] = value

    def setupEnvironment(self):
        """ Setup execution environment.

        We generically add these environment variables, as well as explicitly checking for those
        related to EOS.
        """
        # TODO: Check for EOS variables?

        for k, v in iteritems(self.config["vars"]):
            # Not necessarily a problem, but I want to make the user aware.
            if k in os.environ:
                logger.warning("Environment variable {k} is already set to {val}. It is being updated to {v}".format(k = k, val = os.environ["k"], v = v))
            os.environ[k] = v

_available_executables = {
    "environment": environment,
    "zodb": zodb,
    "autossh": autossh,
    "zmqReceiver": zmqReceiver,
    "dataTransfer": functools.partial(overwatchExecutable,
                                      name = "dataTransfer",
                                      description = "Overwatch receiver data transfer",
                                      args = [
                                          "overwatchReceiverDataHandling",
                                      ]),
    "processing": functools.partial(overwatchExecutable,
                                    name = "processing",
                                    description = "Overwatch processing",
                                    args = [
                                        "overwatchProcessing",
                                    ]),
    "webApp": functools.partial(overwatchFlaskExecutable,
                                name = "webApp",
                                description = "Overwatch web app",
                                args = [
                                    "overwatchWebApp",
                                ]),
    "dqmReceiver": functools.partial(overwatchFlaskExecutable,
                                     name = "dqmReceiver",
                                     description = "Overwatch DQM receiver",
                                     args = [
                                         "overwatchDQMReciever",
                                     ]),
}

def retrieveExecutable(name):
    """ Retrieve an expected by name.

    This is an extremely minimal helper function to allow for flexibility in the future.

    The available executables are:

    - environment
    - zodb
    - autossh
    - zmqReceiver
    - dqmReceiver
    - processing
    - webApp
    - dataTransfer

    Args:
        name (str): Name of the executable "type". For example, "processing" for Overwatch processing.
            An extensive list is in this docstring.
    Returns:
        executable: The requested executable.

    Raises:
        ValueError: If the requested executable doesn't exist.
    """
    if name not in _available_executables:
        raise KeyError("Executable {name} is invalid.".format(name = name))
    return _available_executables[name]

def startOverwatch(configFilename, fromEnvironment, avoidNohup = False):
    """ Start the various parts of Overwatch.

    Components are only started if they are included in the configuration.

    Args:
        configFilename (str): Filename of the configuration.
        fromEnvironment (str): Name of the environment variable which contains the configuration as a string. This
            is usually created by reading a config file into the variable with ``var=$(cat deployConfig.yaml)``.
        avoidNohup (bool): If true, ``nohup`` (which is used to run processes in the background) should not be used.
    Returns:
        None.
    """
    # Get configuration
    if fromEnvironment:
        # From environment
        logger.info("Loading configuration from environment variable '{fromEnvironment}'".format(fromEnvironment = fromEnvironment))
        config = yaml.load(os.environ[fromEnvironment], Loader=yaml.SafeLoader)
    else:
        # From file
        logger.info("Loading configuration from file \"{}\"".format(configFilename))
        with open(configFilename, "r") as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)

    # Setup
    supervisord = "supervisord" in config
    if supervisord:
        logger.info("Setting up supervisord")

        # Setup
        #setupSupervisord(config)

        # Must be avoided when using supervisord
        config["avoidNohup"] = True
    else:
        config["avoidNohup"] = avoidNohup

    logger.info("Config: {}".format(pprint.pformat(config)))

    if "cert" in config and config["cert"]["enabled"]:
        pass

    if "sshKey" in config and config["sshKey"]["enabled"]:
        pass

    # Setup environment
    if "env" in config and config["env"]["enabled"]:
        #setupEnv(config)
        pass

    if "receiver" in config and config["receiver"]["enabled"]:
        # Start the receiver(s)
        #receiver(config)
        pass

    if "processing" in config and config["processing"]["enabled"]:
        #processing(config)
        pass

    if "webApp" in config and config["webApp"]["enabled"]:
        #webApp(config)
        pass

    # Start supervisord
    if "supervisord" in config and config["supervisord"]:
        # Reload supervisor config
        subprocess.Popen(["supervisorctl", "update"])

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
