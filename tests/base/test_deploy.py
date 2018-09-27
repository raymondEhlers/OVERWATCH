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

overwatchExecutableResult = collections.namedtuple("overwatchExecutableResult", ["name", "description", "args"])
@pytest.mark.parametrize("executableType, expected", [
        ("dataTransfer", overwatchExecutableResult(name = "dataTransfer",
                                                   description = "Overwatch receiver data transfer",
                                                   args = ["overwatchReceiverDataHandling"])),
        ("processing", overwatchExecutableResult(name = "processing",
                                                 description = "Overwatch processing",
                                                 args = ["overwatchProcessing"])),
        #("webApp", overwatchExecutableResult(name = "webApp",
        #                                         description = "Overwatch web app",
        #                                         args = ["overwatchWebApp"])),
    ], ids = ["Data transfer", "Processing",])
        #"Web App", "Web App - uwsgi" , "Web App - uwsgi + nginx", "DQM Receiver"])
def testDataTransferExectuable(loggingMixin, executableType, expected):
    """ Test the properties of Overwatch based exectuables. """
    executable = deploy.retrieveExecutable(executableType)(config = {})

    # Perform task setup.
    executable.setup()

    assert executable.name == expected.name
    assert executable.description == expected.description
    assert executable.args == expected.args

    # TODO: Check custom config!

