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
import collections
import logging
logger = logging.getLogger(__name__)

import ruamel.yaml as yaml

from overwatch.base import deploy

def testWriteCustomConfig(loggingMixin):
    pass

@pytest.fixture
def setupBasicExecutable(loggingMixin, mocker):
    """ Fixture to setup an executable object. """
    expected = {
        "name": "testExecutable",
        "description": "Basic exectuable for testing",
        "args": ["exec", "arg1", "arg2"],
        "config": {},
    }
    executable = deploy.executable(**expected)

    return executable, expected

def testGetProcessPID(setupBasicExecutable):
    """ Test getting the PID identified by the exectuable properties. """
    pass

def testKillingProcess(setupBasicExecutable):
    """ Test killing the process identified by the executable. """
    pass

def testFailedKillingProces(setupBasicExecutable):
    """ Test for the various error modes when killing a process. """
    pass


#: Simple named tuple to contain the execution result.
overwatchExecutableResult = collections.namedtuple("overwatchExecutableResult", ["name", "description", "args", "config"])

@pytest.fixture
def setupOverwatchExecutable(loggingMixin):
    """ Setup basic Overwatch executable for testing.

    Args:
        None.
    Returns:
        tuple: (overwatchExecutable, expected) where ``overwatchExecutable`` (overwatchExecutable) is the
            created overwatch executable, and ``expected`` (dict) are the expected outputs.
    """
    expected = overwatchExecutableResult(
        name = "testExecutable",
        description = "Basic exectuable for testing",
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
    executable, expected = setupOverwatchExecutable

    filename = "config.yaml"
    executable.filename = filename

    # Determine the expected result
    expectedConfig = existingConfig.copy()
    expectedConfig.update(expected.config["additionalOptions"])

    # Need to encode the exsting config with yaml so that we can input a string...
    inputStr = StringIO()
    yaml.dump(existingConfig, inputStr, default_flow_style = False)
    inputStr.seek(0)

    # Mock checking for a file
    mExists = mocker.MagicMock(return_value = (existingConfig != {}))
    mocker.patch("os.path.exists", mExists)
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

    # Necessary to ensure that profiling works (it seems that it runs before all mocks are cleared)
    # Probably something to do with mocking open
    mocker.stopall()

@pytest.mark.parametrize("executableType, config, expected", [
        ("dataTransfer", {},
         overwatchExecutableResult(name = "dataTransfer",
                                   description = "Overwatch receiver data transfer",
                                   args = ["overwatchReceiverDataHandling"],
                                   config = {})),
        ("processing", {},
         overwatchExecutableResult(name = "processing",
                                   description = "Overwatch processing",
                                   args = ["overwatchProcessing"],
                                   config = {})),
        ("webApp", {"uwsgi": {}},
         overwatchExecutableResult(name = "webApp",
                                   description = "Overwatch web app",
                                   args = ["overwatchWebApp"],
                                   config = {})),
        ("dqmReceiver", {"uwsgi": {}},
         overwatchExecutableResult(name = "dqmReceiver",
                                   description = "Overwatch DQM receiver",
                                   args = ["overwatchDQMReciever"],
                                   config = {})),
    ], ids = ["Data transfer", "Processing", "Web App", "DQM Receiver"])
        #"Web App - uwsgi" , "Web App - uwsgi + nginx", "DQM Receiver - uwsgi", "DQM Receiver - uwsgi + nginx"])
def testDataTransferExectuable(loggingMixin, executableType, config, expected):
    """ Test the properties of Overwatch based exectuables. """
    executable = deploy.retrieveExecutable(executableType)(config = config)

    # Perform task setup.
    executable.setup()

    assert executable.name == expected.name
    assert executable.description == expected.description
    assert executable.args == expected.args

    # TODO: Check custom config!

