#!/usr/bin/env python

""" Tests for the deploy module, which is used to configure and execute Overwatch scripts.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest
import os
try:
    # For whatever reason, import StringIO from io doesn't behave nicely in python 2.
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import signal
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

    # Need to use the YAML from the deploy module to ensure that the constructor is loaded properly.
    config = deploy.yaml.load(s, Loader = yaml.SafeLoader)

    assert config["normalVar"] == 3
    # Should have no impact because it explicitly needs to be tagged (a `$` on it's own is not enough)
    assert config["normalWithDollarSign"] == "$ Hello World"
    assert config["environmentVar"] == os.environ["HOME"]
    # Should have no impact because there are no envrionment ars
    assert config["expandedWithoutVar"] == "Hello world"

def testRetrieveExecutable(loggingMixin):
    """ Tests for retrieving executables. """
    e = deploy.retrieveExecutable("zodb")
    assert e == deploy._available_executables["zodb"]

    with pytest.raises(KeyError) as exceptionInfo:
        e = deploy.retrieveExecutable("helloWorld")
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
    executable.supervisord = True
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
    executable.supervisord = supervisor
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
        ("dqmReceiver", {"uwsgi": {}},
         executableExpected(name = "dqmReceiver",
                            description = "Overwatch DQM receiver",
                            args = ["overwatchDQMReciever"],
                            config = {})),
    ], ids = ["Data transfer", "Processing", "Web App", "DQM Receiver"])
        #"Web App - uwsgi" , "Web App - uwsgi + nginx", "DQM Receiver - uwsgi", "DQM Receiver - uwsgi + nginx"])
def testOverwatchExecutableProperties(loggingMixin, executableType, config, expected, mocker):
    """ Test the properties of Overwatch based executables. """
    executable = deploy.retrieveExecutable(executableType)(config = config)

    # Check the custom config
    mFile = mocker.mock_open()
    mocker.patch("overwatch.base.deploy.open", mFile)
    # Mock yaml.dump so we can check what was written.
    # (We can't check the write directly because dump writes many times!)
    mYaml = mocker.MagicMock()
    mocker.patch("overwatch.base.deploy.yaml.dump", mYaml)

    # Perform task setup.
    executable.setup()

    assert executable.name == expected.name
    assert executable.description == expected.description
    assert executable.args == expected.args

    # Only check for a custom config if we've actually written one.
    if expected.config:
        mYaml.assert_called_once_with(expected.config, mFile(), default_flow_style = False)

