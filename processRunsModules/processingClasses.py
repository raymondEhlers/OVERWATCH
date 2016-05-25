#!/usr/bin/python

"""
Classes that define the structure of processing. This information can be created and processed,
or read from file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

from __future__ import print_function

import os
import sortedcontainers

from processRunsModules import qa
from processRunsModules import utilities
from config.processingParams import processingParameters

###################################################
class runContainer(object):
    """ Contains an individual run

    """
    def __init__(self, runDir, fileMode):
        self.runDir = runDir
        self.runNumber = int(runDir.replace("Run", ""))
        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer
        self.mode = fileMode
        self.subsystems = {}

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
        self.histGroups = {}

        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer

        # True if we received a new file, therefore leading to reprocessing
        # If the subsystem is being created, we likely need reprocessing, so defaults to true
        self.newFile = True


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
class histGroupContainer(object):
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
class histContainer(object):
    """ Histogram information container
    
    """
    def __init__(self, histName, prettyName = None):
        self.histName = histName
        # Only assign if meaningful
        if prettyName != None:
            self.prettyName = prettyName
        else:
            self.prettyName = hist.histName

        self.information = dict()
        self.hist = None
        self.processedHist = None

