#!/usr/bin/python

"""
Classes that define the structure of processing. This information can be created and processed,
or read from file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

"""

from __future__ import print_function
from __future__ import absolute_import

# Database
import BTrees.OOBTree
import persistent

import os
import time
import ruamel.yaml as yaml
import logging
# Setup logger
logger = logging.getLogger(__name__)

from ..base import utilities
from ..base import config
#from config.processingParams import processingParameters
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

###################################################
class runContainer(persistent.Persistent):
    """ Contains an individual run

    """
    def __init__(self, runDir, fileMode, hltMode = None):
        self.runDir = runDir
        self.runNumber = int(runDir.replace("Run", ""))
        self.prettyName = "Run {0}".format(self.runNumber)
        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer
        self.mode = fileMode
        self.subsystems = BTrees.OOBTree.BTree()
        self.hltMode = hltMode

        # Try to retrieve the HLT mode if it was not passed
        runInfoFilePath = os.path.join(processingParameters["dirPrefix"], self.runDir, "runInfo.yaml")
        if not hltMode:
            try:
                with open(runInfoFilePath, "rb") as f:
                    runInfo = yaml.load(f.read())

                self.hltMode = runInfo["hltMode"]
            except IOError as e:
                # File does not exist
                # HLT mode will have to be unknown
                self.hltMode = "U"

        # Run Information
        # Since this is only information to save, only write it if the file doesn't exist
        if not os.path.exists(runInfoFilePath):
            runInfo = {}
            # "U" for unknown
            runInfo["hltMode"] = hltMode if hltMode else "U"

            # Write information
            if not os.path.exists(os.path.dirname(runInfoFilePath)):
                os.makedirs(os.path.dirname(runInfoFilePath))
            with open(runInfoFilePath, "wb") as f:
                yaml.dump(runInfo, f)

    def isRunOngoing(self):
        """ Checks if one of the subsystems has a new file, indicating that the run is ongoing. """
        returnValue = False
        try:
            # We just take the last subsystem in a given run. Any will do
            lastSubsystem = self.subsystems[self.subsystems.keys()[-1]]
            returnValue = lastSubsystem.newFile
        except KeyError:
            returnValue = False

        return returnValue

    def timeStamp(self):
        """ Returns a pretty time stamp from the last subsystem. """
        returnValue = False
        try:
            # We just take the last subsystem in a given run. Any will do
            lastSubsystem = self.subsystems[self.subsystems.keys()[-1]]
            returnValue = lastSubsystem.prettyPrintUnixTime(lastSubsystem.startOfRun)
        except KeyError:
            returnValue = False

        return returnValue

