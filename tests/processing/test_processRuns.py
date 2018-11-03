#!/usr/bin/env python

""" Tests for the process runs module.

The process runs module is quite complicated (and probably is due for a refactor), so only some functionality is
tested here. Due to the nature of the module, these tests are more or less integration tests.

.. code-author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
"""

from future.utils import itervalues

import pytest

from BTrees.OOBTree import OOBTree
import copy
import collections
import logging
import os
logger = logging.getLogger(__name__)

from overwatch.base import utilities
from overwatch.processing import processRuns
from overwatch.processing import processingClasses

@pytest.fixture
def setupNewSubsystemsFromMovedFileInfo(loggingMixin, mocker):
    """ Setup for testing create new runs and subsystems based on moved file information. """
    # Ensure that processing clasess doesn't actually create any files or folders...
    mocker.patch("overwatch.processing.processingClasses.os.makedirs")

    # Set the relevant subsystems
    # We want the TPC to use HLT subsystem files.
    subsystems = ["EMC", "HLT", "TPC"]
    processRuns.processingParameters["subsystemList"] = subsystems

    runDir = "Run123"
    hltMode = "C"
    runDict = {
        runDir: {
            "hltMode": hltMode,
            "HLT": ["HLThists.2015_11_24_18_05_10.root", "HLThists.2015_11_24_18_09_12.root"],
            "EMC": ["EMChists.2015_11_24_18_05_12.root", "EMChists.2015_11_24_18_09_14.root"],
        }
    }
    # Same as the runDict above, but with an additional set of files.
    additionalRunDict = {
        runDir: {
            "hltMode": hltMode,
            "HLT": ["HLThists.2015_11_24_19_05_10.root", "HLThists.2015_11_24_19_09_12.root"],
            "EMC": ["EMChists.2015_11_24_19_05_11.root", "EMChists.2015_11_24_19_09_13.root"],
        }
    }

    # Ensure we don't create random directories
    mocker.patch("overwatch.processing.processingClasses.os.path.exists")
    # Create the runs container
    runs = OOBTree()
    runs.update({runDir: processingClasses.runContainer(runDir = runDir, fileMode = True, hltMode = hltMode)})
    # Add some subsystems
    runs[runDir].subsystems

    return runs, runDir, runDict, additionalRunDict, subsystems

expectedSubsystemValues_ = collections.namedtuple("expectedSubsystem", ["subsystem", "fileLocationSubsystem", "filenames", "showRootFiles", "startOfRun", "endOfRun"])
# This full class definition only exists to get the right docstring definition.
# ``__slots__`` is necessary to keep the namedtuple properties
# See: https://stackoverflow.com/a/1606478
class expectedSubsystemValues(expectedSubsystemValues_):
    """ Contains expected subsystem values.

    This basically exists for convenience in passing values around.

    Note:
        All values other than the subsystem name contain the expected values.

    Args:
        subsystem (str): Three letter subsystem name.
        fileLocationSubsystem (str): Three letter subsystem name where the subsystem files are stored.
        filenames (list): Filenames sorted by the time in the names (but without the base path).
        showRootFiles (bool): True if the root files are to be shown.
        startOfRun (int): Unix time for SOR.
        endOfRun (int): Unix time for EOR.
    """
    __slots__ = ()

def determineExpectedValues(runDict, runDir, subsystem):
    """ Determine the expected values based on the selected subsystem.

    Args:
        expectedRunDict (dict): Dict following the runDict format which contains the input values.
        runDir (str): Run directory name (ex. "Run123").
        subsystem (str): Three letter subsystem name.
    Returns:
        expectedSubsystemValues: Contains the expected subsystem values.
    """
    expectedFileLocationSubsystem = subsystem if runDict[runDir].get(subsystem, False) else "HLT"
    expectedFilenames = runDict[runDir].get(expectedFileLocationSubsystem)
    expectedShowRootFiles = subsystem in processRuns.processingParameters["subsystemsWithRootFilesToShow"]
    expectedFilenamesSorted = sorted(expectedFilenames)
    expectedStartOfRun = utilities.extractTimeStampFromFilename(expectedFilenamesSorted[0])
    expectedEndOfRun = utilities.extractTimeStampFromFilename(expectedFilenamesSorted[-1])

    return expectedSubsystemValues(subsystem = subsystem,
                                   fileLocationSubsystem = expectedFileLocationSubsystem,
                                   filenames = expectedFilenamesSorted,
                                   showRootFiles = expectedShowRootFiles,
                                   startOfRun = expectedStartOfRun,
                                   endOfRun = expectedEndOfRun)

