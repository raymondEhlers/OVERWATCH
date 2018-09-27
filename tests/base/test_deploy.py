#!/usr/bin/env python

""" Tests for the deploy module, which is used to configure and execute Overwatch scripts.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest
import os
import collections
import logging
logger = logging.getLogger(__name__)

from overwatch.base import deploy

def testWriteCustomConfig(loggingMixin):
    pass

@pytest.fixture
def setupExecutable():
    """ Fixture to setup an executable object. """
    pass

def testGetProcessPID(loggingMixin, setupExecutable):
    """ Test getting the PID identified by the exectuable properties. """
    pass

def testKillingProcess(loggingMixin, setupExecutable):
    """ Test killing the process identified by the executable. """
    pass

def testFailedKillingProces(loggingMixin, setupExecutable):
    """ Test for the various error modes when killing a process. """
    pass

overwatchExecutableResult = collections.namedtuple("overwatchExecutableResult", ["name", "description", "args", "config"])
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

