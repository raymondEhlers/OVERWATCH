#!/usr/bin/python

"""
Classes that define the structure of processing. This information can be created and processed,
or read from file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

from __future__ import print_function

from processRunsModules import qa

###################################################
class runContainer(object):
    """ Contains an individual run

    """
    def __init__(self, runNumber, fileMode):
        self.runNumber = runNumber
        self.runNumberString = "Run{0}".format(runNumber)
        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer
        self.mode = fileMode
        self.subsystems = []

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

    def __init__(self, subsystem, runDirs, mergeDirs = None, showRootFiles = False):
        """ Initializes subsystem properties.

        It does safety and sanity checks on a number of variables.
        """
        self.subsystem = subsystem
        self.showRootFiles = showRootFiles
        self.writeDirs = []

        # Contains all files for that particular run
        self.files = []
        # Times
        self.startOfRun = startOfRun
        self.endOfRun = endOfRun
        self.runLenght = self.endOfRun - self.startOfRun
        # Histograms
        self.histGroups = []
        # Need to rework the qa container 
        #self.qaContainer = qa.qaFunctionContainer
        # True if we received a new file, therefore leading to reprocessing
        self.newFile = True

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
class fileContainer(object):
    """ File information container
    
    """
    def __init__(self, filename, startOfRun):
        self.fileName = filename
        # Extract from filename?
        self.fileTime = 123456789
        self.timeIntoRun = self.fileTime - startOfRun
        self.combinedFile = False

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


