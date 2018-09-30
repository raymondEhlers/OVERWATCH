#!/usr/bin/env python

""" Tests for the deploy module, which is used to configure and execute Overwatch scripts.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

from future.utils import iteritems

import pytest
import os
try:
    # For whatever reason, import StringIO from io doesn't behave nicely in python 2.
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import signal
import stat
import inspect
import subprocess
import collections
import logging
logger = logging.getLogger(__name__)

import ruamel.yaml as yaml

from overwatch.base import deploy

def testExpandEnvironmentVars(loggingMixin):
    """ Test the YAML constructor to expand environment vars. """
    testYaml = """
    normalVar: 3
    normalWithDollarSign: "$ Hello World"
    environmentVar: !expandVars $HOME
    expandedWithoutVar: !expandVars "Hello world"
    """
    # Setup the YAML to be read from a stream
    s = StringIO()
    s.write(testYaml)
    s.seek(0)

    config = deploy.yaml.load(s, Loader = yaml.SafeLoader)

    assert config["normalVar"] == 3
    # Should have no impact because it explicitly needs to be tagged (a `$` on it's own is not enough)
    assert config["normalWithDollarSign"] == "$ Hello World"
    assert config["environmentVar"] == os.environ["HOME"]
    # Should have no impact because there are no envrionment ars
    assert config["expandedWithoutVar"] == "Hello world"

def testRetrieveExecutable(loggingMixin):
    """ Tests for retrieving executables. """
    e = deploy.retrieveExecutable("zodb", config = {})
    assert isinstance(e, deploy._available_executables["zodb"])

    with pytest.raises(KeyError) as exceptionInfo:
        e = deploy.retrieveExecutable("helloWorld", config = {})
    assert exceptionInfo.value.args[0] == "Executable helloWorld is invalid."

#: Simple named tuple to contain the execution expectations.
executableExpected = collections.namedtuple("executableExpected", ["name", "description", "args", "config"])

@pytest.fixture
def setupBasicExecutable(loggingMixin, mocker):
    """ Fixture to setup an executable object.

    Returns:
        tuple: (executable, expected) where executable is an executable object and expected are the expected
            parameters.
    """
    expected = {
        "name": "{label}Executable",
        "description": "Basic executable for {label}ing",
        "args": ["execTest", "arg1", "arg2", "test{hello}"],
        "config": {"hello": "world", "label": "test"},
    }
    executable = deploy.executable(**expected)

    for k in ["name", "description"]:
        expected[k] = expected[k].format(**expected["config"])
    expected["args"] = [arg.format(**expected["config"]) for arg in expected["args"]]
    expected = executableExpected(**expected)
    return executable, expected

@pytest.mark.parametrize("processIdentifier", [
    "",
    "unique process identnfier"
    ], ids = ["Default process identifier", "Unique process identifier"])
def testSetupExecutable(setupBasicExecutable, processIdentifier):
    """ Test setting up a basic executable. """
    executable, expected = setupBasicExecutable

    executable.processIdentifier = processIdentifier
    executable.setup()

    assert executable.name == expected.name
    assert executable.description == expected.description
    assert executable.args == expected.args
    assert executable.config == expected.config
    assert executable.processIdentifier == (processIdentifier if processIdentifier else " ".join(expected.args))

def testExecutableFromConfig(loggingMixin):
    """ Test for configuring an executable via a config.

    This duplicates some code from ``setupBasicExecutable``, but it's necessary because we need to create the
    executable in the test function to properly test the initialization.
    """
    expected = {
        "name": "{label}Executable",
        "description": "Basic executable for {label}ing",
        "args": ["execTest", "arg1", "arg2", "test{hello}"],
        "config": {"runInBackground": True, "enabled": True, "label": "test", "hello": "world"},
    }

    executable = deploy.executable(**expected)
    # Run setup so names are properly formatted
    executable.setup()

    # Determine the expected values
    for k in ["name", "description"]:
        expected[k] = expected[k].format(**expected["config"])
    expected["args"] = [arg.format(**expected["config"]) for arg in expected["args"]]
    expected = executableExpected(**expected)

    assert executable.runInBackground == expected.config["runInBackground"]
    assert executable.executeTask == expected.config["enabled"]
    assert executable.logFilename == "{name}.log".format(name = expected.name)

@pytest.mark.parametrize("pid", [
    [],
    [1234],
    ], ids = ["No PIDs", "One PID"])
def testGetProcessPID(setupBasicExecutable, pid, mocker):
    """ Test of getting the process PID identified by the executable properties. """
    executable, expected = setupBasicExecutable
    executable.setup()

    # Pre-process the PID input. We don't do it above so it's easier to read here.
    inputPID = "\n".join((str(p) for p in pid)) + "\n"

    # Mock opening the process
    m = mocker.MagicMock(return_value = inputPID)
    mocker.patch("overwatch.base.deploy.subprocess.check_output", m)

    outputPID = executable.getProcessPID()

    assert outputPID == pid

@pytest.mark.parametrize("returnCode", [
    1,
    3
    ], ids = ["No process found", "Unknown error"])
def testGetProcessPIDSubprocessFailure(setupBasicExecutable, mocker, returnCode):
    """ Test for subprocess failure when getting the process PID. """
    executable, expected = setupBasicExecutable
    executable.setup()

    # Test getting a process ID. We mock it up.
    m = mocker.MagicMock()
    m.side_effect = subprocess.CalledProcessError(returncode = returnCode, cmd = executable.args)
    mocker.patch("overwatch.base.deploy.subprocess.check_output", m)

    if returnCode == 1:
        outputPID = executable.getProcessPID()
        assert outputPID == []
    else:
        with pytest.raises(subprocess.CalledProcessError) as exceptionInfo:
            outputPID = executable.getProcessPID()

        assert exceptionInfo.value.returncode == returnCode

def testGetProcessPIDFailure(setupBasicExecutable, mocker):
    """ Test failure modes of getting the process PID. """
    pid = [1234, 5678]
    executable, expected = setupBasicExecutable
    executable.setup()

    # Pre-process the PID input. We don't do it above so it's easier to read here.
    inputPID = "\n".join((str(p) for p in pid)) + "\n"

    # Test getting a process ID. We mock it up.
    m = mocker.MagicMock(return_value = inputPID)
    mocker.patch("overwatch.base.deploy.subprocess.check_output", m)

    with pytest.raises(ValueError) as exceptionInfo:
        executable.getProcessPID()
    # We don't need to check the exact message.
    assert "Multiple PIDs" in exceptionInfo.value.args[0]

@pytest.fixture
def setupKillProcess(setupBasicExecutable, mocker):
    """ Setup for tests of killing a process.

    Returns:
        tuple: (executable, expected, mGetProcess, mKill) where executable is an executable object and expected are
            the expected parameters, mGetProcess is the mock for ``executable.getProcessPID()``, and mKill is the mock
            for ``executable.killExistingProcess()``.
    """
    executable, expected = setupBasicExecutable

    # First we return the PID to kill, then we return nothing (as if the kill worked)
    mGetProcessPID = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.executable.getProcessPID", mGetProcessPID)
    # Also need to mock the kill command itself.
    mKill = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.os.kill", mKill)

    # Setup
    executable.setup()

    return executable, expected, mGetProcessPID, mKill

# Intentionally select non-existent PID (above 65535) just in case the mocking doesn't work properly.
@pytest.mark.parametrize("pidsToKill", [
    [],
    [1234567],
    [1234567, 1234568]
    ], ids = ["No PIDs", "One PID", "Multiple PIDs"])
def testKillingProcess(setupKillProcess, pidsToKill):
    """ Test killing the process identified by the executable. """
    executable, expected, mGetProcess, mKill = setupKillProcess

    mGetProcess.side_effect = [pidsToKill, []]

    # Perform the actual method that we want to test
    nKilled = executable.killExistingProcess()

    # Check the calls
    if len(pidsToKill) == 0:
        mKill.assert_not_called()
    else:
        for pid in pidsToKill:
            if len(pidsToKill) == 1:
                mKill.assert_called_once_with(pid, signal.SIGINT)
            else:
                mKill.assert_any_call(pid, signal.SIGINT)

    # Check that the number of processes
    assert nKilled == len(pidsToKill)

def testFailedKillingProces(setupKillProcess):
    """ Test for the various error modes when killing a process. """
    executable, expected, mGetProcess, mKill = setupKillProcess

    # Setup the PIDs to always return, such that it appears as if the kill didn't work.
    pidsToKill = [1234567]
    mGetProcess.side_effect = [pidsToKill, pidsToKill]

    with pytest.raises(RuntimeError) as exceptionInfo:
        # Call the actual method that we want to test
        executable.killExistingProcess()
    # We don't need to check the exact message.
    assert "found PIDs {PIDs} after killing the processes.".format(PIDs = pidsToKill) in exceptionInfo.value.args[0]

@pytest.fixture
def setupStartProcessWithLog(setupBasicExecutable, mocker):
    """ Setup required for testing startProcessWithLog.

    It mocks:

    - Writing a ConfigParser configuration
    - ``subprocess.Popen``
    - Opening files

    Returns:
        tuple: (mFile, mPopen, mConfigParserWrite) where ``mFile`` is the mock for opening a file, ``mPopen`` is the mock
            for ``subprocess.Popen(...)``, and ``mConfigParserWrite`` is the mock for writing a ``configparser`` config.
    """
    # For standard processes
    # Mock the subprocess command
    mPopen = mocker.MagicMock(return_value = "Fake value")
    mocker.patch("overwatch.base.deploy.subprocess.Popen", mPopen)
    # For supervisor processes
    # Mock write with the config parser
    mConfigParserWrite = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.ConfigParser.write", mConfigParserWrite)
    # Shared by both
    # Mock opening the log or config file
    mFile = mocker.mock_open()
    mocker.patch("overwatch.base.deploy.open", mFile)

    return mFile, mPopen, mConfigParserWrite

def testStandardStartProcessWithLogs(setupStartProcessWithLog, setupBasicExecutable):
    """ Tests for starting a process with logs in the standard manner ("Popen"). """
    # Setup mocks
    mFile, mPopen, mConfigParserWrite = setupStartProcessWithLog
    # Setup executable
    executable, expected = setupBasicExecutable
    executable.setup()

    # Execute
    process = executable.startProcessWithLog()

    # Check that it was called successfully
    mFile.assert_called_once_with("{}.log".format(expected.name), "w")
    mPopen.assert_called_once_with(expected.args, stderr = subprocess.STDOUT, stdout = mFile())

    # No need to actually mock up a subprocess.Popen class object.
    assert process == "Fake value"

def testSupervisorStartProcessWithLogs(setupStartProcessWithLog, setupBasicExecutable):
    """ Tests for starting a process with logs in supervisor. """
    # Setup mocks
    mFile, mPopen, mConfigParserWrite = setupStartProcessWithLog
    # Setup executable
    executable, expected = setupBasicExecutable
    executable.supervisor = True
    executable.setup()

    # Execute
    process = executable.startProcessWithLog()

    mFile.assert_called_once_with("supervisord.conf", "a")
    # We don't check the output itself because that would basically be testing ConfigParser, which isn't our goal.
    mConfigParserWrite.assert_called_once_with(mFile())

    assert process is None

@pytest.mark.parametrize("supervisor, runInBackground", [
    (False, False),
    (False, True),
    (True, False),
    ], ids = ["Standard process", "Standard process run in background", "Supervisor"])
@pytest.mark.parametrize("executeTask, shortExecutionTime", [
    (False, False),
    (True, False),
    (True, True)
    ], ids = ["No execute task", "Execute task", "Execute with short executable time"])
@pytest.mark.parametrize("forceRestart", [
    False,
    True,
    ], ids = ["No force restart", "Force restart"])
@pytest.mark.parametrize("returnProcessPID", [
    False,
    True,
    ], ids = ["Do not return process PID", "Return process PID"])
def testRunExecutable(setupBasicExecutable, setupStartProcessWithLog, supervisor, runInBackground, executeTask, shortExecutionTime, forceRestart, returnProcessPID, mocker):
    """ Test running an executable from start to finish.

    Note:
        Since this is an integration task, it is quite a bit more complicated than the other tests.
    """
    executable, expected = setupBasicExecutable
    # Set supervisor state first, as everything else effectively depends on this.
    executable.supervisor = supervisor
    executable.runInBackground = runInBackground
    # Set execution state.
    executable.executeTask = executeTask
    executable.shortExecutionTime = shortExecutionTime
    # Force restart.
    executable.config["forceRestart"] = forceRestart

    # Speed use the tests by avoiding actually sleeping.
    mSleep = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.time.sleep", mSleep)
    # Mock all of the relevant class methods
    mGetProcessPID = mocker.MagicMock(return_value = [1234567])
    # Ensure that we hit the branch where we do not force restart and we find no processes.
    if forceRestart is False:
        if returnProcessPID is True:
            # Continue returning a value as normal
            pass
        else:
            mGetProcessPID.return_value = None
            mGetProcessPID.side_effect = [[], [1234567]]
    mocker.patch("overwatch.base.deploy.executable.getProcessPID", mGetProcessPID)
    mKillExistingProcess = mocker.MagicMock(return_value = 1)
    mocker.patch("overwatch.base.deploy.executable.killExistingProcess", mKillExistingProcess)
    # Mocks relevant to startProcessWithLog
    mFile, mPopen, mConfigParserWrite = setupStartProcessWithLog

    # Run the executable to start the actual test
    result = executable.run()

    # We won't launch a process if executeTask is False or if we don't forceRestart
    # (since the mock returns PID values as if the process exists).
    expectedResult = False if (executeTask is False or (forceRestart is False and executeTask is False) or (forceRestart is False and returnProcessPID is True)) else True
    # Check the basic result
    assert result == expectedResult

    # Now check the details
    if result and runInBackground:
        assert executable.args[0] == "nohup"

def testRunExecutableFailure(setupBasicExecutable, setupStartProcessWithLog, mocker):
    """ Test failure of run executable when the process doesn't start. """
    # Ensure that the executable actually executes
    executable, expected = setupBasicExecutable
    executable.executeTask = True

    # Speed use the tests by avoiding actually sleeping.
    mSleep = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.time.sleep", mSleep)
    # Mock all of the relevant class methods
    mGetProcessPID = mocker.MagicMock(return_value = [])
    # Ensure that we hit the branch where we do not force restart and we find no processes.
    mocker.patch("overwatch.base.deploy.executable.getProcessPID", mGetProcessPID)
    mKillExistingProcess = mocker.MagicMock(return_value = 1)
    mocker.patch("overwatch.base.deploy.executable.killExistingProcess", mKillExistingProcess)
    # Mocks relevant to startProcessWithLog
    mFile, mPopen, mConfigParserWrite = setupStartProcessWithLog

    # Run the executable to start the actual test
    with pytest.raises(RuntimeError) as exceptionInfo:
        executable.run()
    assert "Failed to find the executed process" in exceptionInfo.value.args[0]

