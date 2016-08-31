#!/usr/bin/python

"""
Takes root files from the HLT viewer and organizes them into run directory and subsystem structure, 
then writes out histograms to webpage.  

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""
from __future__ import print_function

# ROOT includes
from ROOT import gROOT, TFile, TCanvas, TClass, TH1, TLegend, SetOwnership, TFileMerger, TList, gPad, TGaxis, gStyle, TProfile, TF1, TH1F, TBufferJSON

# Allow ROOT to be compatiable with Flask reloading in debug mode
# See: https://root.cern.ch/phpBB3/viewtopic.php?t=19594#p83968
from ROOT import std as stdROOT
stdROOT.__file__ = "dummyValueToAllowFlaskReloading"

# For batch mode when loading as a module
# https://root.cern.ch/phpBB3/viewtopic.php?t=3198
# Set batch mode
gROOT.SetBatch(True)

# Suppress print messages
gROOT.ProcessLine("gErrorIgnoreLevel = kWarning;")

# General includes
import os
import time
import sortedcontainers
import uuid
try:
    import cPickle as pickle
    #import pickle
except ImportError:
    import pickle

# Config
from config.processingParams import processingParameters

# Module includes
from processRunsModules import utilities
from processRunsModules import mergeFiles
from processRunsModules import qa
from processRunsModules import processingClasses

###################################################
def processRootFile(filename, outputFormatting, subsystem, qaContainer=None):
    """ Process a given root file, printing out all histograms.

    The function also applies QA as appropriate (either always applied or from a particular QA request) via
    :func:`~processRunsModules.qa.checkHist()`. It is expected that the qaContainer is only passed when
    processing a particular QA request (ie. it should *not* be passed when called by, for example,
    :func:`processAllRuns()`).

    Args:
        filename (str): The full path to the file to be processed.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png".
        subsystem (:class:`~subsystemProperties`): Contains information about the current subsystem.
        qaContainer (Optional[:class:`~processRunsModules.processingClasses.qaFunctionContainer`]): Contains information
            about the QA function and histograms, as well as the run being processed.

    Returns:
        list: Contains all of the names of the histograms that were printed.

    """
    # The file with the new histograms
    fIn = TFile(filename, "READ")

    # Read in available keys in the file
    keysInFile = fIn.GetListOfKeys()

    # Sorts keys so that we can have consistency when histograms are processed.
    keysInFile.Sort()

    # Get histograms and sort them if they do not exist in the subsystem
    # Only need to do this the first time for each run
    if not subsystem.hists:
        for key in keysInFile:
            classOfObject = gROOT.GetClass(key.GetClassName())
            #if classOfObject.InheritsFrom("TH1"):
            if classOfObject.InheritsFrom(TH1.Class()):
                # Create histogram object
                hist = processingClasses.histogramContainer(key.GetName())
                hist.hist = None
                hist.canvas = None
                hist.histType = classOfObject
                #hist.hist = key.ReadObj()
                #hist.canvas = TCanvas("{0}Canvas{1}{2}".format(hist.histName, subsystem.subsystem, subsystem.startOfRun),
                #                      "{0}Canvas{1}{2}".format(hist.histName, subsystem.subsystem, subsystem.startOfRun))
                # Shouldn't be needed, because I keep a reference to it
                #SetOwnership(hist.canvas, False)
                subsystem.histsInFile[hist.histName] = hist

                # Set nEvents
                #if subsystem.nEvents is None and "events" in hist.histName.lower():
                if "events" in hist.histName.lower():
                    subsystem.nEvents = key.ReadObj().GetBinContent(1)

        # Create the subsystem stacks
        qa.createHistogramStacks(subsystem)

        # Customize histogram traits
        qa.setHistogramOptions(subsystem)

        # Create histogram sorting groups
        if subsystem.histGroups == sortedcontainers.SortedDict():
            sortingSuccess = qa.createHistGroups(subsystem)
            if sortingSuccess is False:
                if processingParameters.beVerbose:
                    print("Subsystem {0} does not have a sorting function. Adding all histograms into one group!".format(subsystem.subsystem))

                if subsystem.fileLocationSubsystem != subsystem.subsystem:
                    selection = subsystem.subsystem
                else:
                    selection = ""
                print("selection: {0}".format(selection))
                subsystem.histGroups[subsystem.subsystem] = processingClasses.histogramGroupContainer(subsystem.subsystem + " Histograms", selection)

        # Finally classify into the groups and determine which functions to apply
        for hist in subsystem.histsAvailable.values():
            # Add the histogram name to the proper group
            classifiedHist = False
            for group in subsystem.histGroups.values():
                if group.selectionPattern in hist.histName:
                    group.histList.append(hist.histName)
                    classifiedHist = True
                    # Break so that we don't have multiple copies of hists!
                    break

            # TEMP
            print("{2} hist: {0} - classified: {1}".format(hist.histName, classifiedHist, subsystem.subsystem))

            if classifiedHist:
                # Determine the functions (qa and monitoring) to apply
                qa.findFunctionsForHist(subsystem, hist)
                # Add it to the subsystem
                subsystem.hists[hist.histName] = hist
            else:
                if processingParameters.beVerbose:
                    print("Skipping histogram {0} since it is not classifiable for subsystem {1}".format(hist.histName, subsystem.subsystem))

    # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
    # Start of run should unique to each run!
    canvas = TCanvas("{0}Canvas{1}{2}".format("processRuns", subsystem.subsystem, subsystem.startOfRun),
                     "{0}Canvas{1}{2}".format("processRuns", subsystem.subsystem, subsystem.startOfRun))
    # Loop over histograms and draw
    for histGroup in subsystem.histGroups.values():
        for histName in histGroup.histList:
            # Retrieve histogram and canvas
            hist = subsystem.hists[histName]
            hist.retrieveHistogram(fIn)
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

            # Setup and draw histogram
            # Turn off title, but store the value
            gStyle.SetOptTitle(0)
            hist.hist.Draw(hist.drawOptions)

            # Call functions for each hist
            #print("Functions to apply: {0}".format(hist.functionsToApply))
            for func in hist.functionsToApply:
                #print("Calling func: {0}".format(func))
                func(subsystem, hist)

            if qaContainer:
                # Various checks and QA that are performed on hists
                skipPrinting = qa.checkHist(hist.hist, qaContainer)

                # Skips printing out the histogram
                if skipPrinting == True:
                    if processingParameters.beVerbose:
                        print("Skip printing histogram {0}".format(hist.GetName()))
                    continue

            # Filter here for hists in the subsystem if subsystem != fileLocationSubsystem
            # Thus, we can filter the proper subsystems for subsystems that don't have their own data files
            #if subsystem.subsystem != subsystem.fileLocationSubsystem and subsystem.subsystem not in hist.GetName():
            #    continue

            # Save
            outputName = hist.histName
            # Replace any slashes with underscores to ensure that it can be used safely as a filename
            outputName = outputName.replace("/", "_")
            outputFilename = outputFormatting % (os.path.join(processingParameters.dirPrefix, subsystem.imgDir),
                                                 outputName,
                                                 processingParameters.fileExtension)
            hist.canvas.SaveAs(outputFilename)

            # Write BufferJSON
            jsonBufferFile = outputFormatting % (os.path.join(processingParameters.dirPrefix, subsystem.jsonDir),
                                                 outputName,
                                                 "json")
            #print("jsonBufferFile: {0}".format(jsonBufferFile))
            # GZip is performed by the web server, not here!
            with open(jsonBufferFile, "wb") as f:
                f.write(TBufferJSON.ConvertToJSON(canvas).Data())

            # Clear hist and canvas so that we can successfully save
            hist.hist = None
            hist.canvas = None


###################################################
def processQA(firstRun, lastRun, subsystemName, qaFunctionName):
    """ Processes a particular QA function over a set of runs.

    Usually invoked via the web app.

    Args:
        firstRun (str): The first (ie: lowest) run in the form "Run#". Ex: "Run123"
        lastRun (str): The last (ie: highest) run in the form "Run#". Ex: "Run123"
        subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        qaFunction (str): Name of the QA function to be executed.

    Returns:
        dict: The dict values contain paths to the printed histograms generated by the QA function. 
            The keys are from the labels in the qaContainer (usually the histogram names).

    """

    # Load general configuration options
    (fileExtension, beVerbose, forceReprocessing, forceNewMerge, sendData, remoteUsername, cumulativeMode, templateDataDirName, dirPrefix, subsystemList, subsystemsWithRootFilesToShow) = processingParameters.defineRunProperties()

    # Find all possible runs, and then select the runs between [firstRun, lastRun] (inclusive)
    runDirs = utilities.findCurrentRunDirs(dirPrefix)
    tempDirs = []
    for runDir in runDirs:
        if int(runDir.replace("Run","")) >= int(firstRun.replace("Run","")) and int(runDir.replace("Run","")) <= int(lastRun.replace("Run","")):
            tempDirs.append(runDir)

    # Reassign for clarity since that is the name used in other functions.
    runDirs = tempDirs

    # Find directories that exist for each subsystem
    subsystemRunDirDict = {}
    for subsystem in [subsystemName, "HLT"]:
        subsystemRunDirDict[subsystem] = []
        for runDir in runDirs:
            if os.path.exists(os.path.join(dirPrefix, runDir, subsystem)):
                subsystemRunDirDict[subsystem].append(runDir)

    # Create subsystem object
    subsystem = subsystemProperties(subsystem = subsystemName, runDirs = subsystemRunDirDict)

    # Create necessary dirs
    dataDir = os.path.join(dirPrefix, qaFunctionName)
    if not os.path.exists(dataDir):
        os.makedirs(dataDir)

    # Create objects to setup for processRootFile() call
    # QA class
    qaContainer = processingClasses.qaFunctionContainer(firstRun, lastRun, runDirs, qaFunctionName)

    # Formatting
    outputFormatting = os.path.join(dataDir, "%s.png")

    # Call processRootFile looping over all the runs found above
    for runDir in subsystem.runDirs:
        # Update the QA container
        qaContainer.currentRun = runDir
        qaContainer.filledValueInRun = False

        # Get length of run and set the value
        [mergeDict, runLength] = utilities.createFileDictionary(dirPrefix, runDir, subsystem.fileLocationSubsystem)
        qaContainer.runLength = runLength
        
        # Print current progress
        print("Processing run", qaContainer.currentRun)

        # Determine the proper combined file for input
        combinedFile = next(name for name in os.listdir(os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem)) if "combined" in name)
        inputFilename = os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem, combinedFile)
        if beVerbose:
            print(inputFilename)

        # Process the file
        outputHistNames = processRootFile(inputFilename, outputFormatting, subsystem = subsystem, qaContainer = qaContainer)

    # Need to remove the dirPrefix to get the proper URL
    # pathToRemove must end with a slash to ensure that the img path set below is valid
    pathToRemove = dirPrefix
    if not pathToRemove.endswith("/"):
        pathToRemove = pathToRemove + "/"

    # Print histograms from QA and setup the return value
    returnValues = {}
    canvas = TCanvas("canvas", "canvas")

    # Create root file to save out
    fOut = TFile(os.path.join(dataDir, qaContainer.qaFunctionName + ".root"), "RECREATE")

    for label, hist in qaContainer.getHistsDict().items():
        # Print the histogram
        hist.Draw()
        canvas.SaveAs(outputFormatting % label)

        # Write histogram to file
        hist.Write()

        # Set img path in the return value
        # Need to remove the pathToRemove defined above to ensure that the url doesn't include the directory
        # (ie. so it is /monitoring/protected, not /monitoring/protected/data)
        if beVerbose:
            print(outputFormatting)
            print(pathToRemove)
        returnValues[label] = outputFormatting.replace(pathToRemove, "") % label

    # Write root file
    fOut.Close()

    print("returnValues:", returnValues)

    return returnValues

###################################################
def validateAndCreateNewTimeSlice(run, subsystem, minTimeMinutes, maxTimeMinutes):
    # User filter time, in unix time. This makes it possible to compare to the startOfRun and endOfRun times
    minTimeCutUnix = minTimeMinutes*60 + subsystem.startOfRun
    maxTimeCutUnix = maxTimeMinutes*60 + subsystem.startOfRun

    # If max filter time is greater than max file time, merge up to and including last file
    if maxTimeCutUnix > subsystem.endOfRun:
        print("ERROR: Input max time exceeds data! It has been reset to the maximum allowed.")
        maxTimeMinutes = subsystem.runLength
        maxTimeCutUnix = subsystem.endOfRun

    # Return immediately if it is just a full time request
    # TODO: We will need to continue here if we change settings
    if minTimeMinutes == 0 and maxTimeMinutes == round(subsystem.runLength):
        return ("fullProcessing", False, None)

    # If input time range out of range, return 0
    print("Filtering time window! Min:{0}, Max: {1}".format(minTimeMinutes,maxTimeMinutes)) 
    if minTimeMinutes < 0:
        print("Minimum input time less than 0!")
        return (None, None, {"Request Error": ["Miniumum input time of \"{0}\" is less than 0!".format(minTimeMinutes)]})
    if minTimeCutUnix > maxTimeCutUnix:
        print("Max time must be greater than Min time!")
        return (None, None, {"Request Error": ["Max time of \"{0}\" must be greater than the min time of {1}!".format(maxTimeMinutes, minTimeMinutes)]})

    # Filter files by input time range
    filesToMerge = []
    for fileCont in subsystem.files.values():
        #print("fileCont.fileTime: {0}, minTimeCutUnix: {1}, maxTimeCutUnix: {2}".format(fileCont.fileTime, minTimeCutUnix, maxTimeCutUnix))
        print("fileCont.timeIntoRun (minutes): {0}, minTimeMinutes: {1}, maxTimeMinutes: {2}".format(round(fileCont.timeIntoRun/60), minTimeMinutes, maxTimeMinutes))
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
    
    #print("filesToMerge: {0}, times: {1}".format(filesToMerge, [x.fileTime for x in filesToMerge]))

    # Get min and max time stamp remaining
    minFilteredTimeStamp = filesToMerge[0].fileTime
    maxFilteredTimeStamp = filesToMerge[-1].fileTime

    # Check if it already exists and return if that is the case
    #print("subsystem.timeSlice: {0}".format(subsystem.timeSlices))
    for key, timeSlice in subsystem.timeSlices.iteritems():
        #print("minFilteredTimeStamp: {0}, maxFilteredTimeStamp: {1}, timeSlice.minTime: {2}, timeSlice.maxTime: {3}".format(minFilteredTimeStamp, maxFilteredTimeStamp, timeSlice.minTime, timeSlice.maxTime))
        if timeSlice.minTime == minFilteredTimeStamp and timeSlice.maxTime == maxFilteredTimeStamp:
            # Already exists - we don't need to remerge or reprocess
            return (key, False, None)

    # Determine index by UUID to ensure that there is no clash
    timeSlicesCont = processingClasses.timeSliceContainer(minFilteredTimeStamp,
                                                          maxFilteredTimeStamp,
                                                          subsystem.runLength,
                                                          filesToMerge)
    uuidDictKey = uuid.uuid4()
    subsystem.timeSlices[uuidDictKey] = timeSlicesCont

    return (uuidDictKey, True, None)

###################################################
def processTimeSlices(timeSliceRunNumber, minTimeRequested, maxTimeRequested, subsystemName, runs):
    """ Processes a given run using only data in a given time range (ie time slices).

    Usually invoked via the web app on a particular run page.

    Args:
        timeSliceRunNumber (int): The run number to be processed.
        minTimeRequested (int): The requested start time of the merge in minutes.
        maxTimeRequested (int): The requested end time of the merge in minutes.
        subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

    Returns:
        str: Path to the run page that was generated.

    """
    # Setup start runDir string of the form "Run#"
    runDir = "Run" + str(timeSliceRunNumber)
    print("Processing %s" % runDir)

    # Load run information
    if runDir in runs:
        run = runs[runDir]
    else:
        return {"Request Error": ["Requested Run {0}, but there is no run information on it! Please check that it is a valid run and retry in a few minutes!".format(timeSliceRunNumber)]}

    # Get subsystem
    subsystem = run.subsystems[subsystemName]
    print("subsystem.baseDir: {0}".format(subsystem.baseDir))

    # Setup dirPrefix
    dirPrefix = processingParameters.dirPrefix

    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    # While this function should be fast, we want this to run to ensure that time slices use the most recent data
    # available in performed on a run this is ongoing
    runDict = utilities.moveRootFiles(dirPrefix, processingParameters.subsystemList)

    # Little should happen here since few, if any files, should be moved
    processMovedFilesIntoRuns(runs, runDict)

    print("runLength: {0}".format(subsystem.runLength))

    # Validate and create time slice
    (timeSliceKey, newlyCreated, errors) = validateAndCreateNewTimeSlice(run, subsystem, minTimeRequested, maxTimeRequested)
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
                              cumulativeMode = processingParameters.cumulativeMode,
                              timeSlice = timeSlice)
    if errors:
        return errors

    # Print variables for log
    if processingParameters.beVerbose:
        print("minTimeRequested: {0}, maxTimeRequested: {1}".format(minTimeRequested, maxTimeRequested))
        print("subsystem.subsystem: {0}, subsystem.fileLocationSubsystem: {1}".format(subsystem.subsystem, subsystem.fileLocationSubsystem))

    # Generate the histograms
    outputFormattingSave = os.path.join("%s", "timeSlice.{0}.{1}.%s.%s.{2}".format(timeSlice.minTime,
                                                                                   timeSlice.maxTime,
                                                                                   processingParameters.fileExtension))
    if processingParameters.beVerbose:
        print("outputFormattingSave: {0}".format(outputFormattingSave))
        print("path: {0}".format(os.path.join(processingParameters.dirPrefix,
                                                   subsystem.baseDir,
                                                   timeSlice.filename.filename) ))
    outputHistNames = processRootFile(os.path.join(processingParameters.dirPrefix,
                                                   subsystem.baseDir,
                                                   timeSlice.filename.filename),
                                      outputFormattingSave, subsystem)

    print("Finished processing {0}!".format(run.prettyName))

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
    print("runLength filename: {0}".format(filename[-1]))

    # Create the subsystem
    showRootFiles = False
    if subsystem in processingParameters.subsystemsWithRootFilesToShow:
        showRootFiles = True
    runs[runDir].subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                              runDir = runDir,
                                                                              startOfRun = startOfRun,
                                                                              endOfRun = endOfRun,
                                                                              showRootFiles = showRootFiles,
                                                                              fileLocationSubsystem = fileLocationSubsystem)

    # Handle files
    files = sortedcontainers.SortedDict()
    for filename in filenames:
        files[utilities.extractTimeStampFromFilename(filenmae)] = processingClasses.fileContainer(filename, startOfRun)
    runs[runDir].subsystems[subsystem].files = files

    # Flag that there are new files
    runs[runDir].subsystems[subsystem].newFile = True

###################################################
def processMovedFilesIntoRuns(runs, runDict):
    for runDir in runDict:
        if runDir in runs:
            run = runs[runDir]
            # Update each subsystem and note that it needs to be reprocessed
            for subsystemName in processingParameters.subsystemList:
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
                    print("INFO: Previous EOR: {0}\tNew: {1}".format(subsystem.endOfRun, fileKeys[-1]))
                    subsystem.endOfRun = fileKeys[-1]
                else:
                    # Create a new subsystem
                    createNewSubsystemFromMergeInformation(runs, subsystemName, runDict, runDir)

        else:
            runs[runDir] = processingClasses.runContainer(runDir = runDir,
                                                          fileMode = processingParameters.cumulativeMode)
            # Add files and subsystems.
            # We are creating runs here, so we already have all the information that we need from moving the files
            for subsystem in processingParameters.subsystemList:
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
    dirPrefix = processingParameters.dirPrefix

    # Create runs list
    runs = sortedcontainers.SortedDict()
    if os.path.exists(os.path.join(dirPrefix, "objectStore.db")):
        # The objects exist, so just use the stored copy and update it.
        pass
    else:
        # The objects don't exist, so we need to create them.
        # This will be a slow process, so the results should be stored
        for runDir in utilities.findCurrentRunDirs(dirPrefix):
            # Create run object
            runs[runDir] = processingClasses.runContainer( runDir = runDir, 
                                                           fileMode = processingParameters.cumulativeMode)

        # Find files and create subsystems
        for runDir, run in runs.items():
            for subsystem in processingParameters.subsystemList:
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
                            print("WARNING: Could not create subsystem {0} in {1} due to lacking HLT files.".format(subsystem, runDir))
                        else:
                            print("WARNING: Could not create subsystem {0} in {1} due to lacking {0} and HLT files.".format(subsystem, runDir))
                        continue

                print("Creating subsystem {0} in {1}".format(subsystem, runDir))
                # Retrieve the files for a given directory
                [filenamesDict, runLength] = utilities.createFileDictionary(dirPrefix, runDir, fileLocationSubsystem)
                #print("runLength: {0}, filenamesDict: {1}".format(runLength, filenamesDict))
                sortedKeys = sorted(filenamesDict.keys())
                startOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[0]])
                endOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[-1]])
                #print("filenamesDict.keys(): {0}".format(filenamesDict.keys()))
                print("startOfRun: {0}, endOfRun: {1}, runLength: {2}".format(startOfRun, endOfRun, (endOfRun - startOfRun)/60))

                # Now create the subsystem
                showRootFiles = False
                if subsystem in processingParameters.subsystemsWithRootFilesToShow:
                    showRootFiles = True
                run.subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                                 runDir = run.runDir,
                                                                                 startOfRun = startOfRun,
                                                                                 endOfRun = endOfRun,
                                                                                 showRootFiles = showRootFiles,
                                                                                 fileLocationSubsystem = fileLocationSubsystem)

                # Handle files and create file containers
                files = sortedcontainers.SortedDict()

                for key in filenamesDict:
                    files[key] = processingClasses.fileContainer(filenamesDict[key], startOfRun)

                print("DEBUG: files length: {0}".format(len(files)))

                # And add the files to the subsystem
                # Since a run was just appended, accessing the last element should always be fine
                run.subsystems[subsystem].files = files

                # Add combined
                combinedFilename = [filename for filename in os.listdir(subsystemPath) if "combined" in filename and ".root" in filename]
                if len(combinedFilename) > 1:
                    print("ERROR: Number of combined files in {0} is {1}, but should be 1! Exiting!".format(runDir, len(combinedFilename)))
                    exit(0)
                if len(combinedFilename) == 1:
                    run.subsystems[subsystem].combinedFile = processingClasses.fileContainer(combinedFilename[0], startOfRun)
                else:
                    print("INFO: No combined file in {0}".format(runDir))
                        
    # Start of processing data
    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    runDict = utilities.moveRootFiles(dirPrefix, processingParameters.subsystemList)

    print("INFO: Files moved: {0}".format(runDict))

    # Now process the results from moving the files and add them into the runs list
    processMovedFilesIntoRuns(runs, runDict)

    # DEBUG
    print("DEBUG:")
    if processingParameters.beVerbose:
        for runDir in runs:
            for subsystem in runs[runDir].subsystems:
                print("{0}, {1} has nFiles: {2}".format(runDir, subsystem, len(runs[runDir].subsystems[subsystem].files)))

    # Merge histograms over all runs, all subsystems if needed. Results in one combined file per subdir.
    mergedRuns = mergeFiles.mergeRootFiles(runs, dirPrefix,
                                           processingParameters.forceNewMerge,
                                           processingParameters.cumulativeMode)

    # Determine which runs to process
    for runDir, run in runs.items():
        #for subsystem in subsystems:
        for subsystem in run.subsystems.values():
            # Process if there is a new file or if forceReprocessing
            if subsystem.newFile == True or processingParameters.forceReprocessing == True:
                # Process combined root file: plot histos and save in imgDir
                print("INFO: About to process {0}, {1}".format(runDir, subsystem.subsystem))
                #outputFormattingSave = os.path.join(subsystem.imgDir, "%s" + processingParameters.fileExtension) 
                outputFormattingSave = os.path.join("%s", "%s.%s") 
                processRootFile(os.path.join(processingParameters.dirPrefix, subsystem.combinedFile.filename),
                                outputFormattingSave,
                                subsystem)
            else:
                # We often want to skip this point since most runs will not need to be processed most times
                if beVerbose:
                    print("INFO: Don't need to process {0}. It has already been processed".format(runDir))

    # Save the dict out
    pickle.dump(runs, open(os.path.join(processingParameters.dirPrefix, "runs.p"), "wb"))
    #pickle.dump(runs["Run123456"], open(os.path.join(processingParameters.dirPrefix, "runs.p"), "wb"))
    
    print("INFO: Finished processing!")

    # Send data to pdsf via rsync
    if processingParameters.sendData == True:
        print("INFO: Preparing to send data")
        utilities.rsyncData(dirPrefix, processingParameters.remoteUsername, processingParameters.remoteSystems, processingParameters.remoteFileLocations)
        if templateDataDirName != None:
            utilities.rsyncData(templateDataDirName, processingParameters.remoteUsername, processingParameters.remoteSystems, processingParameters.remoteFileLocations)
        
# Allows the function to be invoked automatically when run with python while not invoked when loaded as a module
if __name__ == "__main__":
    # Process all of the run data
    processAllRuns()
    # Function calls that be used for debugging
    #processQA("Run246272", "Run246980", "EMC", "determineMedianSlope")

    ## Test processTimeSlices()
    ## TEMP
    #runs = pickle.load( open(os.path.join("data", "runs.p"), "rb") )
    ## ENDTEMP

    #print("\n\t\t0-4:")
    #returnValue = processTimeSlices(300005, 0, 4, "EMC", runs)
    #print("0-4 UUID: {0}".format(returnValue))

    #print("\n\t\t0-3:")
    #returnValue = processTimeSlices(300005, 0, 3, "EMC", runs)
    #print("0-3 UUID: {0}".format(returnValue))

    #print("\n\t\t0-3 repeat:")
    #returnValue = processTimeSlices(300005, 0, 3, "EMC", runs)
    #print("0-3 repeat UUID: {0}".format(returnValue))

    #print("\n\t\t1-4:")
    #returnValue = processTimeSlices(300005, 1, 4, "EMC", runs)
    #print("1-4 UUID: {0}".format(returnValue))

    #print("\n\t\t1-3:")
    #returnValue = processTimeSlices(300005, 1, 3, "EMC", runs)
    #print("1-3 UUID: {0}".format(returnValue))
