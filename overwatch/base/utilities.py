#!/usr/bin/env python

""" Shared utility functions used for organizing file structure, merging histograms, and transferring data.

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
import shutil
import numpy as np
import signal
import threading

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
    """ Extracts unix time stamp from a given filename.

    This works for combined, time slice, and files received from the HLT filenames, although
    the meaning varies depending on the type of filename passed. The type of the filename will
    be automatically detected based on substrings of the filename. This will determine the
    format of the timestamp to be extracted.

    For possibles filenames are as follows:

    - For combined files, the format is `prefix/combined.unixTimeStamp.root`, so we can just extract it directly.
    - For time slices, the format is `prefix/timeSlices.unixStartTime.unixEndTime.root`, so we extract the two
      times, subtract them, and return the difference. Note that this makes it a different format than the other
      two timestamps.
    - For other files processed into subsystems, the format is `prefix/SYShists.%Y_%m_%d_%H_%M_%S.root`. We
      extract the time stamp and convert it to unix time. The time stamp is assumed to be in the CERN time zone.

    Note:
        The ``prefix/`` can be anything (or non-existent), as long as it doesn't contain any ``.``.

    Args:
        filename (str): Filename which contains the desired timestamp. The precise format of the timestamp
            depends on the type filename passed into the function.
    Returns:
        int: Timestamp extracted from the filename in number of seconds (unix time, except for time slices,
            where it is the length of the time stamp).
    """
    if "combined" in filename:
        # This will be the time stamp of the latest file to contribute to the combined file.
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

    Note:
        The filenames that are returned are of the form ``Run123456/SYS/file.root``.

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
            filename = os.path.join(filenamePrefix, name)
            mergeDict[extractTimeStampFromFilename(filename)] = filename

    # Max time range in minutes (60s added to make sure we don't undershoot)
    keys = sorted(mergeDict.keys())
    # // is integer division
    maxTimeMinutes = (keys[-1] - keys[0] + 60) // 60

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
# Logging utilities
###################################################
def setupLogging(logger, logLevel, debug):
    """ General function to setup the proper logging outputs for an executable.

    Creates loggers for logging to stdout, rotating file, and email (for warning or above logs).
    They are enabled depending on the configuration.

    Args:
        logger (logging.Logger): Logger to be configured. This should be the logger of the executable.
        logLevel (int): Logging level. Select from any of the options defined in the logging module.
        debug (bool): Overall debug mode for the executable. True logs to the console while False logs
            to a rotating file handler and sets up the possibility of sending logs via email. Default: True
    Returns:
        None. The logger is fully configured.
    """
    # We use some of the basic parameters for configuration, so we need to grab them now.
    parameters, _ = config.readConfig(config.configurationType.base)

    # Configure logger
    # Logging level for root logger
    logger.setLevel(logLevel)
    # Format
    #logFormatStr = "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
    logFormatStr = "%(asctime)s %(levelname)s: %(message)s [in %(module)s:%(lineno)d]"
    logFormat = logging.Formatter(logFormatStr)

    # We setup all streams and then decide which to configure based on our deployment mode.
    # Log stream to stdout
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setLevel(logLevel)
    streamHandler.setFormatter(logFormat)

    # Log to file
    # Will be a maximum of 5 MB, rotating with 10 files
    # We will store the log in the ``exec/logs`` dir. We'll create it if necessary.
    # NOTE: We won't actually setup logging to file here. This will be taken care of by supervisor.
    logDirPath = os.path.join("exec", "logs")
    if not os.path.exists(logDirPath):
        os.makedirs(logDirPath)

    # Log to email
    # See: http://flask.pocoo.org/docs/1.0/errorhandling/
    #      and http://flask.pocoo.org/docs/1.0/logging/#logging
    emailHandler = logging.handlers.SMTPHandler(mailhost = "smtp.cern.ch",
                                                fromaddr = "error@aliceoverwatch.cern.ch",
                                                toaddrs = parameters["emailLoggerAddresses"],
                                                subject = "OVERWATCH Failed")
    emailHandler.setLevel(logLevel)
    emailLogFormatStr = """
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    """
    emailLogFormat = logging.Formatter(emailLogFormatStr)
    emailHandler.setFormatter(emailLogFormat)

    # For docker, we log to stdout so that supervisor is able to handle the logging
    logger.addHandler(streamHandler)
    logger.info("Added stdout streaming handler to logging!")
    # Logging to file is taken care of by supervisor (or potentially docker), so we don't need
    # to add it here.

    # Also allow for the possibility of the sending email with higher priority warnings.
    if parameters["emailLogger"]:
        logger.addHandler(emailHandler)
        logger.info("Added mailer handler to logging!")

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

    Note:
        The filenames returned here are different than those from ``createFileDictionary()``. Here, we return
        just the filename in the nested dict, while there we return the full path to the file (not including the
        ``dirPrefix``).

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
            splitFilename = tempFilename.replace(".root", "").split("_")
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
            runDir = "Run" + splitFilename[1]
            # Just to be safe, we explicitly make it upper case (although it should be already).
            hltMode = splitFilename[2].upper()

            # Determine the directory structure for each run
            # We want to start with a path of the form "Run123456"
            runDirectoryPath = runDir

            # Move replays of the data to a different directory, since we don't want to process it.
            if hltMode == "E":
                runDirectoryPath = os.path.join("ReplayData", runDirectoryPath)

            # Create run directory and subsystem directories as needed
            if not os.path.exists(os.path.join(dirPrefix, runDirectoryPath)):
                os.makedirs(os.path.join(dirPrefix, runDirectoryPath))
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
            # Don't import `move` from shutils. It appears to have unexpected behavior which
            # can have very bad consequences, including deleting files and other data loss!
            shutil.move(oldPath, newPath)

            # Store the filenames and HLT mode
            # NOTE: The HLT mode is only stored if it doesn't yet exist because it must be the same
            #       within a particular run.
            # Create dict for subsystem if it doesn't exist, and then create a list for the run if it doesn't exist
            # See: https://stackoverflow.com/a/12906014
            runsDict.setdefault(runDir, {}).setdefault(key, []).append(newFilename)
            # Save the HLT mode
            if "hltMode" not in runsDict[runDir]:
                runsDict[runDir]["hltMode"] = hltMode

    return runsDict

def moveRootFiles(dirPrefix, subsystemList):
    """ Simple driver function to move files received from the HLT into the appropriate directory structure
    for processing.

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        subsystemList (list): List of subsystems to be considered.
    Returns:
        dict: Nested dict which contains the new filenames and the HLT mode. For the precise structure, ``moveFiles()``.
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
        logger.info("Adding user {user}".format(user = user))

    # Secret key
    # Set the secret key to the one set in the server parameters.
    if overwriteSecretKey or "secretKey" not in db["config"]:
        # NOTE: There will always be a secret key in the sensitive paramers (by default, it just generates a random one),
        #       so we can just use the value without worrying whether it exists.
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
    arr = np.delete(arr, 0, axis=0)
    arr = np.append(arr, [value], axis=0)
    return arr

#############
# Run helpers
#############
class handleSignals(object):
    """ Helper class to gracefully handle a kill signal.

    We handle ``SIGINT`` (for example, sent by ctrl-c) and ``SIGTERM`` (for example, sent by docker).

    This class is adapted from the solution described `here <https://stackoverflow.com/a/31464349>`__,
    and improved with the information `here <https://stackoverflow.com/a/46346184>`__.

    In the run module, it is expected to have some kind of code similar to below:

    .. code:: python

        handler = handleSignals()
        while not handler.exit.is_set():
            # Do something
            handler.exit.wait(parameters["dataTransferTimeToSleep"])

    Args:
        None.

    Attributes:
        exit (threading.Event): Event to manage when we've received a signal. ``exit.set()`` is called
            when a signal is received, and can be checked via ``is_set()``.
    """
    exit = threading.Event()

    def __init__(self):
        signal.signal(signal.SIGINT, self.exitGracefully)
        signal.signal(signal.SIGTERM, self.exitGracefully)

    def exitGracefully(self, signum, frame):
        """ Handle the signal by storing that it was sent, allowing the run function to exit. """
        logger.info("Received signal {signum}. Passing on to executing function...".format(signum = signum))
        self.exit.set()