def checkCreatedSubsystem(createdSubsystem, expectedSubsystem):
    """ Helper function to check subsystem properties against expected values.

    Args:
        createdSubsystem (subsystemContainer): The created subsystem to check.
        expectedSubsystem (expectedSubsystemValues): The corresponding expected subsystem values.
    Returns:
        bool: True if all assertions passed (which is implicitly true if we get to the end of the function).
    """
    # Ensure that we've determine the file location subsystem properly.
    assert createdSubsystem.fileLocationSubsystem == expectedSubsystem.fileLocationSubsystem
    # Check keys first.
    assert list(createdSubsystem.files) == [utilities.extractTimeStampFromFilename(filename) for filename in expectedSubsystem.filenames]
    # Then check filenames themselves.
    assert [fileCont.filename for fileCont in itervalues(createdSubsystem.files)] == [os.path.join(createdSubsystem.baseDir, filename) for filename in expectedSubsystem.filenames]
    # Check the start and end times
    assert createdSubsystem.startOfRun == expectedSubsystem.startOfRun
    assert createdSubsystem.endOfRun == expectedSubsystem.endOfRun
    # New files are added.
    assert createdSubsystem.newFile is True
    # Check whether root files will be shown.
    assert createdSubsystem.showRootFiles is expectedSubsystem.showRootFiles

    return True

@pytest.mark.parametrize("subsystem", [
    "EMC",
    "HLT",
    "TPC",
], ids = ["EMC", "HLT", "TPC"])
def testCreateNewSubsystemFromMovedFilesInformation(subsystem, setupNewSubsystemsFromMovedFileInfo):
    """ Tests for creating a new subsystem based on moved file information. """
    runs, runDir, runDict, additionalRunDict, subsystems = setupNewSubsystemsFromMovedFileInfo

    # Determine expected values.
    # We don't enumerate them in the parametrize because we would have to repeat values many times.
    # Instead, we just determine them here.
    expectedSubsystem = determineExpectedValues(runDict = runDict,
                                                runDir = runDir,
                                                subsystem = subsystem)

    # Create the subsystem
    # There is no return value because runs is modified.
    processRuns.createNewSubsystemFromMovedFilesInformation(runs = runs,
                                                            subsystem = subsystem,
                                                            runDict = runDict,
                                                            runDir = runDir)

    assert list(runs[runDir].subsystems) == [subsystem]
    createdSubsystem = runs[runDir].subsystems[subsystem]
    # Assertions are inside of this function.
    assert checkCreatedSubsystem(createdSubsystem, expectedSubsystem) is True

def checkAllCreatedSubsystems(subsystems, expectedRunDict, runDir, runs):
    """ Helper function to check all created subsystems against a set of expected run dict information.

    This leverages ``checkCreatedSubsystem(...)``, but it checks all given subsystems.

    Args:
        subsystems (list): List of three letter subsystems names to check.
        expectedRunDict (dict): Dict following the runDict format which contains the information expected in the
            ``subsystemContainer`` objects.
        runDir (str): Run directory name (ex. "Run123").
        runs (dict): Dictionary containing the ``runContainer`` objects, as a stand-in for the full database.
    Returns:
        bool: True if all assertions passed (which is implicitly true if we get to the end of the function).
    """
    # Check the run properties before going the subsystems
    assert runs[runDir].hltMode == expectedRunDict[runDir]["hltMode"]
    # Now check the subsystems.
    for subsystem in subsystems:
        # Determine expected values for a particular subsystem
        expectedSubsystem = determineExpectedValues(runDict = expectedRunDict,
                                                    runDir = runDir,
                                                    subsystem = subsystem)
        createdSubsystem = runs[runDir].subsystems[subsystem]
        # Check the actual values
        assert checkCreatedSubsystem(createdSubsystem, expectedSubsystem)

    return True

