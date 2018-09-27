#!/usr/bin/env python

""" Tests for the deploy module, which is used to configure and execute Overwatch scripts.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest
import os
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

    # First write the existing config (may be empty)
    directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "deployConfig")
    # Ensure that it exists.
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = os.path.join(directory, "config.yaml")

    yield executable, expected, filename

    # Cleanup the config (if it was created) so we can start clean for the next test.
    if os.path.exists(filename):
        os.remove(filename)

@pytest.mark.parametrize("existingConfig", [
        {},
        {"existingOption": True},
        {"opt2": False},
    ], ids = ["Config from scratch", "Appending to non-overlapping values", "Update overlapping values"])
def testWriteCustomOverwatchConfig(setupOverwatchExecutable, existingConfig):
    """ Test writing a custom Overwtach config. """
    executable, expected, configFilename = setupOverwatchExecutable

    # Write the existing config
    if existingConfig:
        with open(configFilename, "w") as f:
            yaml.dump(existingConfig, f, default_flow_style = False)

    executable.filename = configFilename

    # Run the setup to write the configuration
    executable.setup()

    # Read in the config to check the result
    with open(configFilename, "r") as f:
        customConfig = yaml.load(f, Loader = yaml.SafeLoader)

    # Determine the expected result
    expectedConfig = existingConfig.copy()
    expectedConfig.update(expected.config["additionalOptions"])

    assert customConfig == expectedConfig

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

