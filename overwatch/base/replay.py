#!/usr/bin/env python

""" Enables replaying of data which Overwatch has already processed.

The underlying functions also allow moving data to arbitrary locations, which were used to
transition existing data in various stages of processing to other Overwatch sites and EOS
(the final transferring is done by the data transfer module).

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Python 2/3 support
from __future__ import print_function

# General
import os
import logging
#import shutil
logger = logging.getLogger(__name__)

# Config
from . import config
(parameters, filesRead) = config.readConfig(config.configurationType.processing)

from overwatch.base import utilities

def convertProcessedOverwatchNameToUnprocessed(dirPrefix, name):
    """ Convert a processed Overwtach filename to unprocessed filename.

    The unprocessed Overwatch filenames are of the form: ``EMChistos_300005_B_2015_11_24_18_05_10.root``.
    The processed Overwatch filenames are of the form:   ``EMChists.2015_11_24_18_05_10.root``.

    Args:
        dirPrefix (str): Path to the file.
        name (str): Name of the processed file.
    Returns:
        str: Name of the unprocessed file.
    """
    # Rename the processed name to the unprocessed name.
    # Determine the subsystem by determining the base folder, which is the second entry from split.
    prefixAndRunDir, subsystem = os.path.split(dirPrefix)
    # The run number is always 6 numbers long
    runDirLocation = prefixAndRunDir.find("Run") + len("Run")
    #runNumber = int(dirPrefix[runDirLocation:runDirLocation + 6])
    runNumber = int(prefixAndRunDir[runDirLocation:])
    # We attempt to retrieve the HLT mode if it's stored and available. Otherwise, it will default to "U".
    # since it is not conveniently known for these older files (although one could of course check the log book).
    hltMode = utilities.retrieveHLTModeFromStoredRunInfo(runDirectory = os.path.dirname(dirPrefix))
    name = "{subsystem}histos_{runNumber}_{hltMode}_{time}.root".format(subsystem = subsystem,
                                                                        runNumber = runNumber,
                                                                        hltMode = hltMode,
                                                                        time = name.split(".")[1])

    return name

def availableFiles(baseDir):
    """ Determine all ROOT files available in a particular directory.

    Args:
        baseDir (str): Directory where the ROOT files to be moved are stored.
    Yields:
        tuple: (source, name) where source (str) is the path to the source file, and name (str) is
            the appropriate name for the destination file according to the Overwatch scheme.
    """
    for root, dirs, files in os.walk(baseDir):
        # Sort the file by their arrival time so we can replay in order.
        files.sort(key=lambda x: utilities.extractTimeStampFromFilename(x) if ".root" in x else 0)

        # We move all files, regardless of where they are located.
        for name in files:
            if ".root" in name:
                source = os.path.join(root, name)
                # If the file doesn't have a non-zero size, notify and skip.
                # Check that the file has a non-zero size. If it doesn't then notify.
                metadata = os.stat(source)
                if metadata.st_size == 0:
                    logger.warning("File {source} is a size zero file and won't be moved!".format(source = source))
                    continue

                # If necessary, rename the filename back to the unprocessed Overwatch name.
                # To do so, we use the number of "." as a proxy for which type of filename that we have.
                # The unprocessed names have one "." and the processed have two ".".
                # For more, see ``convertProcessedOverwatchNameToUnprocessed(...)``.
                if name.count(".") == 2:
                    name = convertProcessedOverwatchNameToUnprocessed(dirPrefix = root, name = name)

                yield (source, name)
                #files.append((source, name))

        # Sort the files by their arrival time.
        # This enables replaying the earliest time one file at a time.
        # Determine subsystem for yield value
        #_, subsystem = os.path.split(root)
        #yield subsystem, files

def moveFiles(destinationDir, nMaxFiles):
    """ Move available files from one directory to another.

    Used to moved already existing ROOT files that are perhaps in the Overwatch directory structure
    to a directory where the can be transferred to Overwatch sites and to EOS.

    Args:
        destinationDir (str): Directory where the files should be moved.
        nMaxFiles (int): Maximum number of files which should be moved.
    """

    fileCount = 0
    for source, destinationName in availableFiles():
        if "combined" in source:
            # TODO: For full replay, remove the combined file...
            pass

        # If we've alrady moved enough files, then finish up.
        if fileCount >= nMaxFiles:
            break

        destination = os.path.join(destinationDir, destinationName)
        logger.info("Moving {source} to {destination}".format(source = source, destination = destination))
        #shutil.move(source, destination)

        # Note that the file has been moved.
        fileCount += 1

def runReplay():
    """ Helper run function for replaying or generically moving data.

    This function will run on an interval determined by the value of ``processingTimeToSleep``
    (specified in seconds). If the value is 0 or less, the processing will only run once.

    Note:
        The sleep time is defined as the time between when ``moveFiles()`` finishes and
        when it is started again.

    Args:
        ...
    Returns:
        None.
    """
    handler = utilities.handleSignals()
    sleepTime = parameters["dataReplayTimeToSleep"]
    logger.info("Starting data replay with sleep time of {sleepTime}.".format(sleepTime = sleepTime))
    while not handler.exit.is_set():
        # Run the actual executable.
        moveFiles()
        # Only execute once if the sleep time is <= 0. Otherwise, sleep and repeat.
        if sleepTime > 0:
            handler.exit.wait(sleepTime)
        else:
            break

# These functions should be moved to overwatch.base.run
def runReplayData():
    """ Replay Overwatch data that has already been processed.

    Although force reprocessing allows this to happen without having to move files,
    this type of functionality can be useful for replaying larger sets of data for
    testing the base functionality, trending, etc.

    This function will run on an interval determined by the value of ``dataReplayTimeToSleep``
    (specified in seconds). If the value is 0 or less, the processing will only run once.

    Note:
        The sleep time is defined as the time between when ``moveFiles()`` finishes and
        when it is started again.

    Args:
        None.
    Returns:
        None.
    """
    # TODO: Set the proper input parameters!
    runReplay(...)

def runDataTransition():
    """ Handle moving files so they can be transferred to Overwatch sites and EOS.

    """
    # TODO: Set the proper input parameters!
    runReplay(...)

def replayData():
    pass

# TODO: Tests

if __name__ == "__main__":
    # Configuration parameters
    numberOfFiles = 200
    baseDir = ""
    destinationDir = os.path.join("..", "data")

    moveFiles(baseDir = baseDir, destinationDir = destinationDir)