@pytest.mark.parametrize("useExistingRunContainer", [
    False,
    True,
], ids = ["Do not use existing run container", "Use existing run container"])
def testProcessMovedFilesWithExistingSubsystems(setupNewSubsystemsFromMovedFileInfo, useExistingRunContainer):
    """ Test to create new subsystems based on moved file information.

    Based on the parameterization, it will either use the existing run or create a new one (which cover
    different pieces of code).
    """
    runs, runDir, runDict, additionalRunDict, subsystems = setupNewSubsystemsFromMovedFileInfo
    if useExistingRunContainer:
        # Create subsystems inside of a ``runContainer`` by hand.
        for subsystem in subsystems:
            processRuns.createNewSubsystemFromMovedFilesInformation(runs = runs,
                                                                    subsystem = subsystem,
                                                                    runDict = runDict,
                                                                    runDir = runDir)
    else:
        # Create a new run and new subsystems.
        runs.pop(runDir)
        processRuns.processMovedFilesIntoRuns(runs = runs, runDict = runDict)

    assert checkAllCreatedSubsystems(runs = runs, subsystems = subsystems, expectedRunDict = runDict, runDir = runDir) is True
    # Sanity check that all subsystems have been created.
    # Critically, in the case of creating a new run container, the TPC subsystem should have been created even though it doesn't
    # have any files, as it is not it's own fileLocationSubsystem here.
    assert list(runs[runDir].subsystems) == subsystems

    # Now try adding an additional set of new files to the existing subsystems
    processRuns.processMovedFilesIntoRuns(runs = runs, runDict = additionalRunDict)
    expectedRunDict = copy.deepcopy(runDict)
    # Merge in all the runDirs (r) and subsystems (s) of the additionalRunDict
    for r in expectedRunDict:
        for s in expectedRunDict[r]:
            # Only do this for subsystems, not the HLT mode (which will be the same for all)
            if s != "hltMode":
                expectedRunDict[r][s].extend(additionalRunDict[r][s])

    # Check the final results
    assert checkAllCreatedSubsystems(runs = runs, subsystems = subsystems, expectedRunDict = expectedRunDict, runDir = runDir) is True

def simulatedFileArrival(runDir, runDictForSimulatedArrival):
    """ Helper function to simulate files arriving sequentially, which are then processed.

    To fully cover and test the run and subsystem creation, we need to have files show up separately.
    To do so, we create new runDict dictionaries that are only a subset of the full runDict, and then
    we separately process each newly available file.

    Args:
        runDir (str): Run directory name (ex. "Run123").
        runDictForSimulatedArrival (dict): Dict following the runDict structure, where each contained subsystem
            within a particular runDir will be simulated to arrive separately.
    Yields:
        dict: Dict following the runDict structure which contains the simulated runDict to be processed.
    """
    # Setup our input dict to create objects one at a time.
    inputRunDict = {runDir: {"hltMode": runDictForSimulatedArrival[runDir]["hltMode"]}}
    for subsystem in runDictForSimulatedArrival[runDir]:
        # Skip in case this comes up.
        if subsystem == "hltMode":
            continue

        logger.info("Creating subsystem {subsystem} with inputRunDict: {inputRunDict}".format(subsystem = subsystem, inputRunDict = inputRunDict))
        # Copy the files for the particular subsystem
        inputRunDict[runDir][subsystem] = runDictForSimulatedArrival[runDir][subsystem]
        # Yield the simulated runDict to be processed
        yield inputRunDict
        #processRuns.processMovedFilesIntoRuns(runs = runs, runDict = inputRunDict)
        # Cleanup for the next loop iteration
        inputRunDict[runDir].pop(subsystem)

