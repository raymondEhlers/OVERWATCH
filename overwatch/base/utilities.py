"""
Shared utility functions used for organizing file structure, merging histograms, and posting data.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""
# Python 2/3 support
from __future__ import print_function

# General
import os
import sys
import time
from calendar import timegm
from subprocess import call
import shutil

# ZODB
import ZODB
import transaction
import persistent
# For determining the storage type
import zodburi

# Logging
import logging
import logging.handlers
# Setup logger
logger = logging.getLogger(__name__)

# Configuration
from . import config

# This only works for non combined runs, since they contain a range of times
###################################################
def extractTimeStampFromFilename(filename):
    """ Extracts unix time stamp of a given file.

    Args:
        filename (str): Filename that we want the timestamp of. The file must be named according to the convention specified in the function. 

    Returns:
        int: Unix time stamp that file corresponds to.

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

###################################################
def createFileDictionary(currentDir, runDir, subsystem):
    """ Creates dictionary of files and their unix timestamps, in a given run directory.

    Args:
        currentDir (str): Directory prefix necessary to get to all of the folders.
        runDir (str): Run directory to be considered.
        subsystem (str): Subsystem to be considered. 

    Returns:
        tuple: Tuple containing:

            mergeDict (dict): Dictionary of files (values) and their unix timestamps (keys), in a given run directory.

            maxTimeMinutes (int): Total time, in minutes, spanned by the run. 

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

# Finds all of the dirs in the current working dir with "Run" in the name
###################################################
def findCurrentRunDirs(dirPrefix = ""):
    """ Finds list of currently existing runs that we have data for. 

    Args:
        currentDir (Optional[str]): Directory prefix used to get to all of the folders. Default: current working directory.
       
    Returns:
        list: List of current runs that we have data for. 

    """

    runDirs = []
    if dirPrefix == "":
        currentDir = os.getcwd()
    else:
        currentDir = os.path.abspath(dirPrefix)

    for name in os.listdir(currentDir):
        if os.path.isdir(os.path.join(currentDir, name)) and "Run" in name:
            runDirs.append(name)

    runDirs.sort()
    return runDirs

###################################################
def rsyncData(dirPrefix, username, remoteSystems, remoteFileLocations):
    """ Syncs data directory to a remote system using rsync.

    Note:
        Filenames of the form "*histos_*.root" are excluded from transfer! These are
        unprocessed files from the HLT and should not be transfered!

    Args:
        dirPrefix (str): Directory prefix used to get to all of the data.
        username (str): Username to use with rsync.
        remoteSystem (str): Hostname of the remote system.
        remoteFileLocation (str): Directory to store files on the remote system.
       
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
        logger.error("Number of remote systems is not equal to number of remote file locations. Skipping rsync operations!")
    else:
        for remoteSystem, remoteFileLocation in zip(remoteSystems, remoteFileLocations[fileDestinationLabel]):
            if not remoteFileLocation.endswith("/"):
                remoteFileLocation = remoteFileLocation + "/"

            logger.info("Utilizing user %s to send %s files to %s on %s " % (username, fileDestinationLabel, remoteFileLocation, remoteSystem))

            # The chmod argument is explained here: https://unix.stackexchange.com/a/218165
            # The omit-dir-times does not update the timestamps on dirs (but still does on files in those dirs),
            # which fixes a number of errors thrown when transfering to PDSF
            # Information on determining the right globbing is explained here: https://unix.stackexchange.com/a/2503
            # NOTE: Files in directories "Run*" and "ReplayData/*" are transfered, and all other files in those directries are deleted!
            #        The exception to this is the timeSlice directory.
            #        Otherwise, all files in the root of the data directory are not transfered.
            # NOTE: The argument order matters! The first one always applies, and then subsequent includes or excludes only work with what is still available!
            # NOTE: When we pass the arguments via call(), they are sent directly to rsync. Thus, quotes around
            # each glob are not necessary and do not work correctly. See: https://stackoverflow.com/a/12497246
            #rsync -rvlth --chmod=ugo=rwX --omit-dir-times --exclude="Run*/*/timeSlices" --include="Run*/***" --include="ReplayData/***" --include="runList.html" --exclude="*" --delete data/ rehlers@pdsf.nersc.gov:/project/projectdirs/alice/www/emcalMonitoring/data/2016/
            rsyncCall = ["rsync", "-rvlth", "--chmod=ugo=rwX", "--omit-dir-times", "--exclude=Run*/*/timeSlices", "--include=Run*/***", "--include=ReplayData/***", "--include=runList.html", "--exclude=*", "--delete", sendDirectory, username + "@" + remoteSystem + ":" + remoteFileLocation]
            logger.info(rsyncCall)
            call(rsyncCall)

