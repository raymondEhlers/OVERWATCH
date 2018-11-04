#!/usr/bin/env python

""" Tests for the replay module, which replays already processed data.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest

import logging
import os
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
def testAvailableFiles(loggingMixin, mocker, hltMode):
    """ Test determining which files are available for replay.

    The parametrization may not be so helpful or meaningful here, but I've included it for good measure.
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

    baseDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "replayData")
    # Make the actual call. By calling list, it forces it to iterate and provide all files.
    availableFiles = list(replay.availableFiles(baseDir = baseDir))
    sourceFilenames = [os.path.split(f[0])[1] for f in availableFiles]
    names = [f[1] for f in availableFiles]

    # First check the source files
    assert sourceFilenames == expectedSourceFilenames
    # Then check the destination names
    assert names == expectedDestinationNames
    assert not set(expectedNotToBeDestinationNames).issubset(names)