def testEnvironment(loggingMixin, mocker):
    """ Tests for configuring the environment. """
    receiverPath = os.path.join("receiver", "bin"),

    assert receiverPath in os.environ["PATh"]

def testSupervisorExecutable(loggingMixin, mocker):
    """ Tests for the supervisor executable. """
    executable = deploy.retrieveExecutable("supervisor", config = {})

    # Mock opening the file
    mFile = mocker.mock_open()
    mocker.patch("overwatch.base.deploy.open", mFile)
    # Mock write with the config parser
    mConfigParserWrite = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.ConfigParser.write", mConfigParserWrite)

    result = executable.setup()

    mFile.assert_called_once_with("supervisord.conf", "w+")
    mConfigParserWrite.assert_called_once_with(mFile())

    with pytest.raises(NotImplementedError) as exceptionInfo:
        executable.run()
    assert exceptionInfo.value.args[0] == "The supervisor executable should be run in multiple steps."

def testZMQReceiver(loggingMixin, mocker):
    """ Tests for the ZMQ receiver and the underlying exectuables. """
    config = {
        "enabled": True,
        "receiver": "EMC",
        "localPort": 123456,
        "dataPath": "data",
        "select": "",
        "additionalOptions": ["a", "b"],
        "tunnel": {
            "enabled": False,
            "hltPort": 234567,
            "address": "1.2.3.4",
            "port": 22,
            "username": "myUsername",
        },
    }
    executable = deploy.retrieveExecutable("zmqReceiver", config = config)

    # Show files as not existing, so they attempt to make the directory and file
    mPathExists = mocker.MagicMock(return_value = False)
    mocker.patch("overwatch.base.deploy.os.path.exists", mPathExists)
    # Don't actually create the directory
    mMakeDirs = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.os.makedirs", mMakeDirs)
    # Don't actually change the permissions
    mChmod = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.os.chmod", mChmod)
    # Prevent known_hosts from actually running
    mKnownHostsRun = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.sshKnownHosts.run", mKnownHostsRun)
    # Prevent autossh from actually running
    mAutosshRun = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.autossh.run", mAutosshRun)

    executable.setup()
    # We have to step through the setups because we mocker the run() methods
    executable.tunnel.setup()
    executable.tunnel.knownHosts.setup()

    # Check known hosts
    expectedKnownHostsArgs = [
        "ssh-keyscan",
        "-p {port}",
        "-H",
        "{address}",
    ]
    # It is formatted by the tunnel config, so be certain to use that here as an additional check.
    expectedKnownHostsArgs = [a.format(**config["tunnel"]) for a in expectedKnownHostsArgs]
    assert executable.tunnel.knownHosts.args == expectedKnownHostsArgs
    expectedKnownHostsLocation = os.path.expandvars(os.path.join("$HOME", ".ssh", "known_hosts").replace("\n", ""))
    expectedKnownHostsDir = os.path.dirname(expectedKnownHostsLocation)
    # Sanity check
    assert executable.tunnel.knownHosts.configFilename == expectedKnownHostsLocation
    # Check the setup calls
    mPathExists.assert_any_call(expectedKnownHostsLocation)
    mPathExists.assert_any_call(expectedKnownHostsDir)
    mMakeDirs.assert_called_once_with(expectedKnownHostsDir)
    mChmod.assert_called_once_with(expectedKnownHostsDir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    # Check autossh
    expectedTunnelArgs = [
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
    config["tunnel"]["localPort"] = config["localPort"]
    expectedTunnelArgs = [a.format(**config["tunnel"]) for a in expectedTunnelArgs]

    assert executable.tunnel.args == expectedTunnelArgs

    # Check zmqReceiver
    expectedArgs = [
        "zmqReceive",
        "--subsystem={receiver}",
        "--in=REQ>tcp://localhost:{localPort}",
        "--dataPath={dataPath}",
        "--verbose=1",
        "--sleep=60",
        "--timeout=100",
        "--select={select}",
    ]
    expectedArgs = [a.format(**config) for a in expectedArgs]
    expectedArgs.append(config["additionalOptions"])
    assert executable.args == expectedArgs

def testZODB(loggingMixin, mocker):
    """ Test for the ZODB executable. """
    config = {
        "address": "127.0.0.1",
        "port": 12345,
        "databasePath": "data/overwatch.fs",
    }
    executable = deploy.retrieveExecutable("zodb", config = config)

    # Mock opening the file
    mFile = mocker.mock_open()
    mocker.patch("overwatch.base.deploy.open", mFile)
    executable.setup()

    # Determine expected values
    expected = """
    <zeo>
        address {address}:{port}
    </zeo>

    <filestorage>
        path {databasePath}
    </filestorage>
    """
    # Fill in the values.
    expected = expected.format(**config)
    expected = inspect.cleandoc(expected)

    mFile.assert_called_once_with(executable.configFilename, "w")
    mFile().write.assert_called_once_with(expected)

@pytest.fixture
def setupOverwatchExecutable(loggingMixin):
    """ Setup basic Overwatch executable for testing.

    Args:
        None.
    Returns:
        tuple: (overwatchExecutable, expected) where ``overwatchExecutable`` (overwatchExecutable) is the
            created overwatch executable, and ``expected`` (dict) are the expected outputs.
    """
    expected = executableExpected(
        name = "testExecutable",
        description = "Basic executable for testing",
        args = ["exec", "arg1", "arg2"],
        config = {"additionalOptions": {"opt1": {"a", "b"}, "opt2": True}}
    )
    executable = deploy.overwatchExecutable(**expected._asdict())

    yield executable, expected

@pytest.mark.parametrize("existingConfig", [
        {},
        {"existingOption": True},
        {"opt2": False},
    ], ids = ["Config from scratch", "Appending to non-overlapping values", "Update overlapping values"])
def testWriteCustomOverwatchConfig(setupOverwatchExecutable, existingConfig, mocker):
    """ Test writing a custom Overwtach config. """
    # Basic setup
    executable, expected = setupOverwatchExecutable

    filename = "config.yaml"
    executable.configFilename = filename

    # Determine the expected result
    expectedConfig = existingConfig.copy()
    expectedConfig.update(expected.config["additionalOptions"])

    # Need to encode the exsting config with yaml so that we can input a string...
    inputStr = StringIO()
    yaml.dump(existingConfig, inputStr, default_flow_style = False)
    inputStr.seek(0)

    # Mock checking for a file
    mExists = mocker.MagicMock(return_value = (existingConfig != {}))
    mocker.patch("overwatch.base.deploy.os.path.exists", mExists)
    # Mock opening the file
    mFile = mocker.mock_open(read_data = inputStr.read())
    mocker.patch("overwatch.base.deploy.open", mFile)
    # Mock yaml.dump so we can check what was written.
    # (We can't check the write directly because dump writes many times!)
    mYaml = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.yaml.dump", mYaml)

    # Perform the actual setup
    executable.setup()

    # Should both read and write from here
    if existingConfig != {}:
        mFile.assert_any_call(filename, "r")
    mFile.assert_called_with(filename, "w")

    # Confirm that we've written the right information
    mYaml.assert_called_once_with(expectedConfig, mFile(), default_flow_style = False)

def testTwoOverwatchExecutablesWithCustomConfigs(loggingMixin):
    """ Test two Overwatch executables writing to the same config. """
    # We just write to a scratch area since it is faster and easier.
    # Otherwise, mocks need to be turned on and off, etc.
    directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "deployScratch")
    # Ensure that it exists. It won't by default because we don't store any files that are copied there in git.
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = os.path.join(directory, "config.yaml")

    # Processing and web app are selected randomly. Any overwatch executables would be fine.
    processingOptions = {"additionalOptions": {"processing": True}}
    processing = deploy.retrieveExecutable("processing", config = processingOptions)
    processing.configFilename = filename

    webAppOptions = {"uwsgi": {}, "additionalOptions": {"webApp": True}}
    webApp = deploy.retrieveExecutable("webApp", config = webAppOptions)
    webApp.configFilename = filename

    # Write both configurations
    processing.setup()
    webApp.setup()

    expected = processingOptions["additionalOptions"].copy()
    expected.update(webAppOptions["additionalOptions"])

    with open(filename, "r") as f:
        generatedConfig = deploy.yaml.load(f, Loader = yaml.SafeLoader)

    assert generatedConfig == expected

@pytest.mark.parametrize("executableType, config, expected", [
        ("dataTransfer", {"additionalOptions": {"testVal": True}},
         executableExpected(name = "dataTransfer",
                            description = "Overwatch receiver data transfer",
                            args = ["overwatchReceiverDataHandling"],
                            config = {"testVal": True})),
        ("processing", {},
         executableExpected(name = "processing",
                            description = "Overwatch processing",
                            args = ["overwatchProcessing"],
                            config = {})),
        ("webApp", {"uwsgi": {}},
         executableExpected(name = "webApp",
                            description = "Overwatch web app",
                            args = ["overwatchWebApp"],
                            config = {})),
        ("webApp", {"uwsgi": {"enabled" : True}},
         executableExpected(name = "webApp",
                            description = "Overwatch web app",
                            args = ["uwsgi", "--yaml", "data/config/webApp_uwsgi.yaml"],
                            config = {})),
        ("webApp", {"uwsgi": {"enabled" : True}, "nginx": {"enabled": True}},
         executableExpected(name = "webApp",
                            description = "Overwatch web app",
                            args = ["uwsgi", "--yaml", "data/config/webApp_uwsgi.yaml"],
                            config = {})),
        ("dqmReceiver", {"uwsgi": {}},
         executableExpected(name = "dqmReceiver",
                            description = "Overwatch DQM receiver",
                            args = ["overwatchDQMReciever"],
                            config = {})),
    ], ids = ["Data transfer", "Processing", "Web App", "Web App - uwsgi", "Web App - uwsgi + nginx", "DQM Receiver"])
def testOverwatchExecutableProperties(loggingMixin, executableType, config, expected, setupStartProcessWithLog, mocker):
    """ Integration test for the setup and properties of Overwatch based executables. """
    executable = deploy.retrieveExecutable(executableType, config = config)

    # Centralized setup for `uwsgi`. Defined here so we don't have to copy it in parametrize.
    uwsgi = False
    if "uwsgi" in executable.config and executable.config["uwsgi"].get("enabled", False):
        uwsgi = True
        executable.config["uwsgi"] = {
            "enabled": True,
            "module": "overwatch.webApp.run",
            "http-socket": "127.0.0.1:8850",
            "additionalOptions": {
                "chdir" : "myDir",
            }
        }
    # Centralized setup for `nginx`. Defined here so we don't have to copy it in parametrize.
    nginx = False
    if "nginx" in executable.config and executable.config["nginx"]["enabled"]:
        nginx = True
        executable.config["nginx"] = {
            "enabled": True,
            "webAppName": "webApp",
            "basePath": "data/config",
            "sitesPath": "sites-enabled",
            "configPath": "conf.d",
        }

    # Mocks relevant to startProcessWithLog
    mFile, mPopen, mConfigParserWrite = setupStartProcessWithLog
    # Mocks for checking the custom config
    mFile = mocker.mock_open()
    mocker.patch("overwatch.base.deploy.open", mFile)
    # Mock yaml.dump so we can check what was written.
    # (We can't check the write directly because dump writes many times!)
    mYaml = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.yaml.dump", mYaml)
    # Redirect nginx run to nginx setup so we don't have to mock all of run()
    mNginxRun = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.nginx.run", mNginxRun)

    # Perform task setup.
    executable.setup()
    # Special call to this function so we don't have to mock all of run(). We just want to run setup() to check the config.
    if nginx:
        executable.nginx.setup()

    # Confirm basic properties:
    assert executable.name == expected.name
    assert executable.description == expected.description
    assert executable.args == expected.args

    # Only check for a custom config if we've actually written one.
    if expected.config:
        mYaml.assert_called_once_with(expected.config, mFile(), default_flow_style = False)

    # Check for uwsgi config.
    if uwsgi:
        mFile.assert_any_call(expected.args[2], "w")
        # Effectively copied from the uwsgi config
        expectedConfig = {
            "vacuum": True,
            "stats": "/tmp/sockets/wsgi_{name}_stats.sock",
            "chdir": "myDir",
            "http-socket": "127.0.0.1:8850",
            "module": "overwatch.webApp.run",
            "callable": "app",
            "lazy-apps": True,
            "processes": 4,
            "threads": 2,
            "cheaper": 2,
            "master": True,
            "master-fifo": "/tmp/sockets/wsgiMasterFifo{name}",
        }
        # Format in the variables
        for k, v in iteritems(expectedConfig):
            if isinstance(v, str):
                expectedConfig[k] = v.format(name = "{name}_uwsgi".format(name = expected.name))
        expectedConfig = {"uwsgi" : expectedConfig}
        mYaml.assert_any_call(expectedConfig, mFile(), default_flow_style = False)

    # Check for nginx config.
    if nginx:
        expectedMainNginxConfig = """
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
        expectedMainNginxConfig = expectedMainNginxConfig % {"name": executable.config["nginx"]["webAppName"]}
        expectedMainNginxConfig = inspect.cleandoc(expectedMainNginxConfig)

        print(mFile.mock_calls)
        mFile.assert_any_call(os.path.join("data", "config", "sites-enabled", "webAppNginx.conf"), "w")
        mFile().write.assert_any_call(expectedMainNginxConfig)

        # We skip the gzip config contents because they're static
        mFile.assert_any_call(os.path.join("data", "config", "conf.d", "gzip.conf"), "w")

def testStartOverwatch(loggingMixin, mocker):
    """ Test for the main driver function. """

    assert False
