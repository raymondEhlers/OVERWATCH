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
    ("EMChists.2015_11_24_18_05_10.root", 1448388310),
], ids = ["Combined file", "Time slice", "Standard file"])
def testExtractTimeStampFromFilename(loggingMixin, filePath, filename, expectedTime):
    """ Tests for extracting the time stamp from a given filename. """
    filename = os.path.join(filePath, filename)
    time = utilities.extractTimeStampFromFilename(filename = filename)
    assert time == expectedTime
