#!/usr/bin/env python

""" Tests for the replay module, which replays already processed data.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest

import copy
import os
import logging
logger = logging.getLogger(__name__)

from overwatch.base import replay

def setupRetrieveHLTModeMock(hltMode, mocker):
    """ Helper function to mock the HLT mode which is extracted for a run.

    This is all just for convenience so we don't have to create the run information files.

    Args:
        hltMode (str): A valid HLT mode.
        mocker (mocker): The mock object from ``pytest-mock`` to be used in mocking the object.
    Returns:
        MagicMock: The HLT mode mock.
    """
    # Mock retrieving the HLT mode for implicitly
    mHLTMode = mocker.MagicMock(return_value = hltMode)
    mocker.patch("overwatch.base.utilities.retrieveHLTModeFromStoredRunInfo", mHLTMode)
    return mHLTMode

@pytest.mark.parametrize("hltMode", [
    "C",
    "U",
], ids = ["HLT Mode C", "HLT Mode U"])
def testConvertProcessedOverwatchNameToUnprocessed(loggingMixin, mocker, hltMode):
    """ Test for converting a processed Overwatch name into an unprocessed name.

    The parametrization may not be so helpful or meaningful here, but I've included it for good measure.
    """
    # Setup expected values
    expectedName = "EMChistos_300005_{hltMode}_2015_11_24_18_05_10.root".format(hltMode = hltMode)
    mHLTMode = setupRetrieveHLTModeMock(hltMode = hltMode, mocker = mocker)

    # Determine inputs
    name = "EMChists.2015_11_24_18_05_10.root"
    dirPrefix = os.path.join("data", "Run300005", "EMC")

    # Make the actual call
    name = replay.convertProcessedOverwatchNameToUnprocessed(dirPrefix = dirPrefix, name = name)

    # Check the expected values
    mHLTMode.assert_called_once_with(runDirectory = os.path.dirname(dirPrefix))
    assert name == expectedName

@pytest.mark.parametrize("hltMode", [
    "C",
    "U",
], ids = ["HLT Mode C", "HLT Mode U"])
@pytest.mark.parametrize("baseDir", [
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "replayData"),
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "replayData", "Run123"),
], ids = ["Standard base dir", "Base dir in run directory"])
def testAvailableFiles(loggingMixin, mocker, hltMode, baseDir):
    """ Test determining which files are available for replay.

    The ``hltMode`` parametrization may not be so helpful or meaningful here, but I've included it
    for good measure. The ``baseDir`` parametrization should give the same result in either case, but it's
    included to ensure that the ``baseDir`` is relatively position independent (and therefore will work will all
    runs, or with a single specified run).
    """
    # Determine expected values
    expectedSourceFilenames = [
        "EMChists.2015_11_24_18_05_10.root",
        "EMChists.2015_11_24_18_06_10.root",
        "EMChists.2015_11_24_18_07_10.root",
        "EMChists.2015_11_24_18_08_11.root",
        "hists.combined.1.1448388552.root",
        "EMChists.2015_11_24_18_09_12.root",
        "HLThists.2015_11_24_18_05_10.root",
        "HLThists.2015_11_24_18_06_10.root",
        "HLThists.2015_11_24_18_07_10.root",
        "HLThists.2015_11_24_18_08_11.root",
        "hists.combined.1.1448388552.root",
        "HLThists.2015_11_24_18_09_12.root",
    ]
    # These are the destination file names
    expectedDestinationNames = [
        "EMChistos_123_{hltMode}_2015_11_24_18_05_10.root",
        "EMChistos_123_{hltMode}_2015_11_24_18_06_10.root",
        "EMChistos_123_{hltMode}_2015_11_24_18_07_10.root",
        "EMChistos_123_{hltMode}_2015_11_24_18_08_11.root",
        "hists.combined.1.1448388552.root",
        "EMChistos_123_{hltMode}_2015_11_24_18_09_12.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_05_10.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_06_10.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_07_10.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_08_11.root",
        "hists.combined.1.1448388552.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_09_12.root",
    ]
    expectedDestinationNames = [f.format(hltMode = hltMode) for f in expectedDestinationNames]
    # These files shouldn't be available because they are empty.
    expectedNotToBeDestinationNames = [
        "EMChistos_123_{hltMode}_2015_11_24_18_04_10.root",
        "HLThistos_123_{hltMode}_2015_11_24_18_04_10.root",
    ]
    expectedNotToBeDestinationNames = [f.format(hltMode = hltMode) for f in expectedNotToBeDestinationNames]
    setupRetrieveHLTModeMock(hltMode = hltMode, mocker = mocker)

    # Make the actual call. By calling list, it forces it to iterate and provide all files.
    availableFiles = list(replay.availableFiles(baseDir = baseDir))
    sourceFilenames = [os.path.split(f[0])[1] for f in availableFiles]
    names = [f[1] for f in availableFiles]

    # First check the source files
    # Use a set to check the files because the order doesn't appear to be stable on different systems.
    assert set(sourceFilenames) == set(expectedSourceFilenames)
    # Then check the destination names
    assert set(names) == set(expectedDestinationNames)
    assert not set(expectedNotToBeDestinationNames).issubset(names)

def testAvailableFilesWithUnprocessedFiles(loggingMixin, mocker):
    """ Test replaying data which hasn't already been processed.

    This is particularly used for replaying data for transfer to other Overwatch sites and EOS.
    """
    # Setup
    hltMode = "C"
    baseDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "replayUnprocessedData")
    expectedSourceFilenames = [
        "EMChistos_123_C_2015_11_24_18_05_10.root",
        "EMChistos_123_C_2015_11_24_18_06_10.root",
        "EMChistos_123_C_2015_11_24_18_07_10.root",
        "EMChistos_123_C_2015_11_24_18_08_11.root",
        "EMChistos_123_C_2015_11_24_18_09_12.root",
        "HLThistos_123_C_2015_11_24_18_05_10.root",
        "HLThistos_123_C_2015_11_24_18_06_10.root",
        "HLThistos_123_C_2015_11_24_18_07_10.root",
        "HLThistos_123_C_2015_11_24_18_08_11.root",
        "HLThistos_123_C_2015_11_24_18_09_12.root",
    ]
    # These files shouldn't be available because they are empty.
    expectedNotToBeDestinationNames = [
        "EMChistos_123_C_2015_11_24_18_04_10.root",
        "HLThistos_123_C_2015_11_24_18_04_10.root",
    ]
    expectedDestinationNames = copy.deepcopy(expectedSourceFilenames)
    setupRetrieveHLTModeMock(hltMode = hltMode, mocker = mocker)

    # Make the actual call. By calling list, it forces it to iterate and provide all files.
    availableFiles = list(replay.availableFiles(baseDir = baseDir))
    sourceFilenames = [os.path.split(f[0])[1] for f in availableFiles]
    names = [f[1] for f in availableFiles]

    # First check the source files
    # Use a set to check the files because the order doesn't appear to be stable on different systems.
    assert set(sourceFilenames) == set(expectedSourceFilenames)
    # Then check the destination names
    assert set(names) == set(expectedDestinationNames)
    assert not set(expectedNotToBeDestinationNames).issubset(names)

@pytest.mark.parametrize("nMaxFiles", [
    3,
    30,
], ids = ["Move 3 files", "Try to move 30, but fewer are available"])
def testMoveFiles(loggingMixin, mocker, nMaxFiles):
    """ Test the driver function to move files.

    This test takes advantage of the files created for ``testAvailableFiles(...)``.
    """
    # Setup
    hltMode = "C"
    # Mocks
    # Mock for moving files
    mMove = mocker.MagicMock()
    mocker.patch("overwatch.base.replay.shutil.move", mMove)
    # Mock for retrieving the HLT mode
    setupRetrieveHLTModeMock(hltMode = hltMode, mocker = mocker)

    fileLocation = os.path.dirname(os.path.realpath(__file__))
    baseDir = os.path.join(fileLocation, "replayData")
    destinationDir = os.path.join(fileLocation, "destinationDir")
    nMoved = replay.moveFiles(baseDir = baseDir,
                              destinationDir = destinationDir,
                              nMaxFiles = nMaxFiles)

    # Determine expected values
    availableFiles = list(replay.availableFiles(baseDir = baseDir))
    availableFiles = [(source, os.path.join(destinationDir, name)) for source, name in availableFiles if "combined" not in source]

    # If there aren't enough files, don't check that we've transferred as many as requested because
    # it won't be possible.
    if not len(availableFiles) < nMaxFiles:
        assert nMoved == nMaxFiles

    # For each call, we expand each tuple of args.
    assert mMove.mock_calls == [mocker.call(*args) for args in availableFiles[:nMaxFiles]]

