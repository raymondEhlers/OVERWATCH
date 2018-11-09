#/usr/bin/env python

""" Tests for the utilities module.

As of Oct 2018, It is not comprehensive, but should be continually improved as time permits.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

import pytest

import logging
import os
logger = logging.getLogger(__name__)

from overwatch.base import utilities

@pytest.mark.parametrize("filePath", [
    "",
    "data/Run123456/EMC"
], ids = ["No additional path", "Full file path"])
@pytest.mark.parametrize("filename, expectedTime", [
    ("hists.combined.1.1448388552.root", 1448388552),
    ("timeSlice.1448388310.1448388552.4bb7fb6d258fe195f50f6360b9ceabb653ba6cc4.root", 242),
    ("EMChists.2015_11_24_18_05_10.root", 1448384710),
], ids = ["Combined file", "Time slice", "Standard file"])
def testExtractTimeStampFromFilename(loggingMixin, filePath, filename, expectedTime):
    """ Tests for extracting the time stamp from a given filename. """
    filename = os.path.join(filePath, filename)
    time = utilities.extractTimeStampFromFilename(filename = filename)
    assert time == expectedTime

@pytest.mark.parametrize("fileExists", [
    False,
    True,
], ids = ["File doesn't exist", "File exists"])
def testRetrieveHLTModeFromStoredRunInfo(loggingMixin, fileExists, mocker):
    """ Tests for retrieving run information from a run info file. """
    # Setup
    expectedHLTMode = "C" if fileExists else "U"
    if fileExists:
        mOpen = mocker.mock_open()
        mocker.patch("overwatch.base.utilities.open", mOpen)
        mConfig = mocker.MagicMock(return_value = {"hltMode": "C"})
        mocker.patch("overwatch.base.utilities.yaml.load", mConfig)

    # Make the actual call
    runDirectory = os.path.join("data", "Run123")
    hltMode = utilities.retrieveHLTModeFromStoredRunInfo(runDirectory = runDirectory)

    # Check expected values.
    if fileExists:
        mOpen.assert_called_once_with(os.path.join(runDirectory, "runInfo.yaml"), "r")
    assert hltMode == expectedHLTMode

@pytest.mark.parametrize("fileExists", [
    False,
    True,
], ids = ["Run info file doesn't exist", "Run info file exists"])
@pytest.mark.parametrize("hltMode", [
    None,
    "C",
], ids = ["No HLT mode set", "HLT Mode C"])
def testWriteRunInfoToFile(loggingMixin, fileExists, hltMode, mocker):
    """ Tests for writing run info to file. """
    # Setup
    mOpen = mocker.mock_open()
    mocker.patch("overwatch.base.utilities.open", mOpen)
    # The file may or may not exist depending on (fileExists), but then the directory should
    # always exist (so we don't have to mock creating the directory as well).
    mExists = mocker.MagicMock(side_effect = [fileExists, True])
    mocker.patch("overwatch.base.utilities.os.path.exists", mExists)
    mConfig = mocker.MagicMock(return_value = {"hltMode": "C"})
    mocker.patch("overwatch.base.utilities.yaml.dump", mConfig)

    # Make the actual call
    runDirectory = os.path.join("data", "Run123")
    utilities.writeRunInfoToFile(runDirectory = runDirectory, hltMode = hltMode)

    # Check expected values.
    if fileExists is False:
        mOpen.assert_called_once_with(os.path.join(runDirectory, "runInfo.yaml"), "w")
        mConfig.assert_called_once_with({"hltMode": hltMode if hltMode else "U"}, mOpen())
    else:
        mOpen.assert_not_called()
        mConfig.assert_not_called()

