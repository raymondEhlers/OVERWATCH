#!/usr/bin/python

"""
Classes that define the structure of processing. This information can be created and processed,
or read from file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University

"""

from __future__ import print_function

import os
import sortedcontainers
import collections

from processRunsModules import utilities
from config.processingParams import processingParameters

###################################################
class runContainer(object):
    """ Contains an individual run

    """
    def __init__(self, runDir, fileMode):
        self.runDir = runDir
        self.runNumber = int(runDir.replace("Run", ""))
        self.prettyName = "Run {0}".format(self.runNumber)
        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer
        self.mode = fileMode
        self.subsystems = collections.OrderedDict()

###################################################
class subsystemContainer(object):
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

    def __init__(self, subsystem, runDir, startOfRun, runLength, showRootFiles = False, fileLocationSubsystem = None):
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
            if os.path.exists(os.path.join(processingParameters.dirPrefix, runDir, subsystem)):
                self.fileLocationSubsystem = self.subsystem
            else:
                self.fileLocationSubsystem = "HLT"
        else:
            self.fileLocationSubsystem = fileLocationSubsystem

        if self.showRootFiles == True and self.subsystem != self.fileLocationSubsystem:
                print("\tWARNING! It is requested to show ROOT files for subsystem %s, but the subsystem does not have specific data files. Using HLT data files!" % subsystem)

        # Files
        # Be certain to set these after the subsystem has been created!
        # Contains all files for that particular run
        self.files = sortedcontainers.SortedDict()
        # Only one combined file, so we do not need a dict!
        self.combinedFile = None

        # Directories
        # Depends on whether the subsystem actually contains the files!
        self.imgDir = os.path.join(processingParameters.dirPrefix, runDir, self.fileLocationSubsystem, "img")
        print("imgDir: {0}".format(self.imgDir))
        self.jsonDir = self.imgDir.replace("img", "json")
        # Ensure that they exist
        if not os.path.exists(self.imgDir):
            os.makedirs(self.imgDir)
        if not os.path.exists(self.jsonDir):
            os.makedirs(self.jsonDir)

        # Times
        self.startOfRun = startOfRun
        self.runLength = runLength
        self.endOfRun = self.startOfRun + runLength*60 # runLength is in minutes

        # Histograms
        #self.histGroups = sortedcontainers.SortedDict()
        self.histGroups = collections.OrderedDict()
        # Should be accessed through the group usually, but this provides direct access
        self.histsInFile = sortedcontainers.SortedDict()
        self.histsAvailable = sortedcontainers.SortedDict()
        # Hists list that should be used
        self.hists = sortedcontainers.SortedDict()

        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer

        # True if we received a new file, therefore leading to reprocessing
        # If the subsystem is being created, we likely need reprocessing, so defaults to true
        self.newFile = True

        # nEvents
        self.nEvents = 1


###################################################
class fileContainer(object):
    """ File information container
    
    """
    def __init__(self, filename, startOfRun):
        self.filename = filename
        if "combined" in self.filename:
            self.combinedFile = True
        else:
            self.combinedFile = False

        # The combined file time will be the length of the run
        self.fileTime = utilities.extractTimeStampFromFilename(self.filename)
        self.timeIntoRun = self.fileTime - startOfRun

###################################################
class histogramGroupContainer(object):
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
        self.histList = []

        # So that it is not necessary to check the list every time
        if self.plotInGridSelectionPattern in self.selectionPattern:
            self.plotInGrid = True
        else:
            self.plotInGrid = False


###################################################
class histogramContainer(object):
    """ Histogram information container
    
    """
    def __init__(self, histName, histList = None, prettyName = None):
        self.histName = histName
        # Only assign if meaningful
        if prettyName != None:
            self.prettyName = prettyName
        else:
            self.prettyName = self.histName

        self.histList = histList
        self.information = dict()
        self.hist = None
        self.drawOptions = ""
        # Contains the canvas where the hist may be plotted, along with additional content
        self.canvas = None
        self.functionsToApply = []

    def retrieveHistogram(self, fIn):
        if self.histList is not None:
            self.hist = THStack(self.histName, self.histName)
            for name in self.histList:
                print("HistName in list: {0}".format(name))
                self.hist.Add(fIn.GetKey(name).ReadObj())
            self.drawOptions += "nostack"
            # TODO: Allow for further configuration of THStack, like TLegend and such
        else:
            print("HistName: {0}".format(self.histName))
            self.hist = fIn.GetKey(self.histName).ReadObj()

###################################################
class qaFunctionContainer(object):
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
            Print("WARNING: Replacing histogram %s in QA Container!" % label)
        self.hists[label] = hist

    def addHists(self, hists):
        """ Add histograms from a dict containing histograms with keys set as the labels.

        Args: 
            hists (dict): Dictionary with the hist labels as keys and the histograms as values.

        Returns:
            None
        """

        for hist, label in zip(hists, labels):
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
            print("WARNING: histName {0} not in qa container, so it could not be removed!".format(histName))


