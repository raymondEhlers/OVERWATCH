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

def checkTransferredFiles(source, destination, filenames):
    """ Helper function to check that files were successfully transferred based on their file contents.

    Args:
        source (str): Path to the source directory where the files are stored locally.
        destination (str): Path to the destination directory where the file are copied.
        filenames (list): Files that were copied and should be checked.
    Returns:
        None. Assertions are made in this function.
    """
    for filename in filenames:
        sourceFileContents = ""
        destinationFileContents = ""
        with open(os.path.join(source, filename), "r") as f:
            sourceFileContents = f.read()
        with open(os.path.join(destination, filename), "r") as f:
            destinationFileContents = f.read()

        # They shouldn't be empty, and they should be equal.
        assert sourceFileContents != "" and destinationFileContents != ""
        assert sourceFileContents == destinationFileContents

@pytest.mark.parametrize("transferFunction", [
        dataHandling.copyFilesToOverwatchSites,
        dataHandling.copyFilesToEOS,
    ], ids = ["Overwatch sites", "EOS"])
def testCopyFilesToOverwatchSites(loggingMixin, dataHandlingSetup, transferFunction):
    """ Test for copying files.

    For simplicity in testing, we simply copy the files locally.
    """
    directory, destination = dataHandlingSetup
    filenames = dataHandling.determineFilesToMove(directory = directory)
    # Remove existing files in the destination to ensure that rsync copies properly.
    # Otherwise, it will not copy any files, which will appear to fail, but only because
    # the destination file already exists.
    for f in filenames:
        filename = os.path.join(destination, f)
        if os.path.exists(filename):
            os.remove(os.path.join(destination, f))
    # Move files using rsync.
    failedFilenames = transferFunction(directory = directory,
                                       destination = destination,
                                       filenames = filenames)

    # Nothing should have failed here.
    assert failedFilenames == []

    # Check the copied file(s).
    # We currently have just one.
    checkTransferredFiles(source = directory,
                          destination = destination,
                          filenames = filenames)

@pytest.mark.slow
@pytest.mark.parametrize("transferFunction", [
        dataHandling.copyFilesToOverwatchSites,
        dataHandling.copyFilesToEOS,
    ], ids = ["Overwatch sites", "EOS"])
def testCopyFilesFailure(loggingMixin, dataHandlingSetup, transferFunction):
    """ Test failure of copying by providing invalid input files.

    This test is slow because it has to try the copy (but will eventually fail).
    """
    directory, destination = dataHandlingSetup
    filenames = dataHandling.determineFilesToMove(directory = directory)
    # We cannot just set an invalid destination because rsync will create that directory.
    filenames = [os.path.join("invalid") for f in filenames]
    failedFilenames = transferFunction(directory = directory,
                           destination = destination,
                           filenames = filenames)

    # All of the files should have failed.
    assert failedFilenames == filenames
