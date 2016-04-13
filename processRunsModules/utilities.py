"""
Shared utility functions used for organizing file structure, merging histograms, and posting data.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""
# Python 2/3 support
from __future__ import print_function

# General
import os
import time
from calendar import timegm
from subprocess import call
import shutil

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
        print("Error: cannot extract a time stamp for a combined file")

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

    filenamePrefix = os.path.join(currentDir, runDir, subsystem)

    # Store unmerged filenames and their unix timestamps in dictionary
    mergeDict = {}

    # Add uncombined .root files to mergeDict, then sort by timestamp
    for name in os.listdir(os.path.join(currentDir, runDir, subsystem)):
        if ".root" in name and "combined" not in name:
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
    if "templates" in dirPrefix:
        fileDestinationLabel = "templates"

    # An ending slash is needed so that rsync transfers the proper files (and not just the directory)
    sendDirectory = dirPrefix
    if not sendDirectory.endswith("/"):
        sendDirectory = sendDirectory + "/"

    if len(remoteSystems) != len(remoteFileLocations[fileDestinationLabel]):
        print("Number of remote systems is not equal to number of remote file locations. Skipping rsync operations!")
    else:
        for remoteSystem, remoteFileLocation in zip(remoteSystems, remoteFileLocations[fileDestinationLabel]):
            if not remoteFileLocation.endswith("/"):
                remoteFileLocation = remoteFileLocation + "/"

            print("Utilizing user %s to send %s files to %s on %s " % (username, fileDestinationLabel, remoteFileLocation, remoteSystem))

            # The chmod argument is explained here: https://unix.stackexchange.com/a/218165
            # The omit-dir-times does not update the timestamps on dirs (but still does on files in those dirs),
            # which fixes a number of errors thrown when transfering to PDSF
            # NOTE: Filenames of the form "*histos_*.root" are excluded from transfer! These are unprocessed files from the HLT and should not be transfered!
            #rsync -rvlth --chmod=ugo=rwX --omit-dir-times --exclude="*histos_*.root" data/ rehlers@pdsf.nersc.gov:/project/projectdirs/alice/www/emcalMonitoring/data/2015/
            rsyncCall = ["rsync", "-rvlth","--chmod=ugo=rwX", "--omit-dir-times", "--exclude=\"*histos_*.root\"", sendDirectory, username + "@" + remoteSystem + ":" + remoteFileLocation]
            print(rsyncCall)
            call(rsyncCall)

###################################################
# File moving utilites
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
            #print("name: %s" % name)
        
    return filesToMove

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

    # For each subsystem, loop over all files to move, and put them in subsystem directory
    for key in subsystemDict.keys():
        filesToMove = subsystemDict[key]
        if len(filesToMove) == 0:
            print("No files to move in %s" % key)
        for filename in filesToMove:
            # Extract time stamp and run number
            #print("filename: %s" % filename)
            #print(filesToMove)
            tempFilename = filename
            splitFilename = tempFilename.replace(".root","").split("_")
            #print("tempFilename: %s" % tempFilename)
            #print("splitFilename: ", splitFilename)
            if len(splitFilename) < 2:
                continue
            timeString = "_".join(splitFilename[2:])
            #print("timeString: ", timeString)

            # How to parse the timeString if desired
            #timeStamp = time.strptime(timeString, "%Y_%m_%d_%H_%M_%S")
            runString = splitFilename[1]
            runNumber = int(runString)

            # Create Run directory and subsystem directories as needed
            if not os.path.exists(os.path.join(dirPrefix, "Run" + str(runNumber))):
                os.makedirs( os.path.join(dirPrefix, "Run" + str(runNumber)) )
            if len(filesToMove) != 0 and not os.path.exists(os.path.join(dirPrefix, "Run" + str(runNumber), key)):
                os.makedirs(os.path.join(dirPrefix, "Run" + str(runNumber), key))
            
            newFilename = key + "hists." + timeString + ".root"

            oldPath = os.path.join(dirPrefix, tempFilename)
            newPath = os.path.join(dirPrefix, "Run" + str(runNumber), key, newFilename)
            print("Moving %s to %s" % (oldPath, newPath))
            # DON"T IMPORT MOVE. BAD CONSEQUENCES!!
            shutil.move(oldPath, newPath)

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
    
    moveFiles(subsystemDict, dirPrefix)

