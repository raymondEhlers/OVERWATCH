#!/usr/bin/env python

"""
Shared utility functions used for organizing file structure, merging histograms, and transferring data.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# Python 2/3 support
from __future__ import print_function
from future.utils import iteritems

# General
import os
import sys
import time
from calendar import timegm
from subprocess import call
import shutil
import numpy as np

# ZODB
import ZODB
import transaction
import persistent
# For determining the storage type
import zodburi

# Logging
import logging
import logging.handlers
logger = logging.getLogger(__name__)

# Configuration
from . import config

###################################################
# General utilities
###################################################
def extractTimeStampFromFilename(filename):
    """ Extracts unix time stamp from a given filename. This works for combined, time slice, and
    files received from the HLT filenames.

    The type of the filename will be automatically detected based on substrings of the filename.
    This will determine the format of the timestamp to be extracted.

    For possibles filenames are as follows:

    - For combined files, the format is `combined.unixTimeStamp.root`, so we can just extract it directly.
    - For time slices, the format is `timeSlices.unixStartTime.unixEndTime.root`, so we extract the two times,
      subtract them, and return the difference. Note that this makes it a different format than the other
      two timestamps.
    - For other files processed into subsystems, the format is `SYShists.%Y_%m_%d_%H_%M_%S.root`. We extract
      the time stamp and convert it to unix time. The time stamp is assumed to be in the CERN time zone.

    Args:
        filename (str): Filename which contains the desired timestamp. The precise format of the timestamp
            depends on the type filename passed into the function.
    Returns:
        int: Timestamp extracted from the filename in number of seconds (unix time, except for time slices,
            where it is the length of the time stamp).
    """
    if "combined" in filename:
        # This will be the length of the run
        timeString = filename.split(".")[3]
        return int(timeString)
    elif "timeSlice" in filename:
        # This will be the length of the time slice
        timeString = filename.split(".")
        return int(timeString[2]) - int(timeString[1])
    else:
        timeString = filename.split(".")[1]
        timeStamp = time.strptime(timeString, "%Y_%m_%d_%H_%M_%S")
        return timegm(timeStamp)

def createFileDictionary(currentDir, runDir, subsystem):
    """ Creates dictionary of files and their unix timestamps for a given run directory.

    This function effectively characterizes the files available for a subsystem in a given
    run, providing all files, as well as the length of the run.

    Args:
        currentDir (str): Path to the directory containing run directories.
        runDir (str): Run directory to be considered.
        subsystem (str): Subsystem to be considered. 
    Returns:
        list: [Dictionary from time stamp to filename, time in minutes spanned by the run]
    """
    filenamePrefix = os.path.join(runDir, subsystem)

    # Store unmerged filenames and their unix timestamps in dictionary
    mergeDict = {}

    # Add uncombined .root files to mergeDict, then sort by timestamp
    for name in os.listdir(os.path.join(currentDir, runDir, subsystem)):
        if ".root" in name and "combined" not in name and "timeSlice" not in name:
            filename  = os.path.join(filenamePrefix, name)
            mergeDict[extractTimeStampFromFilename(filename)] = filename 

    # Max time range in minutes (60s added to make sure we don't undershoot)
    keys = sorted(mergeDict.keys())
    # // is integer division
    maxTimeMinutes = (keys[-1] - keys[0] + 60)//60 

    return [mergeDict, maxTimeMinutes]

def findCurrentRunDirs(dirPrefix = ""):
    """ Finds all of the dirs in the specified directory dir with "Run" in the name.

    Args:
        dirPrefix (str): Path to where all of the run directories are stored. Default: current working directory.
    Returns:
        list: List of runs.
    """
    if dirPrefix == "":
        currentDir = os.getcwd()
    else:
        currentDir = os.path.abspath(dirPrefix)

    runDirs = []
    for name in os.listdir(currentDir):
        if os.path.isdir(os.path.join(currentDir, name)) and "Run" in name:
            runDirs.append(name)

    runDirs.sort()
    return runDirs

###################################################
# File transfer utilities
###################################################
def rsyncData(dirPrefix, username, remoteSystems, remoteFileLocations):
    """ Syncs data to a remote system using rsync.

    The overall command is:

    .. code-block:: bash

       rsync -rvlth --chmod=ugo=rwX --omit-dir-times --exclude="Run*/*/timeSlices" --include="Run*/***" --include="ReplayData/***" --include="runList.html" --exclude="*" --delete data/ rehlers@pdsf.nersc.gov:/project/projectdirs/alice/www/emcalMonitoring/data/2016/

    (assuming that we are transferring to PDSF)

    Some notes on the arguments include:

    - The `chmod` option is explained `here <https://unix.stackexchange.com/a/218165>`__.
    - `omit-dir-times` does not update the timestamps on dirs (but still does on files in those directories),
      which fixes a number of errors thrown when transferring to PDSF
    - Information on determining the right globbing is explained `here <https://unix.stackexchange.com/a/2503>`__.
    - Files in directories `Run*` and `ReplayData/*` are transferred, and all other files in those directories
      are deleted! The exception to this is the timeSlice directory. Otherwise, all files in the root of the
      data directory are not transferred.
    - The argument order for specifying directories to include and exclude matters! The first one sets an
      overall pattern, and then subsequent includes or excludes only work with what is still available!
    - When we pass the arguments via call(), they are sent directly to `rsync`. Thus, quotes around each glob
      are not necessary and do not work correctly. See `here <https://stackoverflow.com/a/12497246>`__ for more.

    Note:
        Filenames of the form `*histos_*.root` are excluded from transfer! These are
        unprocessed files from the HLT and should not be transferred!

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        username (str): Username to use with `rsync`.
        remoteSystem (str): Hostname of the remote system.
        remoteFileLocation (str): Directory to where files should be stored on the remote system.
    Returns:
        None.
    """
    # Determine which type of file we are transfering
    fileDestinationLabel = "data"

    # An ending slash is needed so that rsync transfers the proper files (and not just the directory)
    sendDirectory = dirPrefix
    if not sendDirectory.endswith("/"):
        sendDirectory = sendDirectory + "/"

    if len(remoteSystems) != len(remoteFileLocations[fileDestinationLabel]):
        logger.critical("Number of remote systems is not equal to number of remote file locations. Skipping rsync operations!")
    else:
        for remoteSystem, remoteFileLocation in zip(remoteSystems, remoteFileLocations[fileDestinationLabel]):
            if not remoteFileLocation.endswith("/"):
                remoteFileLocation = remoteFileLocation + "/"

            logger.info("Utilizing user %s to send %s files to %s on %s " % (username, fileDestinationLabel, remoteFileLocation, remoteSystem))

            # For more information on these arguments, see the doc string.
            rsyncCall = ["rsync", "-rvlth", "--chmod=ugo=rwX", "--omit-dir-times", "--exclude=Run*/*/timeSlices", "--include=Run*/***", "--include=ReplayData/***", "--include=runList.html", "--exclude=*", "--delete", sendDirectory, username + "@" + remoteSystem + ":" + remoteFileLocation]
            logger.info(rsyncCall)
            call(rsyncCall)

###################################################
# Logging utilities
###################################################
def setupLogging(logger, logLevel, debug, logFilename):
    """ General function to setup the proper logging outputs for an executable.

    Args:
        logger (logging.Logger): Logger to be configured. This should be the logger of the executable.
        logLevel (int): Logging level. Select from any of the options defined in the logging module.
        debug (bool): Overall debug mode for the executable. True logs to the console while False logs
            to a rotating file handler and sets up the possibility of sending logs via email. Default: True
        logFilename (str): Specifies the filename of the log file (when it is created).
    Returns:
        None. The logger is fully configured.
    """
    # Check on docker deployment variables
    # This overrides logging to file and instead logs to the screen,
    # which is then stored by the container itself.
    try:
        dockerDeploymentOption = os.environ["deploymentOption"]
    except KeyError:
        # It doesn't exist
        dockerDeploymentOption = ""

    # Configure logger
    # Logging level for root logger
    logger.setLevel(logLevel)
    # Format
    #logFormatStr = "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    logFormatStr = "%(asctime)s %(levelname)s: %(message)s [in %(module)s:%(lineno)d]"
    logFormat = logging.Formatter(logFormatStr)

    # For docker, we log to stdout so that supervisor is able to handle the logging
    if debug == True or dockerDeploymentOption:
        # Log to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logLevel)
        handler.setFormatter(logFormat)
        logger.addHandler(handler)
        logger.debug("Added streaming handler to logging!")
    else:
        # Log to file
        # Will be a maximum of 5 MB, rotating with 10 files
        handler = logging.handlers.RotatingFileHandler(os.path.join("deploy", "{}.log".format(logFilename)),
                                                       maxBytes = 5000000,
                                                       backupCount = 10)
        handler.setLevel(logLevel)
        handler.setFormatter(logFormat)
        logger.addHandler(handler)
        logger.debug("Added file handler to logging!")

        # Sent issues through email
        # See: http://flask.pocoo.org/docs/0.10/errorhandling/
        notifyAddresses = []
        handler = logging.handlers.SMTPHandler("smtp.cern.ch",
                                                "error@aliceoverwatch.cern.ch",
                                                notifyAddresses, "OVERWATCH Failed")
        handler.setLevel(logging.WARNING)
        logFormatStr = """
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s
        """
        logFormat = logging.Formatter(logFormatStr)
        handler.setFormatter(logFormat)
        # TODO: Properly configure so that it can be added as a handler!
        #logger.addHandler(handler)
        logger.debug("Added mailer handler to logging!")

    # Be sure to propagate messages from modules
    #processRunsLogger = logging.getLogger("processRuns")
    #processRunsLogger.setLevel(logLevel)
    #processRunsLogger.propagate = True

###################################################
# File moving utilities
###################################################
def enumerateFiles(dirPrefix, subsystem):
    """ Determine the ROOT files which have been received from the HLT and need to be moved into the Overwatch
    run file structure for processing.

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        subsystem (str): Subsystem to be considered. 
    Returns:
        list: Files in provided directory that need to be moved.
    """
    if dirPrefix == "":
        currentDir = os.getcwd()
    else:
        currentDir = os.path.abspath(dirPrefix)

    filesToMove = []
    for name in os.listdir(currentDir):
        if subsystem in name and ".root" in name:
            filesToMove.append(name)
            #logger.debug("name: %s" % name)
        
    return sorted(filesToMove)

def moveFiles(dirPrefix, subsystemDict):
    """ For each subsystem, moves ROOT files received from the HLT into appropriate file structure for processing.

    In particular, files from the HLT have the general form of `SYShists_runNumber_hltMode_%Y_%m_%d_%H_%M_%S.root`.
    For a particular example, files start like this:

    .. code-block:: bash

       EMChistos_300005_B_2015_11_24_18_05_10.root
       EMChistos_300005_B_2015_11_24_18_09_12.root
       ...

    and are then moved to

    .. code-block:: bash

       Run300005/
           EMC/
               EMChists.2015_11_24_18_05_10.root
               EMChists.2015_11_24_18_09_12.root

    The new filenames are then returned in a nested dictionary of lists which has the following structure (assuming
    the example specified above):

    >>> runsDict["Run300005"]["EMC"]
    ["EMChists.2015_11_24_18_05_10.root", "EMChists.2015_11_24_18_09_12.root"]
    >>> runsDict["Run300005"]["hltMode"]
    "B"

    The run and subsystem directories are created as needed. The filenames are determined by convention to make
    it possible to extract the timestamps later. The HLT mode is also stored, moving the information from the
    input filename to the output dict. Some care is required here - otherwise the HLT information will be lost
    (although it can always be reconstructed via the logbook).

    Note:
        HLT mode "E" corresponds to be replayed data which can be disregarded. Here, it is moved
        to the `ReplayData` directory so it doesn't get processed, but it also isn't entirely lost.

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        subsystemDict (dict): Dictionary of subsystems (keys) and lists of files that need to be moved (values)
            for each subsystem.
    Returns:
        dict: Nested dict which contains the new filenames and the HLT mode. For the precise structure, see above.
    """
    runsDict = {}

    # For each subsystem, loop over all files to move, and put them in subsystem directory
    for key in subsystemDict.keys():
        filesToMove = subsystemDict[key]
        if len(filesToMove) == 0:
            logger.info("No files to move in %s" % key)
        for filename in filesToMove:
            # Split the filename to extract the relevant information
            # We remove the ".root" so we can split on "_" without having an extraneous
            # information tacked on.
            tempFilename = filename
            splitFilename = tempFilename.replace(".root","").split("_")
            #logger.debug("tempFilename: %s" % tempFilename)
            #logger.debug("splitFilename: ", splitFilename)

            # Skip filenames that don't conform to the expectation.
            # These should be fairly uncommon, as we require the files to be ROOT files received
            # from the HLT which have the subsystem in the name, but somehow are not from the HLT
            # receiver.
            if len(splitFilename) < 3:
                continue
            timeString = "_".join(splitFilename[3:])
            #logger.debug("timeString: ", timeString)

            # Extract the timestamp
            # We don't actually parse the timestamp - we just pass it on from the previous
            # filename. However, if we wanted to parse it, we could parse it as:
            # `timeStamp = time.strptime(timeString, "%Y_%m_%d_%H_%M_%S")`
            # Alternatively, if the string was properly formatted, it could be read
            # using extractTimeStampFromFilename() (although note that it usually assumes
            # that the structure of the filename follows the output of this function,
            # so it would require some additional formatting if it was used right here).
            runString = splitFilename[1]
            runNumber = int(runString)
            hltMode = splitFilename[2]

            # Determine the directory structure for each run
            # We want it to be of the form "Run123456"
            runDirectoryPath = "Run" + str(runNumber)

            # Move replays of the data to a different directory, since we don't want to process it.
            if hltMode == "E":
                runDirectoryPath = os.path.join("ReplayData", runDirectoryPath)

            # Create run directory and subsystem directories as needed
            if not os.path.exists(os.path.join(dirPrefix, runDirectoryPath)):
                os.makedirs( os.path.join(dirPrefix, runDirectoryPath) )
            # Only create the subsystem if we actually have files to move there. In principle, we
            # should never got to this point with no files to move (since it is checked before looping
            # and if there are no files, we wouldn't have anything to loop over), but we check here
            # for good measure.
            if len(filesToMove) != 0 and not os.path.exists(os.path.join(dirPrefix, runDirectoryPath, key)):
                os.makedirs(os.path.join(dirPrefix, runDirectoryPath, key))
            
            # Determine the final filename according to the format "SYShists.timestamp.root"
            newFilename = key + "hists." + timeString + ".root"

            # Determine the final paths and move the file.
            oldPath = os.path.join(dirPrefix, tempFilename)
            newPath = os.path.join(dirPrefix, runDirectoryPath, key, newFilename)
            logger.info("Moving %s to %s" % (oldPath, newPath))
            # Don't import move from shutils. It appears to have unexpected behavior which
            # can have very bad consequences, including deleting files and other data loss!
            shutil.move(oldPath, newPath)

            # Store the filenames and HLT mode
            # NOTE: The HLT mode is only stored if it doesn't yet exist because it must be the same
            #       within a particular run.
            # Create dict for subsystem if it doesn't exist, and then create a list for the run if it doesn't exist
            # See: https://stackoverflow.com/a/12906014
            runsDict.setdefault(runString, {}).setdefault(key, []).append(newFilename)
            # Save the HLT mode
            if "hltMode" not in runsDict[runString]:
                runsDict[runString]["hltMode"] = hltMode

    return runsDict

def moveRootFiles(dirPrefix, subsystemList):
    """ Simple driver function to move files received from the HLT into the appropriate directory structure
    for processing.

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        subsystemList (list): List of subsystems to be considered.
    Returns:
        None.
    """
    subsystemDict = {}
    for subsystem in subsystemList:
        subsystemDict[subsystem] = enumerateFiles(dirPrefix, subsystem)
    
    return moveFiles(dirPrefix, subsystemDict)

###################################################
# Handle database operations
###################################################
def getDB(databaseLocation):
    """ Setup and retrieve the database available at the given location.

    Args:
        databaseLocation (str): Path to the database. Must be a valid zodburi URI, which could be a local
            file, a socket, a network path, or another type.
    Returns:
        tuple: (ZODB db root PersistentMapping, ZODB.Connection.Connection object). The connection object
            should be closed work with the database is completed.
    """
    # Get the database
    # See: http://docs.pylonsproject.org/projects/zodburi/en/latest/
    #storage = ZODB.FileStorage.FileStorage(os.path.join(dirPrefix,"overwatch.fs"))
    storage_factory, dbArgs = zodburi.resolve_uri(databaseLocation)
    storage = storage_factory()
    db = ZODB.DB(storage, **dbArgs)
    connection = db.open()
    dbRoot = connection.root()

    return (dbRoot, connection)

def updateDBSensitiveParameters(db, overwriteSecretKey = True):
    """ Update sensitive parameters which are stored in the database. Those parameters include the users
    dictionary, as well as the secret key used for cookie signing.

    These values are stored under the "config" key in the database and will be created if they do not
    yet exist.

    Args:
        db (PersistentMapping): The root database persistent mapping.
        overwriteSecretKey (bool): If true, the secret key in the database should be overwritten
            with a new value read from the configuration.
    Returns:
        None.
    """
    # We retrieve the configuration related to the webApp module because we may want to
    # update options that are defined only for he webApp (such as the users).
    (sensitiveParameters, filesRead) = config.readConfig(config.configurationType.webApp)

    # Ensure that the config exists
    if "config" not in db:
        db["config"] = persistent.mapping.PersistentMapping()
        logger.warning("Needed to create the config!")

    # Users
    # Create mapping if not already there
    if "users" not in db['config']:
        db["config"]["users"] = persistent.mapping.PersistentMapping()
        logger.info("Created the users dict!")

    # Add each user, overriding an existing settings
    users = db["config"]["users"]
    for user, pw in iteritems(sensitiveParameters["_users"]):
        users[user] = pw
        logger.info("Adding user {0}".format(user))

    # Secret key
    # Set the secret key to that set in the server parameters
    if overwriteSecretKey or "secretKey" not in db["config"]:
        db["config"]["secretKey"] = sensitiveParameters["_secretKey"]
        logger.info("Adding secret key to db!")

    # Ensure that any additional changes are committed
    transaction.commit()

####################
# Histogram array functions
####################
def removeOldestValueAndInsert(arr, value):
    """ Removes the oldest value from the start of a numpy array and appends a new value at the end.

    Args:
        arr (numpy.ndarray): Array containing the values to modify.
        value (int or float): Value to be appended.
    Returns:
        numpy.ndarray: The modified array.
    """
    # Remove oldest value
    np.delete(arr, 0, axis=0)
    # Insert at the end
    arr[-1] = value

    return arr

