#!/usr/bin/env python

""" Tests for the data handling module.

Note that these tests are not quite ideal, as they rely on the default implementation
for the configuration and modules (which can change), but using this implementation
takes much less time than mocking objects.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

from future.utils import iteritems

import pytest
import os
import logging
logger = logging.getLogger(__name__)

import overwatch.base.dataHandling as dataHandling

@pytest.fixture
def dataHandlingSetup():
    """ Basic variables for testing the data handling module.

    Args:
        None.
    Returns:
        tuple: (directory, destination) where directory (str) is the path to the data handling
            test files directory, and destination (str) is the path to the data handling test files
            copy destination directory.
    """
    directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dataHandlingTestFiles")
    destination = os.path.join(directory, "destination")
    # Ensure that it exists. It won't by default because we don't store any files that are copied there in git.
    if not os.path.exists(destination):
        os.makedirs(destination)

    return (directory, destination)

def testDetermineFilesToMove(loggingMixin, dataHandlingSetup):
    """ Test for enumerating the files that should be transferred. """
    directory, destination = dataHandlingSetup
    filenames = dataHandling.determineFilesToMove(directory = directory)

    assert filenames == ["accepted.root"]

def testCopyFilesToEOS(loggingMixin, dataHandlingSetup):
    """ Test the driver function for copying files to EOS.

    For simpliciy, we simply copy the files locally.
    """
    directory, destination = dataHandlingSetup
    filenames = dataHandling.determineFilesToMove(directory = directory)
    failedFilenames = dataHandling.copyFilesToEOS(directory = directory,
                                                  eosDirectory = destination,
                                                  filenames = filenames)

    # Nothing should have failed here.
    assert failedFilenames == []

    # Check the copied file(s).
    # We currently have just one.
    for filename in filenames:
        sourceFileContents = ""
        destinationFileContents = ""
        with open(os.path.join(directory, filename), "r") as f:
            sourceFileContents = f.read()
        with open(os.path.join(destination, filename), "r") as f:
            destinationFileContents = f.read()

        # They shouldn't be empty, and they should be equal.
        assert sourceFileContents != "" and destinationFileContents != ""
        assert sourceFileContents == destinationFileContents

@pytest.mark.slow
def testCopyFilesToEOSFailure(loggingMixin, dataHandlingSetup):
    """ Test failure of copying by providing an invalid destination. 

    This test is slow because it has to try the copy (but will eventually fail).
    """

    directory, destination = dataHandlingSetup
    filenames = dataHandling.determineFilesToMove(directory = directory)
    failedFilenames = dataHandling.copyFilesToEOS(directory = directory,
                                                  eosDirectory = "invalid",
                                                  filenames = filenames)

    # All of the files should have failed.
    assert failedFilenames == filenames
