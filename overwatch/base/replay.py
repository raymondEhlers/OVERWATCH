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
import shutil
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
        # We need to skip files which don't have ".root" in the name, as they won't have a timestamp
        files.sort(key=lambda x: utilities.extractTimeStampFromFilename(x) if x.endswith(".root") else 0)

        # We move all files, regardless of where they are located.
        for name in files:
            if name.endswith(".root"):
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

def moveFiles(baseDir, destinationDir, nMaxFiles):
    """ Move available files from one directory to another.

    Used to moved already existing ROOT files that are perhaps in the Overwatch directory structure
    to a directory where they can be reprocessing (ie replayed) or alternatively, can be transferred
    to Overwatch sites and to EOS.

    Args:
        baseDir (str): Directory where the ROOT files to be moved are stored.
        destinationDir (str): Directory where the files should be moved.
        nMaxFiles (int): Maximum number of files which should be moved.
    Returns:
        int: Number of files that were moved.
    """
    fileCount = 0
    for source, destinationName in availableFiles(baseDir = baseDir):
        # Break out if we're already moved enough files.
        if fileCount >= nMaxFiles:
            break

        # Nothing to be done with a combined file or time slice file - it should just be ignored.
        if "combined" in source or "timeSlice" in source:
            logger.debug('Skipping filename {filename} due to "combined" or "timeSlices" in name!'.format(filename = source))
            continue

        destination = os.path.join(destinationDir, destinationName)
        logger.info("Moving {source} to {destination}".format(source = source, destination = destination))
        shutil.move(source, destination)

        # Note that the file has been moved.
        fileCount += 1

    # We've either moved the requested number of files, or we've ran out of files (and there are no more left to move).
    return fileCount

def runReplay(baseDir, destinationDir, nMaxFiles):
    """ Helper run function for moving processed data into unprocessed data.

    This function basically drives the underlying implementation of replaying data. It will
    run on an interval determined by the value of ``dataReplayTimeToSleep`` (specified in
    seconds). If the value is 0 or less, the processing will only run once. In addition, if
    there are no more files to move, the replay will finish.

    Note:
        The sleep time is defined as the time between when ``moveFiles(...)`` finishes and
        when it is started again.

    Args:
        baseDir (str): Directory where the ROOT files to be moved are stored.
        destinationDir (str): Directory where the files should be moved.
        nMaxFiles (int): Maximum number of files which should be moved.
    Returns:
        None.
    """
    # Now being our loop
    handler = utilities.handleSignals()
    sleepTime = parameters["dataReplayTimeToSleep"]
    logger.info("Starting data replay with sleep time of {sleepTime}.".format(sleepTime = sleepTime))
    while not handler.exit.is_set():
        # Run the actual executable.
        nMoved = moveFiles(baseDir = baseDir,
                           destinationDir = destinationDir,
                           nMaxFiles = nMaxFiles)
        # Only execute once if the sleep time is <= 0 or no files are moved. Otherwise, sleep and repeat.
        if sleepTime > 0 and nMoved != 0:
            handler.exit.wait(sleepTime)
        else:
            if nMoved == 0:
                # Inform about result so the user isn't surprised.
                logger.info("No more files available to move! Finishing up")
            # Set the handler to exit.
            handler.exit.set()

    # Inform about completion.
    logger.info("Completed replay.")
