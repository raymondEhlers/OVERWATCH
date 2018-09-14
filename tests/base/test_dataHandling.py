#!/usr/bin/env python

""" Tests for the data handling module.

Note that these tests are not quite ideal, as they rely on the default implementation
for the configuration and modules (which can change), but using this implementation
takes much less time than mocking objects. Note that these tests modify the parameters
of the ``dataHandling`` module since it is slightly easier here than through a ``config.yaml``
which we would need to rely on being in the proper location.

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

    Note:
        We cleanup any possible transferred files stored at ``destination/filename`` after running
        the test.

    Note:
        We modify some of the configuration parameters of the ``dataHandling`` module to simplify testing.
        However, this means that those values are permanently changed for that module during testing!

    Args:
        None.
    Yields:
        tuple: (directory, destination) where directory (str) is the path to the data handling
            test files directory, and destination (str) is the path to the data handling test files
            copy destination directory.
    """
    directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dataHandlingTestFiles")
    destination = os.path.join(directory, "destination")
    # Ensure that it exists. It won't by default because we don't store any files that are copied there in git.
    if not os.path.exists(destination):
        os.makedirs(destination)
    filenames = dataHandling.determineFilesToMove(directory = directory)

    # Setup the properties of the module appropriately for testing.
    # debug is to avoid deleting files unintentionally.
    dataHandling.parameters["debug"] = True
    dataHandling.parameters["receiverData"] = directory
    dataHandling.parameters["receiverDataTempStorage"] = os.path.join(directory, "tempStorage")
    # Set the site parameters
    dataHandling.parameters["dataTransferLocations"] = {
        "rsync" : destination,
        "EOS" : destination,
    }

    yield (directory, destination, filenames)

    # Cleanup transferred files to ensure that each test is independent.
    for f in filenames:
        path = os.path.join(destination, f)
        if os.path.exists(path):
            os.remove(path)

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

def testRetryDecorator(loggingMixin, mocker):
    """ Test the retry decorator to ensure that it is retried as many times as expected. """
    # Mock an object so we can count how often it is called.
    # We set the return value to be false to ensure that it is retried.
    m = mocker.MagicMock(return_value = False)
    # Shorter delay to save some time!
    testFunc = dataHandling.retry(tries = 2, delay = 0.5)(m)
    arg = "hello"
    testFunc(arg)
    # Since it was retried twice, it should have been called three times (failed the first time,
    # and then retried two more times).
    assert m.call_count == 3
    # The call signature won't vary for each call.
    # This is better than ``assert_has_calls`` here because in this case, we can actually
    # check that the calls occurred with a precise number and signature.
    assert m.mock_calls == [mocker.call(arg), mocker.call(arg), mocker.call(arg)]

def testDetermineFilesToMove(loggingMixin, dataHandlingSetup):
    """ Test for enumerating the files that should be transferred. """
    directory, destination, filenames = dataHandlingSetup

    assert filenames == ["accepted.root"]

@pytest.mark.parametrize("transferFunction", [
        dataHandling.copyFilesToOverwatchSites,
        dataHandling.copyFilesToEOS,
    ], ids = ["Overwatch sites", "EOS"])
def testCopyFilesToOverwatchSites(loggingMixin, dataHandlingSetup, transferFunction):
    """ Test for copying files.

    For simplicity in testing, we simply copy the files locally.
    """
    directory, destination, filenames = dataHandlingSetup
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
    directory, destination, filenames = dataHandlingSetup
    # We cannot just set an invalid destination because rsync will create that directory.
    filenames = [os.path.join("invalid", f) for f in filenames]
    failedFilenames = transferFunction(directory = directory,
                           destination = destination,
                           filenames = filenames)

    # All of the files should have failed.
    assert failedFilenames == filenames

def testProcessReceivedFiles(loggingMixin, dataHandlingSetup):
    """ Test the process received files driver function. """
    directory, destination, filenames = dataHandlingSetup
    (successfullyTransferred, failedFilenames) = dataHandling.processReceivedFiles()

    # If everything works, all files should be transferred and none should have failed.
    for siteName, failed in iteritems(failedFilenames):
        assert failed == []

    assert successfullyTransferred == filenames
    checkTransferredFiles(source = directory,
                          destination = destination,
                          filenames = filenames)

def testProcessReceivedFilesFailure(loggingMixin, dataHandlingSetup, mocker):
    """ Test the process received files driver function when transferring files fail. """
    directory, destination, filenames = dataHandlingSetup
    # Mock the transfer functions so this test runs faster and so we can return the filenames as if they
    # failed without running into trouble with our copy method (which would otherwise be unable to find
    # the files to copy).
    # NOTE: We cannot directly mock ``determineFilesToMove`` to return invalid files because it will break
    #       the copy methods later. And we cannot give a non-existent destination because rsync will just
    #       create the directory. Thus, mocking the initial transfer functions to appear as if they failed
    #       seems to be our best option. Plus, we don't have to wait for the retries, so it's much faster!
    mocker.patch("overwatch.base.dataHandling.copyFilesToOverwatchSites", return_value = filenames)
    mocker.patch("overwatch.base.dataHandling.copyFilesToEOS", return_value = filenames)
    (successfullyTransferred, failedFilenames) = dataHandling.processReceivedFiles()

    # Everything should fail to transfer
    assert successfullyTransferred == []
    # Check that the files that failed to transfer were successfully copied to the location where
    # they will be checked and moved later.
    for siteName, failed in iteritems(failedFilenames):
        assert failed == filenames
        checkTransferredFiles(source = directory,
                              destination = os.path.join(dataHandling.parameters["receiverDataTempStorage"], siteName),
                              filenames = filenames)