###################################################
class subsystemContainer(persistent.Persistent):
    """ Subsystem container class.

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

    def __init__(self, subsystem, runDir, startOfRun, endOfRun, showRootFiles = False, fileLocationSubsystem = None):
        """ Initializes subsystem properties.

        It does safety and sanity checks on a number of variables.
        """
        # Subsystem name
        self.subsystem = subsystem
        # Bool to control whether to show root files for this subsystem for this run
        self.showRootFiles = showRootFiles

        # If data does not exist for this subsystem then it is dependent on HLT data
        # Detect it if not passed to the constructor
        if fileLocationSubsystem is None:
            # Use the subsystem directory as proxy for whether it exists
            # TODO: Improve this detection. It should work, but may not be so flexible
            if os.path.exists(os.path.join(processingParameters["dirPrefix"], runDir, subsystem)):
                self.fileLocationSubsystem = self.subsystem
            else:
                self.fileLocationSubsystem = "HLT"
        else:
            self.fileLocationSubsystem = fileLocationSubsystem

        if self.showRootFiles == True and self.subsystem != self.fileLocationSubsystem:
            logger.warning("\tIt is requested to show ROOT files for subsystem %s, but the subsystem does not have specific data files. Using HLT data files!" % subsystem)

        # Files
        # Be certain to set these after the subsystem has been created!
        # Contains all files for that particular run
        self.files = BTrees.OOBTree.BTree()
        self.timeSlices = persistent.mapping.PersistentMapping()
        # Only one combined file, so we do not need a dict!
        self.combinedFile = None

        # Directories
        # Depends on whether the subsystem actually contains the files!
        self.baseDir = os.path.join(runDir, self.fileLocationSubsystem)
        self.imgDir = os.path.join(self.baseDir, "img")
        self.jsonDir = os.path.join(self.baseDir, "json")
        # Ensure that they exist
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.imgDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.imgDir))
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.jsonDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.jsonDir))

        # Times
        self.startOfRun = startOfRun
        self.endOfRun = endOfRun
        # runLength is in minutes
        self.runLength = (endOfRun - startOfRun)/60

        # Histograms
        self.histGroups = persistent.list.PersistentList()
        # Should be accessed through the group usually, but this provides direct access
        self.histsInFile = BTrees.OOBTree.BTree()
        # All hists, including those which were created, along with those in the file
        self.histsAvailable = BTrees.OOBTree.BTree()
        # Hists list that should be used
        self.hists = BTrees.OOBTree.BTree()

        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer

        # True if we received a new file, therefore leading to reprocessing
        # If the subsystem is being created, we likely need reprocessing, so defaults to true
        self.newFile = True

        # nEvents
        self.nEvents = 1

        # Processing options
        # Implemented by the detector to note how it was processed that may be changed during time slice processing
        # This allows us return full processing when appropriate
        self.processingOptions = persistent.mapping.PersistentMapping()

    @staticmethod
    def prettyPrintUnixTime(unixTime):
        """ Pretty print the unix time. Needed mostly in templates were arbitrary functions are not allowed.

        """
        timeStruct = time.gmtime(unixTime)
        timeString = time.strftime("%A, %d %b %Y %H:%M:%S", timeStruct)

        return timeString

    def resetContainer(self):
        """  Clear the stored hist information so we can recreate (reprocess) the subsystem. """
        del self.histGroups[:]
        self.histsInFile.clear()
        self.histsAvailable.clear()
        self.hists.clear()

class trendingContainer(persistent.Persistent):
    """ Structure of the trending container (quite similar to that of the subsystem container):

        """
    def __init__(self, trendingDB):
        self.subsystem = "TDG"

        # Main container of the trendingObjects
        self.trendingObjects = trendingDB

        # True if the trending container trending objects are entirely filled and up to date
        # Could be used to refill the trending container if it is empty
        # TODO: Implement fully
        self.updateToDate = False

        # Directories for storage
        self.baseDir = self.subsystem
        self.imgDir = os.path.join(self.baseDir, "img")
        self.jsonDir = os.path.join(self.baseDir, "json")
        # Ensure that they exist
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.imgDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.imgDir))
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.jsonDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.jsonDir))

        # Processing options
        # Implemented by the detector to note how it was processed that may be changed during time slice processing
        # This allows us return full processing when appropriate
        self.processingOptions = persistent.mapping.PersistentMapping()

    def addSubsystemTrendingObjects(self, subsystem, trendingObjects, forceRecreateSubsystem):
        """ Add a given subsystem and set of associated trending objects to the trending container.

        Args:
            subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
            trendingObjects (list): List of TrendingObject derived objects.
        """
        if not subsystem in self.trendingObjects.keys():
            self.trendingObjects[subsystem] = BTrees.OOBTree.BTree()

        logger.debug("self.trendingObjects[{}]: {}".format(subsystem, self.trendingObjects[subsystem]))

        for name, obj in trendingObjects.iteritems():
            if not name in self.trendingObjects[subsystem] or forceRecreateSubsystem:
                logger.debug("Adding trending object {} from subsystem {} to the trending objects".format(name, subsystem))
                self.trendingObjects[subsystem][name] = obj
            else:
                logger.debug("Trending object {} (name: {}) already exists in subsystem {}".format(self.trendingObjects[subsystem][name], name, subsystem))

    def resetContainer(self):
        """ Reset the trending container """
        self.trendingObjects.clear()

    def findTrendingFunctionsForHist(self, hist):
        """ Given a hist, determine the trending objects (and therefore functions) which should be applied. """
        logger.debug("Looking for trending objects for hist {}".format(hist.histName))
        for subsystemName, subsystem in self.trendingObjects.iteritems():
            for trendingObjName, trendingObj in subsystem.iteritems():
                if hist.histName in trendingObj.histNames:
                    # Define the temporary function so it can be executed later.
                    #def tempFunc():
                    #    return self.trendingObjects[subsystemName][trendingObjName].Fill(hist)
                    #hist.append(tempFunc)
                    logger.debug("Found trending object match for hist {}, trendingObject: {}".format(hist.histName, self.trendingObjects[subsystemName][trendingObjName].name))
                    hist.trendingObjects.append(self.trendingObjects[subsystemName][trendingObjName])

###################################################
class timeSliceContainer(persistent.Persistent):
    """ Time slice information container

    """
    def __init__(self, minUnixTimeRequested, maxUnixTimeRequested, minUnixTimeAvailable, maxUnixTimeAvailable, startOfRun, filesToMerge, optionsHash):
        # Requested times
        self.minUnixTimeRequested = minUnixTimeRequested
        self.maxUnixTimeRequested = maxUnixTimeRequested
        # Available times
        self.minUnixTimeAvailable = minUnixTimeAvailable
        self.maxUnixTimeAvailable = maxUnixTimeAvailable
        # Start of run is also in unix time
        self.startOfRun = startOfRun
        self.optionsHash = optionsHash

        # File containers of the files to merge
        self.filesToMerge = filesToMerge

        # Filename prefix for saving out files
        self.filenamePrefix = "timeSlice.{0}.{1}.{2}".format(self.minUnixTimeAvailable, self.maxUnixTimeAvailable, self.optionsHash)

        # Create filename
        self.filename = fileContainer(self.filenamePrefix + ".root")

        # Processing options
        # Implemented by the detector to note how it was processed that may be changed during time slice processing
        # This allows us return full processing when appropriate
        # Same as the type of options implemented in the subsystemContainer!
        self.processingOptions = persistent.mapping.PersistentMapping()

    def timeInMinutes(self, inputTime):
        #logger.debug("inputTime: {0}, startOfRun: {1}".format(inputTime, self.startOfRun))
        return (inputTime - self.startOfRun)//60

    def timeInMinutesRounded(self, inputTime):
        return round(self.timeInMinutes(inputTime))

###################################################
class fileContainer(persistent.Persistent):
    """ File information container
    
    """
    def __init__(self, filename, startOfRun = None):
        self.filename = filename

        # Determine types of file
        self.combinedFile = False
        self.timeSlice = False
        if "combined" in self.filename:
            self.combinedFile = True
        elif "timeSlice" in self.filename:
            self.timeSlice = True

        # The combined file time will be the length of the run
        # The time slice will be the length of the time slice
        self.fileTime = utilities.extractTimeStampFromFilename(self.filename)
        if startOfRun:
            self.timeIntoRun = self.fileTime - startOfRun
        else:
            # Show a clearly invalid time, since timeIntoRun doesn't make much sense for a time slice
            self.timeIntoRun = -1

###################################################
class histogramGroupContainer(persistent.Persistent):
    """ Class to handle sorting of objects.

    This class can select a group of histograms and store their names in a list. It also stores a more
    readable version of the group name, as well as whether the histograms should be plotted in a grid.

    Args:
        groupName (str): Readable name of the group.
        groupSelectionPattern (str): Pattern of the histogram names that will be selected. For example, if
            wanted to select histograms related to EMCal patch amplitude, we would make the pattern something
            like "PatchAmp". The name depends on the name of the histogram sent from the HLT.
        plotInGridSelectionPattern (str): Pattern which denotes whether the histograms should be plotted in
            a grid. ``plotInGrid`` is set based on whether this value is in ``groupSelectionPattern``. For
            example, in the EMCal, the ``plotInGridSelectionPattern`` is "_SM". 

    Available attributes include:

    Attributes:
        name (str): Readable name of the group. Set via the ``groupName`` in the constructor.
        selectionPattern (str): Pattern of the histogram names that will be selected.
        plotInGridSelectionPattern (str): Pattern which denotes whether the histograms should be plotted in
            a grid.
        plotInGrid (bool): True when the histograms should be plotted in a grid.
        histList (list): List of the histograms that should be filled when the ``selectionPattern`` is matched.
    
    """

    def __init__(self, prettyName, groupSelectionPattern, plotInGridSelectionPattern = "DO NOT PLOT IN GRID"):
        """ Initializes the hist group """
        self.prettyName = prettyName
        self.selectionPattern = groupSelectionPattern
        self.plotInGridSelectionPattern = plotInGridSelectionPattern
        self.histList = persistent.list.PersistentList()

        # So that it is not necessary to check the list every time
        if self.plotInGridSelectionPattern in self.selectionPattern:
            self.plotInGrid = True
        else:
            self.plotInGrid = False


###################################################
class histogramContainer(persistent.Persistent):
    """ Histogram information container
    
    """
    def __init__(self, histName, histList = None, prettyName = None):
        # Replace any slashes with underscores to ensure that it can be used safely as a filename
        #histName = histName.replace("/", "_")
        self.histName = histName
        # Only assign if meaningful
        if prettyName != None:
            self.prettyName = prettyName
        else:
            self.prettyName = self.histName

        self.histList = histList
        self.information = persistent.mapping.PersistentMapping()
        self.hist = None
        self.histType = None
        self.drawOptions = ""
        # Contains the canvas where the hist may be plotted, along with additional content
        self.canvas = None
        # Functions which will be applied to the histogram each time it is processed
        self.functionsToApply = persistent.list.PersistentList()
        # Trending objects which use this histogram
        self.trendingObjects = persistent.list.PersistentList()

    def retrieveHistogram(self, ROOT, fIn = None, trending = None):
        if fIn:
            if self.histList is not None:
                self.hist = ROOT.THStack(self.histName, self.histName)
                for name in self.histList:
                    logger.debug("HistName in list: {0}".format(name))
                    self.hist.Add(fIn.GetKey(name).ReadObj())
                self.drawOptions += "nostack"
                # TODO: Allow for further configuration of THStack, like TLegend and such
            else:
                logger.debug("HistName: {0}".format(self.histName))
                self.hist = fIn.GetKey(self.histName).ReadObj()
        elif trending:
            # Not particularly efficient
            for subsystemName, subsystem in trending.trendingObjects.iteritems():
                for name, trendingObject in subsystem.iteritems():
                    if self.histName in trendingObject.hist.histName:
                        self.hist = trending.trendingObjects[subsystemName][self.histName].trendingHist
        else:
            logger.warning("Unable to retrieve histogram {}".format(self.histName))

###################################################
class qaFunctionContainer(persistent.Persistent):
    """ QA Container class

    Args:
        firstRun (str): The first (ie: lowest) run in the form "Run#". Ex: "Run123"
        lastRun (str): The last (ie: highest) run in the form "Run#". Ex: "Run123"
        runDirs (list): List of runs in the range [firstRun, lastRun], with entries in the form of "Run#" (str).
        qaFunctionName (str): Name of the QA function to be executed.

    Available attributes include:

    Attributes:
        currentRun (str): The current run being processed in the form "Run#". Ex: "Run123"
        hists (dict): Contains histograms with keys equal to the histogram label (often the hist name).
            Initalized to an empty dict.
        filledValueInRun (bool): Can be set when a value is filled in a run. It is the user's responsibility to
            set the value to ``True`` when desired. The flag will be reset to ``False`` at the start of each run.
            Initialized to ``False``.
        runLength (int): Length of the current run in minutes.

    Note:
        Arguments listed above are also available to be called as members. However, it is greatly preferred to access
        hists through the methods listed below.

    Note:
        You can draw on the histogram that you are processing by passing ``"same"`` as a parameter to the ``Draw()``.

    """

    def __init__(self, firstRun, lastRun, runDirs, qaFunctionName):
        """ Initializes the container with all of the requested information. """
        self.firstRun = firstRun
        self.lastRun = lastRun
        self.runDirs = runDirs
        self.qaFunctionName = qaFunctionName
        self.hists = dict()
        self.currentRun = firstRun
        self.filledValueInRun = False
        self.currentRunLength = 0

    def addHist(self, hist, label):
        """ Add a histogram at a given label.

        Note:
            This function calls ``SetDirectory(0)`` on the passed histogram to make sure that it is not
            removed when it goes out of scope.

        Args:
            hist (TH1): The histogram to be added.
            label (str): 

        Returns:
            None
        """
        # Ensures that the created histogram does not get destroyed after going out of scope.
        hist.SetDirectory(0)
        if label in self.hists:
            logger.warning("Replacing histogram {0} in QA Container!".format(label))
        self.hists[label] = hist

    def addHists(self, hists):
        """ Add histograms from a dict containing histograms with keys set as the labels.

        Args: 
            hists (dict): Dictionary with the hist labels as keys and the histograms as values.

        Returns:
            None
        """

        for hist, label in hists:
            self.addHist(hist, label)

    def getHist(self, histName):
        """ Gets a histogram labeled by name.

        Args:
            histName (str): Label of the desired histogram. Often the hist name.

        Returns:
            TH1: The requested histogram or None if it doesn't exist.

        """
        return self.hists.get(histName, None)

    def getHists(self):
        """ Gets all histograms and returns them in a list.

        Args:
            None

        Returns:
            list: List of TH1s, generated by getting ``values()`` of the ``hists`` dict.

        """
        return self.hists.values()

    def getHistLabels(self):
        """ Gets all histogram labels and returns them in a list.

        Args:
            None

        Returns:
            list: List of strings, generated by getting ``keys()`` of the ``hists`` dict.

        """
        return self.hists.keys()

    def getHistsDict(self):
        """ Gets the dict stored by the class.

        Args:
            None

        Returns:
            dict: Contains histograms with keys equal to the histogram label (often the hist name).
        """
        return self.hists

    def removeHist(self, histName):
        """ Remove histogram from container.

        Args:
            histName (str): Label of the desired histogram. Often the hist name.

        Returns:
            None
        """
        if histName in self.hists:
            del self.hists[histName]
        else:
            logger.warning("histName {0} not in qa container, so it could not be removed!".format(histName))

###################################################
class trendingObject(object):
    """ Base trending object """
    def __init__(self, trendingName, trendingHist, histNames = None):
        self.name = trendingName
        self.trendingHist = trendingHist
        self.trendingFunction = None

        self.hist = histogramContainer(trendingName)
        self.hist.hist = self.trendingHist

        # Set histograms to be included
        # TODO: Should these be hist containers??
        if not histNames:
            histNames = []
        # Ensure that a copy is name by wrapping in list
        self.histNames = list(histNames)

        # Where the next entry should go
        self.nextEntry = 1

        # Visualization of the trending object
        self.canvas = None

    # Handles requests to .hist in the processHist() function
    #@property
    #def hist(self):
    #    return self.trendingHist

    #@hist.setter
    #def hist(self, val):
    #    if val == None:
    #        pass
    #    else:
    #        self.trendingHist = val

    def Fill(self, value, error):
        """ 1D filling function. """
        # TODO: Determine best way to get the previous histogram!
        print("name: {}, self.nextEntry: {}, value: {}".format(self.name, self.nextEntry, value))
        if self.nextEntry > self.nEntries:
            # Get the array and convert to np array so it can be fed back to the hist
            valArray = utilities.convertToNPArray(self.trendingHist.GetArray(), self.trendingHist.GetNcells())
            errorArray = utilities.convertToNPArray(self.trendingHist.GetArrayErrors(), self.trendingHist.GetNcells())

            # Insert back into histogram
            self.trendingHist.SetContent(utilities.removeOldestValueAndInsert(valArray))
            self.trendingHist.SetErrorContent(utilities.removeOldestValueAndInsert(errorArray))

            # Increment the time offset
            # TODO: Determine how to get this value
            #self.trendingHist.GetXaxis().SetTimeOffset()
        else:
            if self.nextEntry == 1:
                # TODO: Determine how to get this value
                #self.trendingHist.GetXaxis().SetTimeOffset()
                pass

            # Fill into the trending histogram
            self.trendingHist.SetBinContent(self.nextEntry, value)
            self.trendingHist.SetBinError(self.nextEntry, error)

        # Keep track to move to the next entry
        self.nextEntry += 1

