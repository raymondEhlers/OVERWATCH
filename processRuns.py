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
from collections import OrderedDict
import sortedcontainers

# Config
from config.processingParams import processingParameters

# Module includes
from processRunsModules import utilities
from processRunsModules import generateWebPages
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
        qaContainer (Optional[:class:`~processRunsModules.qa.qaFunctionContainer`]): Contains information
            about the QA function and histograms, as well as the run being processed.

    Returns:
        list: Contains all of the names of the histograms that were printed.

    """
    # Seems to be required for pyroot?
    gROOT.Reset()

    # Use to write out
    canvas = TCanvas("processRootFilecanvas", "processRootFilecanvas")

    # The file with the new histograms
    fIn = TFile(filename, "READ")

    # Read in available keys in the file
    keysInFile = fIn.GetListOfKeys();

    # Save output names for writing to webpage later
    outputHistNames = [ ]

    # If a qaContainer does not exist, then create one, but do not specify the function
    # By not specifying the function, it denotes that this container is just being used to hold
    # histograms.
    # TODO: A better approach should be taken!
    if qaContainer is None:
        qaContainer = qa.qaFunctionContainer("Run000000", "Run000000", ["Run000000"], "")

    # Find the histogram containing the number of events (if it exists)
    for key in keysInFile:
        if "histEvents" in key.GetName():
            nEventsFromFile = key.ReadObj()
            # If we subtract two files with the same number of events, then we would divide by 0.
            # So we require there to be more than 0 events.
            if nEventsFromFile.GetBinContent(1) > 0:
                # Need to create a new hist to avoid a memory leak!
                nEvents = TH1F("nEvents", "nEvents", 1, 0, 1)
                nEvents.Fill(0.5, nEventsFromFile.GetBinContent(1))
                print("NEvents Hist name: {0}".format(key.GetName()))
                print("NEvents from file: {0}".format(nEventsFromFile.GetBinContent(1)))
                print("NEvents: {0}".format(nEvents.GetBinContent(1)))
                qaContainer.addHist(nEvents, "NEvents")

    # Sorts keys so that we can have consistency when histograms are processed.
    keysInFile.Sort()

    # Useful information: https://root.cern.ch/phpBB3/viewtopic.php?t=11049
    for key in keysInFile:
        classOfObject = gROOT.GetClass(key.GetClassName())
        # Ensure that we only take histograms
        if classOfObject.InheritsFrom("TH1"):
            hist = key.ReadObj()

            # Now set options, draw and save
            drawOptions = ""

            # Allows curotmization of draw options for 2D hists
            if classOfObject.InheritsFrom("TH2"):
                drawOptions = "colz"
                gPad.SetLogz()
            
            # Setup and draw histogram
            # Turn off title, but store the value
            gStyle.SetOptTitle(0)
            hist.Draw(drawOptions)
            canvas.Update()
            
            # Various checks and QA that are performed on hists
            skipPrinting = qa.checkHist(hist, qaContainer)

            # Skips printing out the histogram
            if skipPrinting == True:
                if processingParameters.beVerbose == True and qaContainer.qaFunctionName == "":
                    print("Skip printing histogram {0}".format(hist.GetName()))
                continue

            # Filter here for hists in the subsystem if subsystem != fileLocationSubsystem
            # Thus, we can filter the proper subsystems for subsystems that don't have their own data files
            if subsystem.subsystem != subsystem.fileLocationSubsystem and subsystem.subsystem not in hist.GetName():
                continue

            # Add to our list for printing to the webpage later
            # We only want to do this if we are actually printing the histogram
            outputName = hist.GetName()
            # Replace any slashes with underscores to ensure that it can be used safely as a filename
            outputName = outputName.replace("/", "_")
            outputHistNames.append(outputName)

            # Save
            outputFilename = outputFormatting % outputName
            canvas.SaveAs(outputFilename)

            # Write BufferJSON
            jsonBufferFile = outputFilename.replace("img", "json").replace("png","json")
            print("jsonBufferFile: {0}".format(jsonBufferFile))
            # GZip is performed by the web server, not here!
            with open(jsonBufferFile, "wb") as f:
                f.write(TBufferJSON.ConvertToJSON(canvas).Data())

    # Remove NEvents so that it doesn't get printed
    if qaContainer.getHist("NEvents") is not None:
        if processingParameters.beVerbose == True:
            print("Removing NEvents QA hist!")
        qaContainer.removeHist("NEvents")

    # Add to output names if hists are created
    if qaContainer.getHists() != []:
        print("hists:", qaContainer.getHists())
        # Only print QA hists if we are specifically using a QA function
        if qaContainer.qaFunctionName is not "":
            for hist in qaContainer.getHists():
                outputHistNames.append(hist.GetName())

    return outputHistNames 

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
    qaContainer = qa.qaFunctionContainer(firstRun, lastRun, runDirs, qaFunctionName)

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
def processPartialRun(timeSliceRunNumber, minTimeRequested, maxTimeRequested, subsystemName):
    """ Processes a given run using only data in a given time range.

    Usually invoked via the web app on a particular run page.

    Args:
        timeSliceRunNumber (int): The run number to be processed.
        minTimeRequested (int): The requested start time of the merge in minutes.
        maxTimeRequested (int): The requested end time of the merge in minutes.
        subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).

    Returns:
        str: Path to the run page that was generated.

    """
    # Load general configuration options
    (fileExtension, beVerbose, forceReprocessing, forceNewMerge, sendData, remoteUsername, cumulativeMode, templateDataDirName, dirPrefix, subsystemList, subsystemsWithRootFilesToShow) = processingParameters.defineRunProperties()

    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    # While this function should be fast, we want this to run to ensure that time slices use the most recent data
    # available in performed on a run this is ongoing
    utilities.moveRootFiles(dirPrefix, subsystemList)

    # Setup start runDir string of the form "Run#"
    runDir = "Run" + str(timeSliceRunNumber)
    print("Processing %s" % runDir)

    # Create run dir dict structure necessary for the subsystem properties class
    # Find directories that exist for each subsystem
    subsystemRunDirDict = {}
    for subsystem in [subsystemName, "HLT"]:
        subsystemRunDirDict[subsystem] = []
        if os.path.exists(os.path.join(dirPrefix, runDir, subsystem)):
            subsystemRunDirDict[subsystem].append(runDir)

    # Setup subsystem properties
    subsystem = subsystemProperties(subsystem = subsystemName, runDirs = subsystemRunDirDict)

    # Merge only the partial run.
    (actualTimeBetween, inputFilename) = mergeFiles.merge(dirPrefix, runDir, subsystem.fileLocationSubsystem, cumulativeMode, minTimeRequested, maxTimeRequested)

    # Setup necessary directories
    baseDirName = inputFilename.replace(".root", "")
    if not os.path.exists(baseDirName):
        os.makedirs(baseDirName)

    imgDir = os.path.join(baseDirName, "img")
    if not os.path.exists(imgDir):
        os.makedirs(imgDir)

    # Setup templates
    # Determine template dirPrefix
    if templateDataDirName != None:
        templateDataDirPrefix = baseDirName.replace(os.path.basename(dirPrefix), templateDataDirName)
        # Create directory to store the templates if necessary
        if not os.path.exists(templateDataDirPrefix):
            os.makedirs(templateDataDirPrefix)

    # Print variables for log
    print("baseDirName: %s" % baseDirName)
    print("imgDir: %s" % imgDir)
    print("templateDataDirPrefix: %s" % templateDataDirPrefix)
    print("actualTimeBetween: %d" % actualTimeBetween)
    if beVerbose:
        print("minTimeRequested: %d" % minTimeRequested)
        print("maxTimeRequested: %d" % maxTimeRequested)
        print("subsystem.subsystem: %s" % subsystem.subsystem)
        print("subsystem.fileLocationSubsystem: %s" % subsystem.fileLocationSubsystem)

    # Generate the histograms
    outputFormattingSave = os.path.join(imgDir, "%s") + fileExtension
    if beVerbose:
        print("outputFormattingSave: %s" % outputFormattingSave)
    outputHistNames = processRootFile(inputFilename, outputFormattingSave, subsystem)

    # This func is mostly used just for the properties of the output
    # We do not need the precise files that are being merged.
    [mergeDict, maxTimeMinutes] = utilities.createFileDictionary(dirPrefix, runDir, subsystem.fileLocationSubsystem)

    # Setup to write output page
    outputFormattingWeb =  os.path.join("img", "%s") + fileExtension
    # timeKeys[0] is the start time of the run in unix time
    timeKeys = sorted(mergeDict.keys())

    # Generate the output html, writing out how long was merged
    generateWebPages.writeToWebPage(baseDirName, runDir, subsystem.subsystem, outputHistNames, outputFormattingWeb, timeKeys[0], maxTimeMinutes, minTimeRequested, maxTimeRequested, actualTimeBetween)
    if templateDataDirName != None:
        # templateDataDirPrefix is already set to the time slice dir, so we can just use it.
        if not os.path.exists(templateDataDirPrefix):
            os.makedirs(templateDataDirPrefix)
        generateWebPages.writeToWebPage(templateDataDirPrefix, runDir, subsystem.subsystem, outputHistNames, outputFormattingWeb, timeKeys[0], maxTimeMinutes, minTimeRequested, maxTimeRequested, actualTimeBetween, generateTemplate = True)

    # We don't need to write to the main webpage since this is an inner page that would not show up there anyway

    # Return the path to the file
    returnPath = os.path.join(baseDirName, subsystem.subsystem + "output.html")
    returnPath = returnPath[returnPath.find(dirPrefix) + len(dirPrefix):]
    # Remove leading slash if it is present
    if returnPath[0] == "/":
        returnPath = returnPath[1:]

    print("Finished processing run %i!" % timeSliceRunNumber)

    if beVerbose:
        print(returnPath)
    return returnPath

def createNewSubsystemFromMergeInformation(runs, subsystem, runDict, runDir):
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
    runLength = utilities.extractTimeStampFromFilename(filenames[-1])

    # Create the subsystem
    showRootFiles = False
    if subsystem in processingParameters.subsystemsWithRootFilesToShow:
        showRootFiles = True
    runs[runDir].subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                              runDir = runDir,
                                                                              startOfRun = startOfRun,
                                                                              runLength = runLength,
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
    # Load general configuration options
    #(fileExtension, beVerbose, forceReprocessing, forceNewMerge, sendData, remoteUsername, cumulativeMode, templateDataDirName, dirPrefix, subsystemList, subsystemsWithRootFilesToShow) = processingParameters.defineRunProperties()

    dirPrefix = processingParameters.dirPrefix

    # Setup before processing data
    # Determine templateDataDirPrefix
    if processingParameters.templateDataDirName != None:
        templateDataDirPrefix = os.path.join(os.path.dirname(dirPrefix), processingParameters.templateDataDirName)
        print("templateDataDirPrefix:", templateDataDirPrefix)
        # Create directory to store the templates if necessary
        if not os.path.exists(templateDataDirPrefix):
            os.makedirs(templateDataDirPrefix)

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
                        subsystemPath.replace(subsystem, "HLT")
                    else:
                        # Cannot create subsystem, since the HLT doesn't exist as a fall back
                        print("Could not create subsystem {0} in {1} due to lacking HLT files.".format(subsystem, runDir))
                        continue

                print("Creating subsystem {0} in {1}".format(subsystem, runDir))
                # Retrieve the files for a given directory
                [filenamesDict, runLength] = utilities.createFileDictionary(dirPrefix, runDir, fileLocationSubsystem)
                startOfRun = utilities.extractTimeStampFromFilename(filenamesDict[filenamesDict.keys()[0]])

                # Now create the subsystem
                showRootFiles = False
                if subsystem in processingParameters.subsystemsWithRootFilesToShow:
                    showRootFiles = True
                run.subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                                 runDir = run.runDir,
                                                                                 startOfRun = startOfRun,
                                                                                 runLength = runLength,
                                                                                 showRootFiles = showRootFiles,
                                                                                 fileLocationSubsystem = fileLocationSubsystem)

                # Handle files and create file containers
                files = sortedcontainers.SortedDict()

                for key in filenamesDict:
                    files[key] = processingClasses.fileContainer(filenamesDict[key], startOfRun)

                print("files length: {0}".format(len(files)))

                # Get filenames from dict
                #filenames = [filenamesDict[key] for key in filenamesDict]
                #filenames.sort()
                #print("filenames length: {0}".format(len(filenames)))
                # Add combined files, which are also valid files
                #filenames += [filename for filename in os.listdir(subsystemPath) if "combined" in filename and ".root"in filename]
                #print("With combined - filenames length: {0}".format(len(filenames)))

                # Create file containers
                #for filename in filenames:
                #    files.append(processingClasses.fileContainer(filename, startOfRun))

                # And add the files to the subsystem
                # Since a run was just appended, accessing the last element should always be fine
                run.subsystems[subsystem].files = files

                # Add combined
                combinedFilename = [filename for filename in os.listdir(subsystemPath) if "combined" in filename and ".root"in filename]
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

    print("Files moved: {0}".format(runDict))

    # Now process the results from moving the files and add them into the runs list
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
                    print("Previous EOR: {0}\tNew: {1}".format(subsystem.endOfRun, fileKeys[-1]))
                    subsystem.endOfRun = fileKeys[-1]
                else:
                    # Create a new subsystem
                    createNewSubsystemFromMergeInformation(runs, subsystemName, runDict, runDir)

        else:
            runs[runDir] = processingClasses.runContainer( runDir = runDir,
                                                           fileMode = processingParameters.cumulativeMode)
            # Add files and subsystems.
            # We are creating runs here, so we already have all the information that we need from moving the files
            for subsystem in processingParameters.subsystemList:
                createNewSubsystemFromMergeInformation(runs, subsystem, runDict, runDir)
                
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

    # Construct subsystems
    # Up to this point, the files have just been setup and merged.
    # Analysis below requires additional information, so it will be collected in subsystemProperties classes
    #subsystems = []
    #for subsystem in subsystemList:
    #    showRootFiles = False
    #    if subsystem in subsystemsWithRootFilesToShow:
    #        showRootFiles = True

    #    subsystems.append(subsystemProperties(subsystem = subsystem,
    #                                          runDirs = subsystemRunDirDict,
    #                                          mergeDirs = mergedRuns,
    #                                          showRootFiles = showRootFiles))

    # Contains which directories to write out on the main page
    #writeDirs = []

    # Determine which runs to process
    for runDir, run in runs.items():
        #for subsystem in subsystems:
        for subsystem in run.subsystems:
            # Determine img dir and input file
            #imgDir = os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem, "img")
            #combinedFile = next(name for name in os.listdir(os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem)) if "combined" in name)
            inputFilename = os.path.join(dirPrefix, runDir, run.subsystems[subsystem].fileLocationSubsystem, run.subsystems[subsystem].combinedFile.filename)

            #if os.path.exists(inputFilename):
            #    # Does not always append, since a run number could come up multiple times when processing
            #    # different subsystems. This is not necessarily a problem since it is not new information,
            #    # but it could become confusing.
            #    if runDir not in subsystem.writeDirs:
            #        subsystem.writeDirs.append(runDir)
            #else:
            #    print("File %s does not seem to exist! Skipping!" % inputFilename)
            #    continue

            # Process if imgDir doesn't exist, or if forceReprocessing, or if runDir has been merged recently
            #if not os.path.exists(imgDir) or forceReprocessing == True or runDir in subsystem.mergeDirs:
            if run.subsystems[subsystem].newFile == True or processingParameters.forceReprocessing == True:
                #if not os.path.exists(imgDir): # check in case forceReprocessing
                #    os.makedirs(imgDir)
                ## json files
                #jsonPath = imgDir.replace("img", "json")
                #print("jsonPath: {0}".format(jsonPath))
                #if not os.path.exists(jsonPath):
                #    os.makedirs(jsonPath)

                # Process combined root file: plot histos and save in imgDir
                print("About to process %s, %s" % (runDir, subsystem))
                outputFormattingSave = os.path.join(run.subsystems[subsystem].imgDir, "%s" + processingParameters.fileExtension) 
                outputHistNames = processRootFile(inputFilename, outputFormattingSave, subsystem)

                # Store filenames and timestamps in dictionary, for sorting by time
                #[mergeDict, maxTimeMinutes] = utilities.createFileDictionary(dirPrefix, runDir, subsystem.fileLocationSubsystem)
                outputFormattingWeb =  os.path.join("img","%s") + processingParameters.fileExtension
                # timeKeys[0] is the start time of the run in unix time
                #timeKeys = sorted(mergeDict.keys())

                # Write subsystem html page
                # Write static page
                #generateWebPages.writeToWebPage(os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem), runDir, subsystem.subsystem, outputHistNames, outputFormattingWeb, timeKeys[0], maxTimeMinutes)
                #if templateDataDirName != None:
                # Write template page
                templateFolderForRunPage = os.path.join(templateDataDirPrefix, runDir, subsystem.fileLocationSubsystem)
                if not os.path.exists(templateFolderForRunPage):
                    os.makedirs(templateFolderForRunPage)
                generateWebPages.writeToWebPage(templateFolderForRunPage, runDir, subsystem, outputHistNames, outputFormattingWeb, run.subsystems[subsystem].startOfRun, run.subsystems[subsystem].runLength, generateTemplate = True)
            else:
                # We often want to skip this point since most runs will not need to be processed most times
                if beVerbose:
                    print("Don't need to process %s. It has already been processed" % runDir)

    exit(0)

    # Now write the webpage in the root directory
    # Static page
    generateWebPages.writeRootWebPage(dirPrefix, subsystems)
    if templateDataDirName != None:
        # Templated page
        generateWebPages.writeRootWebPage(templateDataDirPrefix, subsystems, generateTemplate = True)

    print("Finished processing! Webpage available at: %s/runList.html" % os.path.abspath(dirPrefix))

    # Send data to pdsf via rsync
    if sendData == True:
        utilities.rsyncData(dirPrefix, remoteUsername, processingParameters.remoteSystems, processingParameters.remoteFileLocations)
        if templateDataDirName != None:
            utilities.rsyncData(templateDataDirName, remoteUsername, processingParameters.remoteSystems, processingParameters.remoteFileLocations)
        
# Allows the function to be invoked automatically when run with python while not invoked when loaded as a module
if __name__ == "__main__":
    # Process all of the run data
    processAllRuns()
    # Function calls that be used for debugging
    #processQA("Run246272", "Run246980", "EMC", "determineMedianSlope")
    #processPartialRun(123457, 0, 5, "EMC")