def testProcessMovedFilesWithNewFileArrival(setupNewSubsystemsFromMovedFileInfo):
    """ Test for modifying existing subsystems with files that are simulated to arrive.

    Here, we create a new run container (and the corresponding subsystem containers), then simulate files
    arriving to add new files to all of the subsystems.
    """
    runs, runDir, runDict, additionalRunDict, subsystems = setupNewSubsystemsFromMovedFileInfo
    # Remove the initial run container.
    runs.pop(runDir)
    # Create the new run container and an initial set of subsystems
    processRuns.processMovedFilesIntoRuns(runs = runs, runDict = runDict)

    # Simulate files arriving into an existing run and subsystem structure.
    # Use with yield.
    for simulatedRunDict in simulatedFileArrival(runDir = runDir,
                                                 runDictForSimulatedArrival = additionalRunDict):
        processRuns.processMovedFilesIntoRuns(runs = runs, runDict = simulatedRunDict)

    expectedRunDict = copy.deepcopy(runDict)
    # Merge in all the runDirs (r) and subsystems (s) of the additionalRunDict
    for r in expectedRunDict:
        for s in expectedRunDict[r]:
            # Only do this for subsystems, not the HLT mode (which will be the same for all)
            if s != "hltMode":
                expectedRunDict[r][s].extend(additionalRunDict[r][s])

    # Check the final results
    assert checkAllCreatedSubsystems(runs = runs, subsystems = subsystems, expectedRunDict = expectedRunDict, runDir = runDir) is True

    # Explicit check on the number of TPC files. This is less flexible, but I want to be entirely
    # certain that I haven't been confused by using the generated values.
    assert len(runs[runDir].subsystems["TPC"].files) == 4

def testProcessMovedFilesWithInitialFileArrival(setupNewSubsystemsFromMovedFileInfo):
    """ Test for creating new runs and subsystems with files that are simulated to arrive.

    Here, we create a new run container with simulated file arrival. This is particularly important to check the conversion
    from a file which does not have it's own files to one which does.
    """
    runs, runDir, runDict, additionalRunDict, subsystems = setupNewSubsystemsFromMovedFileInfo
    # Remove the initial run container.
    runs.pop(runDir)

    for simulatedRunDict in simulatedFileArrival(runDir = runDir,
                                                 runDictForSimulatedArrival = runDict):
        processRuns.processMovedFilesIntoRuns(runs = runs, runDict = simulatedRunDict)

    # Check the final results
    assert checkAllCreatedSubsystems(runs = runs, subsystems = subsystems, expectedRunDict = runDict, runDir = runDir) is True

    # Explicit check on the number of TPC files. This is less flexible, but I want to be entirely
    # certain that I haven't been confused by using the generated values.
    assert len(runs[runDir].subsystems["TPC"].files) == 2

    # Now, use the additionalRunDict just for good measure to make sure that our conversion from
    # fileLocationSubsystem -> subsystem for EMC worked properly.
    for simulatedRunDict in simulatedFileArrival(runDir = runDir,
                                                 runDictForSimulatedArrival = additionalRunDict):
        processRuns.processMovedFilesIntoRuns(runs = runs, runDict = simulatedRunDict)

    expectedRunDict = copy.deepcopy(runDict)
    # Merge in all the runDirs (r) and subsystems (s) of the additionalRunDict
    for r in expectedRunDict:
        for s in expectedRunDict[r]:
            # Only do this for subsystems, not the HLT mode (which will be the same for all)
            if s != "hltMode":
                expectedRunDict[r][s].extend(additionalRunDict[r][s])

    # Check the final results
    assert checkAllCreatedSubsystems(runs = runs, subsystems = subsystems, expectedRunDict = expectedRunDict, runDir = runDir) is True

    # Explicit check on the number of TPC files. This is less flexible, but I want to be entirely
    # certain that I haven't been confused by using the generated values.
    assert len(runs[runDir].subsystems["TPC"].files) == 4
