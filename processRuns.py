#!/usr/bin/python

"""
Takes root files from the HLT viewer and organizes them into run directory and subsystem structure, 
then writes out histograms to webpage.  

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""
from __future__ import print_function

# ROOT includes
from ROOT import gROOT, TFile, TCanvas, TClass, TH1, TLegend, SetOwnership, TFileMerger, TList, gPad, TGaxis, gStyle, TProfile, TF1, TH1F

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
from os import makedirs
from os.path import exists
import time

# Config
from config.processingParams import processingParameters

# Module includes
from processRunsModules import utilities
from processRunsModules import generateWebPages
from processRunsModules import mergeFiles
from processRunsModules import qa

###################################################
class subsystemProperties(object):
    """ Subsystem Property container class.

    Defines properties of each subsystem in a consistent place.

    Args:
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        runDirs (dict): Contains list of valid runDirs for each subsystem, indexed by subsystem.
        mergeDirs (Optional[dict]): Contains list of valid mergeDirs for each subsystem, indexed by subsystem.
            Defaults to ``None``.
        showRootFiles (Optional[bool]): Determines whether to create a page to make the ROOT files available.
            Defaults to ``False``.

    Available attributes include:

    Attributes:
        fileLocationSubsystem (str): Subsystem name of where the files are actually located. If a subsystem has
            specific data files then this is just equal to the `subsystem`. However, if it relies on files inside
            of another subsystem, then this variable is equal to that subsystem name.
        runDirs (list): List of runs with entries in the form of "Run#" (str).
        mergeDirs (list): List of merged runs with entries in the form of "Run#" (str).

    """

    def __init__(self, subsystem, runDirs, mergeDirs = None, showRootFiles = False):
        """ Initializes subsystem properties.

        It does safety and sanity checks on a number of variables.
        """
        self.subsystem = subsystem
        self.showRootFiles = showRootFiles
        self.writeDirs = []

        # If data does not exist for this subsystem then it is dependent on HLT data
        subsystemDataExistsFlag = False
        for runDir in runDirs[subsystem]:
            if exists(os.path.join(processingParameters.dirPrefix, runDir, subsystem)):
                subsystemDataExistsFlag = True

        if subsystemDataExistsFlag == True:
            self.fileLocationSubsystem = subsystem
        else:
            self.fileLocationSubsystem = "HLT"
            if showRootFiles == True:
                print("\tWARNING! It is requested to show ROOT files for subsystem %s, but the subsystem does not have specific data files. Using HLT data files!" % subsystem)

        # Complete variable assignment now that we know where the data is located.
        self.runDirs = runDirs[self.fileLocationSubsystem]
        self.mergeDirs = []
        if mergeDirs != None:
            self.mergeDirs = mergeDirs[self.fileLocationSubsystem]

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
            hist.SetTitle("")
            hist.Draw(drawOptions)
            canvas.Update()
            
            # Various checks and QA that are performed on hists
            skipPrinting = qa.checkHist(hist, qaContainer)

            # Skips printing out the histogram
            if skipPrinting == True:
                continue

            # Filter here for hists in the subsystem if subsystem != fileLocationSubsystem
            # Thus, we can filter the proper subsystems for subsystems that don't have their own data files
            if subsystem.subsystem != subsystem.fileLocationSubsystem and subsystem.subsystem not in hist.GetName():
                continue

            # Add to our list for printing to the webpage later
            # We only want to do this if we are actually printing the histogram
            outputHistNames.append(hist.GetName())

            # Save
            outputFilename = outputFormatting % hist.GetName()
            canvas.SaveAs(outputFilename)

    # Add to output names if hists are created
    if qaContainer is not None:
        print("hists:", qaContainer.getHists())
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
            if exists(os.path.join(dirPrefix, runDir, subsystem)):
                subsystemRunDirDict[subsystem].append(runDir)

    # Create subsystem object
    subsystem = subsystemProperties(subsystem = subsystemName, runDirs = subsystemRunDirDict)

    # Create necessary dirs
    dataDir = os.path.join(dirPrefix, qaFunctionName)
    if not exists(dataDir):
        makedirs(dataDir)

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
        if exists(os.path.join(dirPrefix, runDir, subsystem)):
            subsystemRunDirDict[subsystem].append(runDir)

    # Setup subsystem properties
    subsystem = subsystemProperties(subsystem = subsystemName, runDirs = subsystemRunDirDict)

    # Merge only the partial run.
    (actualTimeBetween, inputFilename) = mergeFiles.merge(dirPrefix, runDir, subsystem.fileLocationSubsystem, cumulativeMode, minTimeRequested, maxTimeRequested)

    # Setup necessary directories
    baseDirName = inputFilename.replace(".root", "")
    if not exists(baseDirName):
        makedirs(baseDirName)

    imgDir = os.path.join(baseDirName, "img")
    if not exists(imgDir):
        makedirs(imgDir)

    # Setup templates
    # Determine template dirPrefix
    if templateDataDirName != None:
        templateDataDirPrefix = baseDirName.replace(os.path.basename(dirPrefix), templateDataDirName)
        # Create directory to store the templates if necessary
        if not exists(templateDataDirPrefix):
            makedirs(templateDataDirPrefix)

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
        if not exists(templateDataDirPrefix):
            makedirs(templateDataDirPrefix)
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
    (fileExtension, beVerbose, forceReprocessing, forceNewMerge, sendData, remoteUsername, cumulativeMode, templateDataDirName, dirPrefix, subsystemList, subsystemsWithRootFilesToShow) = processingParameters.defineRunProperties()

    # Setup before processing data
    # Determine templateDataDirPrefix
    if templateDataDirName != None:
        templateDataDirPrefix = os.path.join(os.path.dirname(dirPrefix), templateDataDirName)
        print("templateDataDirPrefix:", templateDataDirPrefix)
        # Create directory to store the templates if necessary
        if not exists(templateDataDirPrefix):
            makedirs(templateDataDirPrefix)

    # Start of processing data
    # Takes histos from dirPrefix and moves them into Run dir structure, with a subdir for each subsystem
    utilities.moveRootFiles(dirPrefix, subsystemList)

    # Find directories to run over
    runDirs = utilities.findCurrentRunDirs(dirPrefix)

    # If subsystem dir exists (which only happens if it has files), add runDir to subsystem run list
    subsystemRunDirDict = {}
    for subsystem in subsystemList:
        subsystemRunDirDict[subsystem] = []
        for runDir in runDirs:
            if exists(os.path.join(dirPrefix, runDir, subsystem)):
                subsystemRunDirDict[subsystem].append(runDir)

    # Merge histograms over all runs, all subsystems if needed. Results in one combined file per subdir.
    mergedRuns = mergeFiles.mergeRootFiles(runDirs, subsystemRunDirDict, dirPrefix, subsystemList, forceNewMerge, cumulativeMode)

    # Construct subsystems
    # Up to this point, the files have just been setup and merged.
    # Analysis below requires additional information, so it will be collected in subsystemProperties classes
    subsystems = []
    for subsystem in subsystemList:
        showRootFiles = False
        if subsystem in subsystemsWithRootFilesToShow:
            showRootFiles = True

        subsystems.append(subsystemProperties(subsystem = subsystem,
                                              runDirs = subsystemRunDirDict,
                                              mergeDirs = mergedRuns,
                                              showRootFiles = showRootFiles))

    # Contains which directories to write out on the main page
    writeDirs = []

    # Determine which runs to process
    for runDir in runDirs:
        for subsystem in subsystems:
            # Check if the run exists for that subsystem
            # If it does not exist, continue on to the next run
            if runDir not in subsystem.runDirs:
                continue

            # Determine img dir and input file
            imgDir = os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem, "img")
            combinedFile = next(name for name in os.listdir(os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem)) if "combined" in name)
            inputFilename = os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem, combinedFile)

            if exists(inputFilename):
                # Does not always append, since a run number could come up multiple times when processing
                # different subsystems. This is not necessarily a problem since it is not new information,
                # but it could become confusing.
                if runDir not in subsystem.writeDirs:
                    subsystem.writeDirs.append(runDir)
            else:
                print("File %s does not seem to exist! Skipping!" % inputFilename)
                continue

            # Process if imgDir doesn't exist, or if forceReprocessing, or if runDir has been merged recently
            if not exists(imgDir) or forceReprocessing == True or runDir in subsystem.mergeDirs:
                if not exists(imgDir): # check in case forceReprocessing
                    makedirs(imgDir)

                # Process combined root file: plot histos and save in imgDir
                print("About to process %s, %s" % (runDir, subsystem.subsystem))
                outputFormattingSave = os.path.join(imgDir, "%s") + fileExtension
                outputHistNames = processRootFile(inputFilename, outputFormattingSave, subsystem)

                # Store filenames and timestamps in dictionary, for sorting by time
                [mergeDict, maxTimeMinutes] = utilities.createFileDictionary(dirPrefix, runDir, subsystem.fileLocationSubsystem)
                outputFormattingWeb =  os.path.join("img","%s") + fileExtension
                # timeKeys[0] is the start time of the run in unix time
                timeKeys = sorted(mergeDict.keys())

                # Write subsystem html page
                # Write static page
                generateWebPages.writeToWebPage(os.path.join(dirPrefix, runDir, subsystem.fileLocationSubsystem), runDir, subsystem.subsystem, outputHistNames, outputFormattingWeb, timeKeys[0], maxTimeMinutes)
                if templateDataDirName != None:
                    # Write template page
                    templateFolderForRunPage = os.path.join(templateDataDirPrefix, runDir, subsystem.fileLocationSubsystem)
                    if not exists(templateFolderForRunPage):
                        makedirs(templateFolderForRunPage)
                    generateWebPages.writeToWebPage(templateFolderForRunPage, runDir, subsystem.subsystem, outputHistNames, outputFormattingWeb, timeKeys[0], maxTimeMinutes, generateTemplate = True)
            else:
                # We often want to skip this point since most runs will not need to be processed most times
                if beVerbose:
                    print("Don't need to process %s. It has already been processed" % runDir)

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
