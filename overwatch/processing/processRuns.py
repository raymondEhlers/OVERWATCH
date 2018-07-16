#!/usr/bin/python

"""
Takes root files from the HLT viewer and organizes them into run directory and subsystem structure, 
then writes out histograms to webpage.  

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""
from __future__ import print_function
from future.utils import iteritems

# ROOT
import ROOT

# Allow ROOT to be compatiable with Flask reloading in debug mode.
# This onlly applies to Flask debug mode with ROOT 5.
# See: https://root-forum.cern.ch/t/pyroot-and-spyder-re-running-error/20926/5
# See: https://root.cern.ch/phpBB3/viewtopic.php?t=19594#p83968
ROOT.std.__file__ = "ROOT.std.py"

# For batch mode when loading as a module
# https://root.cern.ch/phpBB3/viewtopic.php?t=3198
# Set batch mode
ROOT.gROOT.SetBatch(True)

# Suppress print messages
ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kWarning;")

# General includes
import os
import hashlib
import uuid
# Python logging system
# See: https://stackoverflow.com/a/346501
import logging
# Setup logger
if __name__ == "__main__":
    # By not setting a name, we get everything!
    #logger = logging.getLogger("")
    # Alternatively, we could set processRuns to get everything derived from that
    #logger = logging.getLogger("processRuns")
    pass
else:
    # When imported, we just want it to take on it normal name
    logger = logging.getLogger(__name__)
    # Alternatively, we could set processRuns to get everything derived from that
    #logger = logging.getLogger("processRuns")

# ZODB
import BTrees.OOBTree
import transaction
import persistent

# Config
from ..base import config
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

# Module includes
from ..base import utilities
from . import mergeFiles
from . import qa
from . import processingClasses

###################################################
def processRootFile(filename, outputFormatting, subsystem, processingOptions = None, forceRecreateSubsystem = False, trendingContainer = None):
    """ Process a given root file, printing out all histograms.

    Args:
        filename (str): The full path to the file to be processed.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png".
        subsystem (:class:`~subsystemProperties`): Contains information about the current subsystem.

    Returns:
        list: Contains all of the names of the histograms that were printed.

    """
    # The file with the new histograms
    fIn = ROOT.TFile(filename, "READ")

    # Read in available keys in the file
    keysInFile = fIn.GetListOfKeys()

    # Sorts keys so that we can have consistency when histograms are processed.
    keysInFile.Sort()

    if forceRecreateSubsystem:
        # Clear the stored hist information so we can recreate (reprocess) the subsystem
        subsystem.resetContainer()

    # Get histograms and sort them if they do not exist in the subsystem
    # Only need to do this the first time for each run
    if not subsystem.hists:
        for key in keysInFile:
            classOfObject = ROOT.gROOT.GetClass(key.GetClassName())
            #if classOfObject.InheritsFrom("TH1"):
            if classOfObject.InheritsFrom(ROOT.TH1.Class()):
                # Create histogram object
                hist = processingClasses.histogramContainer(key.GetName())
                hist.hist = None
                hist.canvas = None
                hist.histType = classOfObject
                #hist.hist = key.ReadObj()
                #hist.canvas = ROOT.TCanvas("{0}Canvas{1}{2}".format(hist.histName, subsystem.subsystem, subsystem.startOfRun),
                #                           "{0}Canvas{1}{2}".format(hist.histName, subsystem.subsystem, subsystem.startOfRun))
                # Shouldn't be needed, because I keep a reference to it
                #ROOT.SetOwnership(hist.canvas, False)
                subsystem.histsInFile[hist.histName] = hist

                # Set nEvents
                #if subsystem.nEvents is None and "events" in hist.histName.lower():
                if "events" in hist.histName.lower():
                    subsystem.nEvents = key.ReadObj().GetBinContent(1)

        #logger.debug("pre  create additional histsAvailable: {}".format(", ".join(subsystem.histsAvailable.keys())))

        # Create additional histograms
        qa.createAdditionalHistograms(subsystem)

        #logger.debug("post create additional histsAvailable: {}".format(", ".join(subsystem.histsAvailable.keys())))

        # Create the subsystem stacks
        qa.createHistogramStacks(subsystem)

        # Customize histogram traits
        qa.setHistogramOptions(subsystem)

        # Create histogram sorting groups
        if not subsystem.histGroups:
            sortingSuccess = qa.createHistGroups(subsystem)
            if sortingSuccess is False:
                logger.debug("Subsystem {0} does not have a sorting function. Adding all histograms into one group!".format(subsystem.subsystem))

                if subsystem.fileLocationSubsystem != subsystem.subsystem:
                    selection = subsystem.subsystem
                else:
                    # NOTE: In addition to being a normal option, this ensures that the HLT will always catch all extra histograms from HLT files!
                    # However, having this selection for other subsystems is dangerous, because it will include many unrelated hists
                    selection = ""
                logger.info("selection: {0}".format(selection))
                subsystem.histGroups.append(processingClasses.histogramGroupContainer(subsystem.subsystem + " Histograms", selection))

        logger.debug("post groups histsAvailable: {}".format(", ".join(subsystem.histsAvailable.keys())))

        # Finally classify into the groups and determine which functions to apply
        for hist in subsystem.histsAvailable.values():
            # Add the histogram name to the proper group
            classifiedHist = False
            for group in subsystem.histGroups:
                if group.selectionPattern in hist.histName:
                    group.histList.append(hist.histName)
                    classifiedHist = True
                    # Break so that we don't have multiple copies of hists!
                    break

            # TEMP
            logger.info("{2} hist: {0} - classified: {1}".format(hist.histName, classifiedHist, subsystem.subsystem))

            if classifiedHist:
                # Determine the functions (qa and monitoring) to apply
                qa.findFunctionsForHist(subsystem, hist)
                # Determine the trending functions to apply
                if trendingContainer:
                    trendingContainer.findTrendingFunctionsForHist(hist)
                    print("trending container: {}, hist: {}, ")
                # Add it to the subsystem
                subsystem.hists[hist.histName] = hist
            else:
                logger.debug("Skipping histogram {0} since it is not classifiable for subsystem {1}".format(hist.histName, subsystem.subsystem))

    # Set the proper processing options
    # If it was passed in, it was from time slices
    if processingOptions is None:
        processingOptions = subsystem.processingOptions
    logger.debug("processingOptions: {0}".format(processingOptions))

    # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
    # Start of run should unique to each run!
    canvas = ROOT.TCanvas("{0}Canvas{1}{2}".format("processRuns", subsystem.subsystem, subsystem.startOfRun),
                          "{0}Canvas{1}{2}".format("processRuns", subsystem.subsystem, subsystem.startOfRun))
    # Loop over histograms and draw
    for histGroup in subsystem.histGroups:
        for histName in histGroup.histList:
            # Retrieve histogram and canvas
            hist = subsystem.hists[histName]
            retrievedHist = hist.retrieveHistogram(fIn = fIn, ROOT = ROOT)
            if not retrievedHist:
                logger.warning("Could not retrieve histogram for hist {}, histList: {}".format(hist.histName, hist.histList))
                continue
            processHist(subsystem = subsystem, hist = hist, canvas = canvas, outputFormatting = outputFormatting, processingOptions = processingOptions)

###################################################
def processTrending(outputFormatting, trending, processingOptions = None, forceRecreateSubsystem = False):
    # Set the proper processing options
    # If it was passed in, it was from time slices
    if processingOptions == None:
        processingOptions = trending.processingOptions
    logger.debug("processingOptions: {0}".format(processingOptions))

    # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
    canvas = ROOT.TCanvas("processTrendingCanvas", "processTrendingCanvas")

    logger.debug("trending.trendingObjects: {}".format([key for key in trending.trendingObjects.keys()]))
    logger.debug("trending.trendingObjects: {}".format(trending.trendingObjects["TPC"]))
    for subsystemName, subsystem in iteritems(trending.trendingObjects):
        logger.debug("{}: subsystem from trending: {}".format(subsystemName, subsystem))
        for name, trendingObject in iteritems(subsystem):
            hist = trendingObject.hist
            hist.retrieveHistogram(trending = trending, ROOT = ROOT)
            logger.debug("trendingObject: {}, hist: {}, hist.histName: {}, hist.hist: {}".format(trendingObject, hist, hist.histName, hist.hist))
            #logger.debug("entries: {}".format(hist.hist.GetEntries()))
            # TEMP - Check for entries!
            if hist.hist.InheritsFrom(ROOT.TH1.Class()):
                nonzeroBins = [index for index in range(0, hist.hist.GetXaxis().GetNbins()) if hist.hist.GetBinContent(index) > 0.]
            else:
                import ctypes
                x = ctypes.c_double(0.)
                y = ctypes.c_double(0.)
                nonzeroBins = []
                values = []
                for index in range(0, hist.hist.GetN()):
                    hist.hist.GetPoint(index, x, y)
                    values.append(y.value)
                    if y.value > 0:
                        nonzeroBins.append(index)
                logger.debug("nonzeroBins: {}".format(nonzeroBins))
                logger.debug("values: {}".format(values))
            # ENDTEMP
            processHist(subsystem = trending, hist = hist, canvas = canvas, outputFormatting = outputFormatting, processingOptions = processingOptions, subsystemName = subsystemName)

###################################################
def processHist(subsystem, hist, canvas, outputFormatting, processingOptions, subsystemName = None):
    # In the case of trending, we have to pass a separate subsystem name because the trending container
    # holds hists from various subsystems
    if subsystemName is None:
        subsystemName = subsystem.subsystem

    if hist.canvas is None:
        # Reset canvas and make it accessible through the hist object
        hist.canvas = canvas
        canvas.Clear()
        # Reset log status, since clear does not do this
        canvas.SetLogx(False)
        canvas.SetLogy(False)
        canvas.SetLogz(False)

    # Ensure we plot onto the right canvas
    hist.canvas.cd()

    # Apply projection functions
    # Must be done before drawing!
    for func in hist.projectionFunctionsToApply:
        logger.debug("Calling projection func: {0}".format(func))
        hist.hist = func(subsystem, hist, processingOptions)

    # Setup and draw histogram
    # Turn off title, but store the value
    ROOT.gStyle.SetOptTitle(0)
    logger.debug("hist: {}, hist.hist: {}".format(hist, hist.hist))
    hist.hist.Draw(hist.drawOptions)

    # Call functions for each hist
    #logger.debug("Functions to apply: {0}".format(hist.functionsToApply))
    for func in hist.functionsToApply:
        logger.debug("Calling func: {0}".format(func))
        func(subsystem, hist, processingOptions)

    logger.debug("histName: {}, hist: {}".format(hist.histName, hist.hist))
    #logger.debug("histName: {}, hist: {}, hist entries: {}".format(hist.histName, hist.hist, hist.hist.GetEntries()))

    # Apply trending functions
    print("hist {} trending objects: {}".format(hist.histName, hist.trendingObjects))
    for trendingObject in hist.trendingObjects:
        logger.debug("Filling trending object {}".format(trendingObject.name))
        trendingObject.fill(hist)
        #func(hist)

    # Filter here for hists in the subsystem if subsystem != fileLocationSubsystem
    # Thus, we can filter the proper subsystems for subsystems that don't have their own data files
    #if subsystem.subsystem != subsystem.fileLocationSubsystem and subsystem.subsystem not in hist.GetName():
    #    continue

    # Save
    outputName = hist.histName
    # Replace any slashes with underscores to ensure that it can be used safely as a filename
    outputName = outputName.replace("/", "_")
    outputFilename = outputFormatting % (os.path.join(processingParameters["dirPrefix"], subsystem.imgDir % {"subsystem" : subsystemName}),
                                         outputName,
                                         processingParameters["fileExtension"])
    logger.debug("Saving hist to {}".format(outputFilename))
    hist.canvas.SaveAs(outputFilename)

    # Write BufferJSON
    jsonBufferFile = outputFormatting % (os.path.join(processingParameters["dirPrefix"], subsystem.jsonDir % {"subsystem" : subsystemName}),
                                         outputName,
                                         "json")
    #logger.debug("jsonBufferFile: {0}".format(jsonBufferFile))
    # GZip is performed by the web server, not here!
    with open(jsonBufferFile, "wb") as f:
        f.write(ROOT.TBufferJSON.ConvertToJSON(canvas).Data().encode())

    # Clear hist and canvas so that we can successfully save
    hist.hist = None
    hist.canvas = None

###################################################
def compareProcessingOptionsDicts(inputProcessingOptions, processingOptions):
    """ Compare an input and existing processing options dicts and return True if all input options are the same values as in the existing options.

    NOTE:
        The existing processing options can have more than entries than the input. Only the values in the input are checked.
    
    """
    processingOptionsAreTheSame = True
    for key,val in iteritems(inputProcessingOptions):
        if key not in processingOptions:
            return (None, None, {"Processing option error": ["Key \"{0}\" in inputProcessingOptions ({1}) is not in subsystem processingOptions {2}!".format(key, inputProcessingOptions, processingOptions)]})
        if val != processingOptions[key]:
            processingOptionsAreTheSame = False
            break

    return processingOptionsAreTheSame

###################################################
def validateAndCreateNewTimeSlice(run, subsystem, minTimeMinutes, maxTimeMinutes, inputProcessingOptions):
    # User filter time, in unix time. This makes it possible to compare to the startOfRun and endOfRun times
    minTimeCutUnix = minTimeMinutes*60 + subsystem.startOfRun
    maxTimeCutUnix = maxTimeMinutes*60 + subsystem.startOfRun

    # If max filter time is greater than max file time, merge up to and including last file
    if maxTimeCutUnix > subsystem.endOfRun:
        logger.warning("Input max time exceeds data! It has been reset to the maximum allowed.")
        maxTimeMinutes = subsystem.runLength
        maxTimeCutUnix = subsystem.endOfRun

    # Return immediately if it is just a full time request with the normal processing options
    processingOptionsAreTheSame = compareProcessingOptionsDicts(inputProcessingOptions, subsystem.processingOptions)
    if minTimeMinutes == 0 and maxTimeMinutes == round(subsystem.runLength) and processingOptionsAreTheSame:
        return ("fullProcessing", False, None)

    # If input time range out of range, return 0
    logger.info("Filtering time window! Min:{0}, Max: {1}".format(minTimeMinutes,maxTimeMinutes)) 
    if minTimeMinutes < 0:
        logger.info("Minimum input time less than 0!")
        return (None, None, {"Request Error": ["Miniumum input time of \"{0}\" is less than 0!".format(minTimeMinutes)]})
    if minTimeCutUnix > maxTimeCutUnix:
        logger.info("Max time must be greater than Min time!")
        return (None, None, {"Request Error": ["Max time of \"{0}\" must be greater than the min time of {1}!".format(maxTimeMinutes, minTimeMinutes)]})

    # Filter files by input time range
    filesToMerge = []
    for fileCont in subsystem.files.values():
        #logger.info("fileCont.fileTime: {0}, minTimeCutUnix: {1}, maxTimeCutUnix: {2}".format(fileCont.fileTime, minTimeCutUnix, maxTimeCutUnix))
        logger.info("fileCont.timeIntoRun (minutes): {0}, minTimeMinutes: {1}, maxTimeMinutes: {2}".format(round(fileCont.timeIntoRun/60), minTimeMinutes, maxTimeMinutes))
        #if fileCont.fileTime >= minTimeCutUnix and fileCont.fileTime <= maxTimeCutUnix and fileCont.combinedFile == False:
        # It is important to make this check in such a way that we can round to the nearest minute.
        if round(fileCont.timeIntoRun/60) >= minTimeMinutes and round(fileCont.timeIntoRun/60) <= maxTimeMinutes and fileCont.combinedFile == False:
            # The file is in the time range, so we keep it
            filesToMerge.append(fileCont)

    # If filesToMerge is empty, then the time range has no files. We need to report as such
    if filesToMerge == []:
         return (None, None, {"Request Error": ["No files are available in requested range of {0}-{1}! Please make another request with a different range".format(minTimeMinutes, maxTimeMinutes)]})

    # Sort files by time
    filesToMerge.sort(key=lambda x: x.fileTime)
    
    #logger.info("filesToMerge: {0}, times: {1}".format(filesToMerge, [x.fileTime for x in filesToMerge]))

    # Get min and max time stamp remaining
    minFilteredTimeStamp = filesToMerge[0].fileTime
    maxFilteredTimeStamp = filesToMerge[-1].fileTime

    # Check if it already exists and return if that is the case
    #logger.info("subsystem.timeSlice: {0}".format(subsystem.timeSlices))
    for key, timeSlice in iteritems(subsystem.timeSlices):
        #logger.info("minFilteredTimeStamp: {0}, maxFilteredTimeStamp: {1}, timeSlice.minTime: {2}, timeSlice.maxTime: {3}".format(minFilteredTimeStamp, maxFilteredTimeStamp, timeSlice.minTime, timeSlice.maxTime))
        processingOptionsAreTheSame = compareProcessingOptionsDicts(inputProcessingOptions, timeSlice.processingOptions)
        if timeSlice.minUnixTimeAvailable == minFilteredTimeStamp and timeSlice.maxUnixTimeAvailable == maxFilteredTimeStamp and processingOptionsAreTheSame:
            # Already exists - we don't need to remerge or reprocess
            return (key, False, None)

    # Hash processing options so that we can compare
    # The hash is needed to ensure that different options with the same times don't overwrite each other!
    optionsHash = hashlib.sha1(str(inputProcessingOptions).encode()).hexdigest()
    # Determine index by UUID to ensure that there is no clash
    timeSliceCont = processingClasses.timeSliceContainer(minUnixTimeRequested = minTimeCutUnix,
                                                          maxUnixTimeRequested = maxTimeCutUnix,
                                                          minUnixTimeAvailable = minFilteredTimeStamp,
                                                          maxUnixTimeAvailable = maxFilteredTimeStamp,
                                                          startOfRun = subsystem.startOfRun,
                                                          filesToMerge = filesToMerge,
                                                          optionsHash = optionsHash)
    # Set the processing options in the time slice container
    for key, val in iteritems(inputProcessingOptions):
        timeSliceCont.processingOptions[key] = val

    uuidDictKey = str(uuid.uuid4())
    subsystem.timeSlices[uuidDictKey] = timeSliceCont

    return (uuidDictKey, True, None)

###################################################
def processTimeSlices(runs, timeSliceRunNumber, minTimeRequested, maxTimeRequested, subsystemName, inputProcessingOptions):
    """ Processes a given run using only data in a given time range (ie time slices).

    Usually invoked via the web app on a particular run page.

    Args:
        timeSliceRunNumber (str): The run dir to be processed.
        minTimeRequested (int): The requested start time of the merge in minutes.
        maxTimeRequested (int): The requested end time of the merge in minutes.
        subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

    Returns:
        str: Path to the run page that was generated.

    """
    # Setup start runDir string of the form "Run#"
    #runDir = "Run" + str(timeSliceRunNumber)
    runDir = timeSliceRunNumber
    logger.info("Processing %s" % runDir)

    # Load run information
    if runDir in runs:
        run = runs[runDir]
    else:
        return {"Request Error": ["Requested Run {0}, but there is no run information on it! Please check that it is a valid run and retry in a few minutes!".format(timeSliceRunNumber)]}

    # Get subsystem
    subsystem = run.subsystems[subsystemName]
    logger.info("subsystem.baseDir: {0}".format(subsystem.baseDir))

    # Setup dirPrefix
    dirPrefix = processingParameters["dirPrefix"]

    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    # While this function should be fast, we want this to run to ensure that time slices use the most recent data
    # available in performed on a run this is ongoing
    runDict = utilities.moveRootFiles(dirPrefix, processingParameters["subsystemList"])

    # Little should happen here since few, if any files, should be moved
    processMovedFilesIntoRuns(runs, runDict)

    logger.info("runLength: {0}".format(subsystem.runLength))

    # Validate and create time slice
    (timeSliceKey, newlyCreated, errors) = validateAndCreateNewTimeSlice(run, subsystem, minTimeRequested, maxTimeRequested, inputProcessingOptions)
    if errors:
        return errors
    # It has already been merged and processed
    if not newlyCreated:
        # This is the UUID
        return timeSliceKey

    timeSlice = subsystem.timeSlices[timeSliceKey]

    # Merge only the partial run.
    # Return if there were errors in merging
    errors = mergeFiles.merge(dirPrefix, run, subsystem,
                              cumulativeMode = processingParameters["cumulativeMode"],
                              timeSlice = timeSlice)
    if errors:
        return errors

    # Print variables for log
    logger.debug("minTimeRequested: {0}, maxTimeRequested: {1}".format(minTimeRequested, maxTimeRequested))
    logger.debug("subsystem.subsystem: {0}, subsystem.fileLocationSubsystem: {1}".format(subsystem.subsystem, subsystem.fileLocationSubsystem))

    # Generate the histograms
    outputFormattingSave = os.path.join("%s", "{0}.%s.%s".format(timeSlice.filenamePrefix))
    logger.debug("outputFormattingSave: {0}".format(outputFormattingSave))
    logger.debug("path: {0}".format(os.path.join(processingParameters["dirPrefix"],
                                               subsystem.baseDir,
                                               timeSlice.filename.filename) ))
    logger.debug("timeSlice.processingOptions: {0}".format(timeSlice.processingOptions))
    outputHistNames = processRootFile(os.path.join(processingParameters["dirPrefix"],
                                                   subsystem.baseDir,
                                                   timeSlice.filename.filename),
                                      outputFormattingSave, subsystem,
                                      processingOptions = timeSlice.processingOptions)

    logger.info("Finished processing {0}!".format(run.prettyName))

    # No errors, so return the key
    return timeSliceKey

###################################################
def createNewSubsystemFromMergeInformation(runs, subsystem, runDict, runDir):
    """ Creates a new subsystem based on the information from the merge. """
    if subsystem in runDict.subsystems:
        fileLocationSubsystem = subsystem
    else:
        if "HLT" in runDict.subsystems:
            fileLocationSubsystem = "HLT"
        else:
            # Cannot create subsystem, since the HLT doesn't exist as a fall back
            return 1

    filenames = sorted(runDict[runDir].subsystems[fileLocationSubsystem])
    startOfRun = utilities.extractTimeStampFromFilename(filenames[0])
    endOfRun = utilities.extractTimeStampFromFilename(filenames[-1])
    logger.info("runLength filename: {0}".format(filenames[-1]))

    # Create the subsystem
    showRootFiles = False
    if subsystem in processingParameters["subsystemsWithRootFilesToShow"]:
        showRootFiles = True
    runs[runDir].subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                              runDir = runDir,
                                                                              startOfRun = startOfRun,
                                                                              endOfRun = endOfRun,
                                                                              showRootFiles = showRootFiles,
                                                                              fileLocationSubsystem = fileLocationSubsystem)

    # Handle files
    subsystemFiles = runs[runDir].subsystems[subsystem].files
    for filename in filenames:
        subsystemFiles[utilities.extractTimeStampFromFilename(filename)] = processingClasses.fileContainer(filename, startOfRun)
    #runs[runDir].subsystems[subsystem].files = files

    # Flag that there are new files
    runs[runDir].subsystems[subsystem].newFile = True

###################################################
def processMovedFilesIntoRuns(runs, runDict):
    for runDir in runDict:
        if runDir in runs:
            run = runs[runDir]
            # Update each subsystem and note that it needs to be reprocessed
            for subsystemName in processingParameters["subsystemList"]:
                if subsystemName in runs.subsystems:
                    # Update the existing subsystem
                    subsystem = run.subsystems[subsystemName]
                    subsystem.newFile = True
                    for filename in runDict[runDir][subsystem]:
                        subsystem.files[utilities.extractTimeStampFromFilename(filename)] = processingClasses.fileContainer(filename = filename, startOfRun = subsystem.startOfRun)

                    # Update time stamps
                    fileKeys = subsystem.files.keys()
                    # This should rarely change, but in principle we could get a new file that we missed.
                    subsystem.startOfRun = fileKeys[0]
                    logger.info("Previous EOR: {0}\tNew: {1}".format(subsystem.endOfRun, fileKeys[-1]))
                    subsystem.endOfRun = fileKeys[-1]
                else:
                    # Create a new subsystem
                    createNewSubsystemFromMergeInformation(runs, subsystemName, runDict, runDir)

        else:
            runs[runDir] = processingClasses.runContainer(runDir = runDir,
                                                          fileMode = processingParameters["cumulativeMode"],
                                                          hltMode = runDict[runDir]["hltMode"])
            # Add files and subsystems.
            # We are creating runs here, so we already have all the information that we need from moving the files
            for subsystem in processingParameters["subsystemList"]:
                createNewSubsystemFromMergeInformation(runs, subsystem, runDict, runDir)

###################################################
def processAllRuns():
    """ Process all available data and write out individual run pages and a run list.

    This function moves all data that has been received by the HLT, categorizes the data by subsystem
    and puts it into a directory structure, prints it out applying the proper always applied QA
    functions, and then writes out web pages for each individual run, as well as a run list index
    which allows access to all runs.
    Each run will only be processed if necessary (for example, if there is new data) or if it is
    specifically set to reprocess in the configuration files.
    This function drives all of the processing, except for functions that are specifically
    requested by a user through the web app (ie. QA and time slices).

    This is the main function to process data, and should be run repeatedly with a short period
    to ensure that data is processed in a timely manner. This function also can handle exporting
    the data to another system, such as PDSF, via rsync.

    Note:
        Configuration is set in the class :class:`config.processingParams.processingParameters`
        instead of via arguments to this function. This allows it to be easily invoked
        via ``python processRuns.py`` in the terminal.

    Args:
        None: See the note above.

    Returns:
        None

    """
    dirPrefix = processingParameters["dirPrefix"]

    # Get the database
    (dbRoot, connection) = utilities.getDB(processingParameters["databaseLocation"])

    # Create runs list
    if "runs" in dbRoot:
        # The objects exist, so just use the stored copy and update it.
        logger.info("Utilizing existing database!")
        runs = dbRoot["runs"]

        # Files which were new are marked as such from the previous run,
        # They are not anymore, so we mark them as processed
        for runDir,run in runs.items():
            for subsystemName, subsystem in run.subsystems.items():
                if subsystem.newFile:
                    subsystem.newFile = False
    else:
        # Create the runs tree to store the information
        dbRoot["runs"] = BTrees.OOBTree.BTree()
        runs = dbRoot["runs"]

        # The objects don't exist, so we need to create them.
        # This will be a slow process, so the results should be stored
        for runDir in utilities.findCurrentRunDirs(dirPrefix):
            # Create run object
            runs[runDir] = processingClasses.runContainer( runDir = runDir, 
                                                           fileMode = processingParameters["cumulativeMode"])

        # Find files and create subsystems
        for runDir, run in runs.items():
            for subsystem in processingParameters["subsystemList"]:
                # Skip trending subsystem here
                #if subsystem == "TDG":
                #    continue

                # If subsystem exists, then create file containers 
                subsystemPath = os.path.join(dirPrefix, runDir, subsystem)
                if os.path.exists(subsystemPath):
                    fileLocationSubsystem = subsystem
                else:
                    if os.path.exists(os.path.join(dirPrefix, runDir, "HLT")):
                        fileLocationSubsystem = "HLT"
                        # Define subsystem path properly for this data arrangement
                        subsystemPath = subsystemPath.replace(subsystem, "HLT")
                    else:
                        # Cannot create subsystem, since the HLT doesn't exist as a fall back
                        if subsystem == "HLT":
                            logger.warning("Could not create subsystem {0} in {1} due to lacking HLT files.".format(subsystem, runDir))
                        else:
                            logger.warning("Could not create subsystem {0} in {1} due to lacking {0} and HLT files.".format(subsystem, runDir))
                        continue

                logger.info("Creating subsystem {0} in {1}".format(subsystem, runDir))
                # Retrieve the files for a given directory
                [filenamesDict, runLength] = utilities.createFileDictionary(dirPrefix, runDir, fileLocationSubsystem)
                #logger.info("runLength: {0}, filenamesDict: {1}".format(runLength, filenamesDict))
                sortedKeys = sorted(filenamesDict.keys())
                startOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[0]])
                endOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[-1]])
                #logger.info("filenamesDict.values(): {0}".format(filenamesDict.values()))
                logger.info("startOfRun: {0}, endOfRun: {1}, runLength: {2}".format(startOfRun, endOfRun, (endOfRun - startOfRun)/60))

                # Now create the subsystem
                showRootFiles = False
                if subsystem in processingParameters["subsystemsWithRootFilesToShow"]:
                    showRootFiles = True
                run.subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                                 runDir = run.runDir,
                                                                                 startOfRun = startOfRun,
                                                                                 endOfRun = endOfRun,
                                                                                 showRootFiles = showRootFiles,
                                                                                 fileLocationSubsystem = fileLocationSubsystem)

                # Handle files and create file containers
                subsystemFiles = run.subsystems[subsystem].files

                # And add the files to the subsystem
                for key in filenamesDict:
                    subsystemFiles[key] = processingClasses.fileContainer(filenamesDict[key], startOfRun)

                logger.debug("Files length: {0}".format(len(subsystemFiles)))

                # Add combined
                combinedFilename = [filename for filename in os.listdir(subsystemPath) if "combined" in filename and ".root" in filename]
                if len(combinedFilename) > 1:
                    logger.critical("Number of combined files in {0} is {1}, but should be 1! Exiting!".format(runDir, len(combinedFilename)))
                    exit(0)
                if len(combinedFilename) == 1:
                    run.subsystems[subsystem].combinedFile = processingClasses.fileContainer(os.path.join(runDir, fileLocationSubsystem, combinedFilename[0]), startOfRun)
                else:
                    logger.info("No combined file in {0}".format(runDir))

        # Commit any changes made to the database
        transaction.commit()

    # Create trending if necessary
    if "trending" not in dbRoot and processingParameters["trending"]:
        dbRoot["trending"] = BTrees.OOBTree.BTree()

    # Create configuration list
    if "config" not in dbRoot:
        dbRoot["config"] = persistent.mapping.PersistentMapping()

    logger.info("runs: {0}".format(list(runs.keys())))

    # Start of processing data
    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    runDict = utilities.moveRootFiles(dirPrefix, processingParameters["subsystemList"])

    logger.info("Files moved: {0}".format(runDict))

    # Now process the results from moving the files and add them into the runs list
    processMovedFilesIntoRuns(runs, runDict)

    # Potentially helpful debug information
    if processingParameters["debug"]:
        for runDir in runs.keys():
            for subsystem in runs[runDir].subsystems.keys():
                logger.debug("{0}, {1} has nFiles: {2}".format(runDir, subsystem, len(runs[runDir].subsystems[subsystem].files)))

    # Merge histograms over all runs, all subsystems if needed. Results in one combined file per subdir.
    mergedRuns = mergeFiles.mergeRootFiles(runs, dirPrefix,
                                           processingParameters["forceNewMerge"],
                                           processingParameters["cumulativeMode"])

    # Setup trending
    if processingParameters["trending"]:
        trendingContainer = processingClasses.trendingContainer(dbRoot["trending"])
        # Subsystem specific trending histograms
        # TDG corresponds to general trending histograms (perhaps between two subsystem)
        for subsystem in processingParameters["subsystemList"] + ["TDG"]:
            trendingObjects = qa.defineTrendingObjects(subsystem)
            trendingContainer.addSubsystemTrendingObjects(subsystem, trendingObjects, forceRecreateSubsystem = processingParameters["forceRecreateSubsystem"])
    else:
        trendingContainer = None

    # Determine which runs to process
    outputFormattingSave = os.path.join("%s", "%s.%s")
    for runDir, run in runs.items():
        #for subsystem in subsystems:
        for subsystem in run.subsystems.values():
            # Process if there is a new file or if forceReprocessing
            logger.debug("runDir: {}, reprocessRuns: {}".format(runDir.replace("Run", ""), processingParameters["forceReprocessRuns"]))
            if subsystem.newFile or processingParameters["forceReprocessing"] or int(runDir.replace("Run","")) in processingParameters["forceReprocessRuns"]:
                # Process combined root file: plot histos and save in imgDir
                logger.info("About to process {0}, {1}".format(run.prettyName, subsystem.subsystem))
                processRootFile(os.path.join(processingParameters["dirPrefix"], subsystem.combinedFile.filename),
                                outputFormattingSave,
                                subsystem,
                                forceRecreateSubsystem = processingParameters["forceRecreateSubsystem"],
                                trendingContainer = trendingContainer)
                if trendingContainer and not trendingContainer.updateToDate:
                    # Loop over process root file with various until it is up to date
                    pass
            else:
                # We often want to skip this point since most runs will not need to be processed most times
                logger.debug("Don't need to process {0}. It has already been processed".format(run.prettyName))

        # Commit after we have successfully processed a run
        transaction.commit()

    logger.info("Finished processing!")

    if trendingContainer:
        # Run trending once we have gotten to the most recent run
        logger.info("About to process trending")
        processTrending(outputFormatting = outputFormattingSave,
                        trending = trendingContainer,
                        forceRecreateSubsystem = processingParameters["forceRecreateSubsystem"])

        # Commit after we have successfully processed the trending
        transaction.commit()

    logger.info("Finishing trending")

    # Send data to pdsf via rsync
    if processingParameters["sendData"]:
        logger.info("Preparing to send data")
        utilities.rsyncData(dirPrefix, processingParameters["remoteUsername"], processingParameters["remoteSystems"], processingParameters["remoteFileLocations"])

    # Update receiver last modified time if the log exists
    receiverLogFileDir = os.path.join("deploy")
    if os.path.exists(receiverLogFileDir):
        receiverLogFilePath = os.path.join(receiverLogFileDir,
                                           next(( name for name in os.listdir(receiverLogFileDir) if "Receiver.log" in name), ""))
        logger.debug("receiverLogFilePath: {0}".format(receiverLogFilePath))

        # Add the receiver last modified time
        if receiverLogFilePath and os.path.exists(receiverLogFilePath):
            logger.debug("Updating receiver log last modified time!")
            receiverLogLastModified = os.path.getmtime(receiverLogFilePath)
            dbRoot["config"]["receiverLogLastModified"] = receiverLogLastModified

    # Add users and secret key if debugging
    # This needs to be done manually if deploying, since this requires some care to ensure that everything is configured properly
    if processingParameters["debug"]:
        utilities.updateDBSensitiveParameters(dbRoot)

    # Ensure that any additional changes are committed
    transaction.commit()
    connection.close()

# Allows the function to be invoked automatically when run with python while not invoked when loaded as a module
if __name__ == "__main__":
    pass