###################################################
def setupLogging(logger, logLevel, debug, runType):
    # Check on docker deplyoment variables
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
        handler = logging.handlers.RotatingFileHandler(os.path.join("deploy", "{0}.log".format(runType)),
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
    """ Makes list of ROOT files that need to be moved from directory that receives HLT histograms into appropriate file structure for processing. 

    Args:
        dirPrefix (str): Directory prefix used to get to all of the folders.
        subsystem (str): Subsystem to be considered. 
       
    Returns:
        list: List of files in current working directory that need to be moved to appropriate file structure for processing.

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

###################################################
def moveFiles(subsystemDict, dirPrefix):
    """ For each subsystem, moves ROOT files that need to be moved from directory that receives HLT histograms into appropriate file structure for processing. 

    Creates run directory and subsystem directories as needed. Renames files to convention that is later used for extracting timestamps. 

    Args:
        subsystemDict (dict): Dictionary of subsystems (keys) and lists of files that need to be moved (values) for each subsystem.
        dirPrefix (str): Directory prefix used to get to all of the folders.
       
    Returns:
        None.

    """

    runsDict = {}

    # For each subsystem, loop over all files to move, and put them in subsystem directory
    for key in subsystemDict.keys():
        filesToMove = subsystemDict[key]
        if len(filesToMove) == 0:
            logger.info("No files to move in %s" % key)
        for filename in filesToMove:
            # Extract time stamp and run number
            tempFilename = filename
            splitFilename = tempFilename.replace(".root","").split("_")
            #logger.debug("tempFilename: %s" % tempFilename)
            #logger.debug("splitFilename: ", splitFilename)
            if len(splitFilename) < 3:
                continue
            timeString = "_".join(splitFilename[3:])
            #logger.debug("timeString: ", timeString)

            # How to parse the timeString if desired
            #timeStamp = time.strptime(timeString, "%Y_%m_%d_%H_%M_%S")
            runString = splitFilename[1]
            runNumber = int(runString)
            hltMode = splitFilename[2]

            # Determine the directory structure for each run
            runDirectoryPath = "Run" + str(runNumber)
            # Move replays of the data to a different directory
            if hltMode == "E":
                runDirectoryPath = os.path.join("ReplayData", runDirectoryPath)

            # Create Run directory and subsystem directories as needed
            if not os.path.exists(os.path.join(dirPrefix, runDirectoryPath)):
                os.makedirs( os.path.join(dirPrefix, runDirectoryPath) )
            if len(filesToMove) != 0 and not os.path.exists(os.path.join(dirPrefix, runDirectoryPath, key)):
                os.makedirs(os.path.join(dirPrefix, runDirectoryPath, key))
            
            newFilename = key + "hists." + timeString + ".root"

            oldPath = os.path.join(dirPrefix, tempFilename)
            newPath = os.path.join(dirPrefix, runDirectoryPath, key, newFilename)
            logger.info("Moving %s to %s" % (oldPath, newPath))
            # DON"T IMPORT MOVE. BAD CONSEQUENCES!!
            shutil.move(oldPath, newPath)

            # Create dict for subsystem if it doesn't exist, and then create a list for the run if it doesn't exist
            # See: https://stackoverflow.com/a/12906014
            runsDict.setdefault(runString, {}).setdefault(key, []).append(newFilename)
            # Save the HLT mode
            # Must be the same for each file in the run
            if "hltMode" not in runsDict[runString]:
                runsDict[runString]["hltMode"] = hltMode

    return runsDict

###################################################
def moveRootFiles(dirPrefix, subsystemList):
    """ Orchestrates the enumeration of files to be moved as they are read in from the HLT, the creation the appropriate directory structure for processing, and the moving of these files to these directories.  

    Uses enumerateFiles() and moveFiles() to do the work. 

    Args:
        dirPrefix (str): Directory prefix used to get to all of the folders.
        subsystemList (list): List of subsystems considered. 
       
    Returns:
        None.

    """

    subsystemDict = {}
    for subsystem in subsystemList:
        subsystemDict[subsystem] = enumerateFiles(dirPrefix, subsystem)
    
    return moveFiles(subsystemDict, dirPrefix)


###################################################
# Handle database operations
###################################################
def getDB(databaseLocation):
    # Get the database
    # See: http://docs.pylonsproject.org/projects/zodburi/en/latest/
    #storage = ZODB.FileStorage.FileStorage(os.path.join(dirPrefix,"overwatch.fs"))
    storage_factory, dbArgs = zodburi.resolve_uri(databaseLocation)
    storage = storage_factory()
    db = ZODB.DB(storage, **dbArgs)
    connection = db.open()
    dbRoot = connection.root()

    return (dbRoot, connection)

###################################################
def updateDBSensitiveParameters(db, overwriteSecretKey = True):
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
    for user, pw in sensitiveParameters["_users"].items():
        users[user] = pw
        logger.info("Adding user {0}".format(user))

    # Secret key
    # Set the secret key to that set in the server parameters
    if overwriteSecretKey or "secretKey" not in db["config"]:
        db["config"]["secretKey"] = sensitiveParameters["_secretKey"]
        logger.info("Adding secret key to db!")

    # Ensure that any additional changes are committed
    transaction.commit()
