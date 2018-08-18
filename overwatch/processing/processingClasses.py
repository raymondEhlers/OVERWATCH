#!/usr/bin/env python

""" Classes that define the processing structure of Overwatch.

Classes that define the structure of processing. This information can be created and processed,
or read from file.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

from __future__ import print_function
from __future__ import absolute_import
from future.utils import iteritems

# Database
import BTrees.OOBTree
import persistent

import os
import time
import ruamel.yaml as yaml
import numpy as np
import ROOT
import ctypes
import logging
# Setup logger
logger = logging.getLogger(__name__)

from ..base import utilities
from ..base import config
#from config.processingParams import processingParameters
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

class runContainer(persistent.Persistent):
    """ Object to represent a particular run.

    It stores run level information, as well the subsystems which then containing the corresponding
    event information (histogram groups, histograms, etc).

    Note that files are *not* considered event level information because the files correspond to individual
    subsystem. Furthermore, in rare cases, there may be numbers of files for different subsystems
    that are included in an individual run. Consequently, it is cleaner for each subsystem to track it's
    own files.

    To allow the object to be reconstructed from scratch, the HLT mode is stored by writing a YAML file
    in the corresponding run directory. This file is referred to as the "run info" file. Additional
    properties could also be written to this file to avoid the loss of transient information.

    Note:
        The run info file is read and written on object construction. It will only be checked if the
        HLT mode is not set.

    Args:
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``
        fileMode (bool): If true, the run data was collected in cumulative mode. See the module README
            for further information.
        hltMode (str): String containing the HLT mode used for the run.

    Attributes:
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``
        runNumber (int): Run number extracted from the ``runDir``.
        prettyName (str): Reformatting of the ``runDir`` for improved readability.
        mode (bool): If true, the run data was collected in cumulative mode. See the module README
            for further information. Set via ``fileMode``.
        subsystems (BTree): Dict-like object which will contain all of the subsystem containers in
            an event. The key is the corresponding subsystem three letter name.
        hltMode (str): Mode the HLT operated in for this run. Valid HLT modes are "B", "C", "E", and "U".
            Further information on the various modes is in the module ``README.md``. Default: ``None`` (which
            will be converted to "U", for "unknown").
    """
    def __init__(self, runDir, fileMode, hltMode = None):
        self.runDir = runDir
        self.runNumber = int(runDir.replace("Run", ""))
        self.prettyName = "Run {0}".format(self.runNumber)
        self.mode = fileMode
        self.subsystems = BTrees.OOBTree.BTree()
        self.hltMode = hltMode

        # Try to retrieve the HLT mode if it was not passed
        runInfoFilePath = os.path.join(processingParameters["dirPrefix"], self.runDir, "runInfo.yaml")
        if not hltMode:
            # Use the mode from the file if it exists, or otherwise note it as undefined = "U".
            try:
                with open(runInfoFilePath, "rb") as f:
                    runInfo = yaml.load(f.read())

                self.hltMode = runInfo["hltMode"]
            except IOError as e:
                # File does not exist
                # HLT mode will have to be unknown
                self.hltMode = "U"

        # Run Information
        # Since this is only information to save (ie it doesn't update each time the object is constructed),
        # only write it if the file doesn't exist
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
        """ Checks if a run is ongoing.

        The ongoing run check is performed by looking checking for a new file in
        any of the subsystems. If they have just received a new file, then the run
        is ongoing.

        Args:
            None
        Returns:
            bool: True if the run is ongoing.
        """
        returnValue = False
        try:
            # We just take the last subsystem in a given run. Any will do
            lastSubsystem = self.subsystems[self.subsystems.keys()[-1]]
            returnValue = lastSubsystem.newFile
        except KeyError:
            returnValue = False

        return returnValue

    def startOfRunTimeStamp(self):
        """ Provides the start of the run time stamp in a format suitable for display.

        This timestamp is determined by looking at the timestamp of the last subsystem
        (arbitrarily selected) that is available in the run. No time zone conversion is
        performed, so it simply displays the time zone where the data was stored (CERN
        time in production systems).

        Args:
            None
        Returns:
            str: Start of run time stamp formatted in an appropriate manner for display.
        """
        returnValue = False
        try:
            # We just take the last subsystem in a given run. Any will do
            lastSubsystem = self.subsystems[self.subsystems.keys()[-1]]
            returnValue = lastSubsystem.prettyPrintUnixTime(lastSubsystem.startOfRun)
        except KeyError:
            returnValue = False

        return returnValue

class subsystemContainer(persistent.Persistent):
    """ Object to represent a particular subsystem (detector).

    It stores subsystem level information, including the histograms, groups, and file information.
    It is the main container for much of the information that is relevant for processing.

    Information on the file storage layout implemented through this class is available in the
    module ``README.md``.

    Note:
        This object checks for and creates a number of directories on initialization.

    Args:
        subsystem (str): The current subsystem in the form of a three letter, all capital name (ex. ``EMC``).
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``
        startOfRun (int): Start of the run in unix time.
        endOfRun (int): End of the run in unix time.
        showRootFiles (bool): True if the ROOT files should be made accessible through the run list.
            Default: ``False``.
        fileLocationSubsystem (str): Subsystem name of where the files are actually located. If a subsystem
            has specific data files then this is just equal to the `subsystem`. However, if it relies on
            files inside of another subsystem (such as those from the HLT subsystem receiver), then this
            variable is equal to that subsystem name. Default: ``None``, which corresponds to the subsystem
            storing it's own data.

    Attributes:
        subsystem (str): The current subsystem in the form of a three letter, all capital name (ex. ``EMC``).
        showRootFiles (bool): True if the ROOT files should be made accessible through the run list.
        fileLocationSubsystem (str): Subsystem name of where the files are actually located. If a subsystem has
            specific data files then this is just equal to the `subsystem`. However, if it relies on files inside
            of another subsystem, then this variable is equal to that subsystem name.
        files (BTree): Dict-like object which describes subsystem ROOT files. Unix time of a given file is the key
            and a file container for that file is the value.
        timeSlices (BTree): Dict-like object which describes subsystem time slices. A UUID is the dict key (so they
            can be uniquely identified), while a time slice container with the corresponding time slice properties
            is the value.
        combinedFile (fileContainer): File container corresponding to the combined file.
        baseDir (str): Path to the base storage directory for the subsystem. Of the form ``Run123456/SYS``.
        imgDir (str): Path to the image storage directory for the subsystem. Of the form ``Run123456/SYS/img``.
        jsonDir (str): Path to the json storage directory for the subsystem. Of the form ``Run123456/SYS/json``.
        startOfRun (int): Start of the run in unix time.
        endOfRun (int): End of the run in unix time.
        runLength (int): Length of the run in minutes.
        histGroups (PersistentList): List-like object of histogram groups, which are used to classify similar histograms.
        histsInFile (BTree): Dict-like object of all histograms that are in a particular file. Keys are the histogram name,
            while the values are ``histogramContainer`` objects which contain the histogram. Hists should be usually be accessed
            through the hist groups, but list this provides direct access when necessary early in processing.
        histsAvailable (BTree): Dict-like object containing all histograms that are available, including those in a particular
            file and those that are created during processing. Newly created hists should be stored in this dict. Keys are
            histogram names, while values are ``histogramContainer`` objects which contain the histogram.
        hists (BTree): Dict-like object which contains all histograms that should be processed by a histogram.
            After initial creation, this should be the definitive source of histograms for processing and display.
            Keys are histogram names, while values are ``histogramContainer`` objects which contain the histogram.
        newFile (bool): True if we received a new file, while will trigger reprocessing. This flag should only be
            changed when beginning processing the next time. To be explicit, if a subsystem just received a new file
            and it was processed, this flag should only be changed to ``False`` after the next processing iteration
            begins. This allows the status of the run (determined through the subsystem) to be displayed in the web app.
            Default: True because if the subsystem is being created, we likely need reprocessing. 
        nEvents (int): Number of events in the subsystem. Processing will look for a histogram that contains ``events``
            in the name and attempt to extract the number of events based on the number of entries. Should not be used
            unless the subsystem explicitly includes a histogram with the number of events. Default: 1. 
        processingOptions (PersistentMapping): Implemented by the subsystem to note options used during
            standard processing. The subsystem processing options can vary when processing a time slice,
            so storing the options allow us to return to the standard options when performing a full processing.
            Keys are the option names as string, while values are their corresponding values.
    """
    def __init__(self, subsystem, runDir, startOfRun, endOfRun, showRootFiles = False, fileLocationSubsystem = None):
        """ Initializes subsystem properties.

        It does safety and sanity checks on a number of variables.
        """
        self.subsystem = subsystem
        self.showRootFiles = showRootFiles

        # If data does not exist for this subsystem then it is dependent on HLT data
        # Detect it if not passed to the constructor
        if fileLocationSubsystem is None:
            # Use the subsystem directory as proxy for whether it exists.
            # NOTE: This detection works, but it isn't so flexible.
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
        # The run length is in minutes
        self.runLength = (endOfRun - startOfRun)//60

        # Histograms
        self.histGroups = persistent.list.PersistentList()
        # Should be accessed through the group usually, but this provides direct access
        self.histsInFile = BTrees.OOBTree.BTree()
        # All hists, including those which were created, along with those in the file
        self.histsAvailable = BTrees.OOBTree.BTree()
        # Hists list that should be used
        self.hists = BTrees.OOBTree.BTree()

        # True if we received a new file, therefore leading to reprocessing
        # If the subsystem is being created, we likely need reprocessing, so defaults to true
        self.newFile = True

        # Number of events in the subsystem. The processing will attempt to determine the number of events,
        # but it is a subsystem dependent quantity. It needs explicit support.
        self.nEvents = 1

        # Processing options
        self.processingOptions = persistent.mapping.PersistentMapping()

    @staticmethod
    def prettyPrintUnixTime(unixTime):
        """ Converts the given time stamp into an appropriate manner ("pretty") for display.

        Needed mostly in Jinja templates were arbitrary functions are not allowed.

        Args:
            unixTime (int): Unix time to be converted.
        Returns:
            str: The time stamp converted into an appropriate manner for display.
        """
        timeStruct = time.gmtime(unixTime)
        timeString = time.strftime("%A, %d %b %Y %H:%M:%S", timeStruct)

        return timeString

    def resetContainer(self):
        """ Clear the stored hist information so we can recreate (reprocess) the subsystem.

        Without resetting the container, reprocessing doesn't fully test the processing functions,
        which are skipped if these list- and dict-like hist objects have entries.

        Args:
            None
        Returns:
            None
        """
        del self.histGroups[:]
        self.histsInFile.clear()
        self.histsAvailable.clear()
        self.hists.clear()

class trendingContainer(persistent.Persistent):
    """ Object to represent the trending system.

    The trending system is given it's own "subsystem" to handle the storage and configuration
    of trending objects. It also can be used to handle cross subsystem trending which doesn't
    naturally fit into a single subsystem.

    The structure of this container is quite similar to that of the subsystem container.
    This allows for the same functions to operate on both standard subsystem containers
    as well as trending containers (with some minimal wrappers).

    Args:
        trendingDB (BTree): Dict-like object stored in the main ZODB database which is used for storing
            trending objects persistently. Keys are the names of subsystems used for trending and values are 
            ``BTree`` objects which are used to store the trending objects for that histogram. See the
            ``trendingObjects`` attribute description for further details.

    Attributes:
        subsystem (str): Name of trending subsystem, "TDG".
        trendingObjects (BTree): Dict-like object stored in the main ZODB database which is used for storing
            trending objects persistently. Keys are the names of subsystems used for trending and values are 
            ``BTree`` objects which are used to store the trending objects for that histogram. Inside of these
            ``BTree`` objects, keys are the name of the individual trending objects and values are the trending
            objects themselves. As an example, ``trendingObjects["TDG"]["testObj"]`` will be a trending object
            stored within the trending "TDG" subsystem which is called "testObj".
        updateToDate (bool): True if the trending container trending objects are entirely filled and up to date.
            It could be used to refill the trending container if it is empty. Default: ``False``.
        baseDir (str): Path to the base storage directory for the trending. Of the form ``trending``.
        imgDir (str): Path to the image storage directory for the trending. Of the form ``trending/SYS/img``.
        jsonDir (str): Path to the json storage directory for the trending. Of the form ``trending/SYS/json``.
        processingOptions (PersistentMapping): Implemented by the trending system to note options used during
            standard processing. The subsystem processing options can vary when processing a time slice,
            so storing the options allow us to return to the standard options when performing a full processing.
            Keys are the option names as string, while values are their corresponding values.
    """
    def __init__(self, trendingDB):
        self.subsystem = "TDG"

        # Main container of the trendingObjects
        self.trendingObjects = trendingDB

        # True if the trending container trending objects are entirely filled and up to date.
        # Could be used to refill the trending container if it is empty
        # TODO: Implement fully
        self.updateToDate = False

        # Directories for storage
        # Should be of the form, for example, "tredning/SYS/json"
        #self.baseDir = self.subsystem
        self.baseDir = "trending"
        # Need to define the names later because there are multiple subsystems inside of the trending container
        self.imgDir = os.path.join(self.baseDir, "%(subsystem)s", "img")
        self.jsonDir = os.path.join(self.baseDir, "%(subsystem)s", "json")
        # Ensure that they exist for each subsystem
        for subsystemName in processingParameters["subsystemList"] + ["TDG"]:
            if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.imgDir % {"subsystem" : subsystemName})):
                os.makedirs(os.path.join(processingParameters["dirPrefix"], self.imgDir % {"subsystem" : subsystemName}))
            if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.jsonDir % {"subsystem" : subsystemName})):
                os.makedirs(os.path.join(processingParameters["dirPrefix"], self.jsonDir % {"subsystem" : subsystemName}))

        # Processing options
        # Implemented by the detector to note how it was processed that may be changed during time slice processing
        # This allows us return full processing when appropriate
        self.processingOptions = persistent.mapping.PersistentMapping()

    def addSubsystemTrendingObjects(self, subsystem, trendingObjects, forceRecreateSubsystem):
        """ Add a given subsystem and set of associated trending objects to the trending container.

        Args:
            subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
            trendingObjects (dict): Dict of TrendingObject derived objects. Keys are names of the
                trending objects, while the values should be already created and setup trending objects.
            forceRecreateSubsystem (bool): True indicates that the subsystem is being recreated.
                Consequently, the trending objects must also be recreated.
        Returns:
            None
        """
        # The storage for a particular subsystem may not always be initialized, so set it up if necessary.
        if not subsystem in self.trendingObjects.keys():
            self.trendingObjects[subsystem] = BTrees.OOBTree.BTree()

        logger.debug("self.trendingObjects[{}]: {}".format(subsystem, self.trendingObjects[subsystem]))

        # Assign the trending objects created by the subsystem to the trending object storage.
        # There shouldn't be an namespace conflicts because each subsystem has it's own entry
        # in the storage dict.
        for name, obj in iteritems(trendingObjects):
            if not name in self.trendingObjects[subsystem] or forceRecreateSubsystem:
                logger.debug("Adding trending object {} from subsystem {} to the trending objects".format(name, subsystem))
                self.trendingObjects[subsystem][name] = obj
            else:
                logger.debug("Trending object {} (name: {}) already exists in subsystem {}".format(self.trendingObjects[subsystem][name], name, subsystem))
                logger.debug("Trending next entry value: {}".format(self.trendingObjects[subsystem][name].nextEntry))

    def resetContainer(self):
        """ Clear the stored trending objects so we can recreate (reprocess) the trending container.

        Without resetting the container, reprocessing doesn't fully test the processing functions,
        which are skipped if these list- and dict-like trending objects have entries.

        Args:
            None
        Returns:
            None
        """
        self.trendingObjects.clear()

    def findTrendingFunctionsForHist(self, hist):
        """ Given a hist, determine the trending objects (and therefore functions) which should be applied.

        Each trending object select the histograms that are needed for trending by name. This function
        loops over those names and checks if the given histogram is included in the list for any trending
        object. We cannot optimize this loop much because multiple trending objects may use a particular
        histogram, and the histograms requested by the trending object may not necessarily exist for a
        given run.

        Args:
            hist (histogramContainer): Histogram to be checked for trending objects.
        Returns:
            None
        """
        logger.debug("Looking for trending objects for hist {}".format(hist.histName))
        for subsystemName, subsystem in iteritems(self.trendingObjects):
            for trendingObjName, trendingObj in iteritems(subsystem):
                if hist.histName in trendingObj.histNames:
                    # Define the temporary function so it can be executed later.
                    #def tempFunc():
                    #    return self.trendingObjects[subsystemName][trendingObjName].Fill(hist)
                    #hist.append(tempFunc)
                    logger.debug("Found trending object match for hist {}, trendingObject: {}".format(hist.histName, self.trendingObjects[subsystemName][trendingObjName].name))
                    hist.trendingObjects.append(self.trendingObjects[subsystemName][trendingObjName])

class timeSliceContainer(persistent.Persistent):
    """ Time slice information container.

    Contains information about a time slice request, including the time ranges and the files involved.
    These values are required to uniquely describe a time slice.

    Args:
        minUnixTimeRequested (int): Minimum requested unix time. This is the first time stamp to be included
            in the time slice.
        maxUnixTimeRequested (int): Maximum requested unix time. This is the last time stamp to be included
            in the time slice.
        minUnixTimeAvailable (int): Minimum unix time of the run.
        maxUnixTimeAvailable (int): Maximum unix time of the run.
        startOfRun (int): Unix time of the start of the run.
        filesToMerge (list): List of fileContainer objects which need to be merged to create the time slice.
        optionsHash (str): SHA1 hash of the processing options used to construct the time slice.

    Attributes:
        minUnixTimeRequested (int): Minimum requested unix time. This is the first time stamp to be included
            in the time slice.
        maxUnixTimeRequested (int): Maximum requested unix time. This is the last time stamp to be included
            in the time slice.
        minUnixTimeAvailable (int): Minimum unix time of the run.
        maxUnixTimeAvailable (int): Maximum unix time of the run.
        startOfRun (int): Unix time of the start of the run.
        filesToMerge (list): List of fileContainer objects which need to be merged to create the time slice.
        optionsHash (str): SHA1 hash of the processing options used to construct the time slice. This hash
            is used for caching by comparing the processing options for a new time slice request with those
            already processed. If the hashes are the same, we can directly return the already processed result.
        filenamePrefix (str): Filename for the timeSlice file, based on the given start and end times.
        filename (fileContainer): File container for the timeSlice file.
        processingOptions (PersistentMapping): Implemented by the time slice container to note options used
            during standard processing. The time slice processing options can vary when compared to standard
            subsystem processing, so storing the options allow us to apply the custom time slice options.
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
        self.filenamePrefix = "timeSlice.{}.{}.{}".format(self.minUnixTimeAvailable, self.maxUnixTimeAvailable, self.optionsHash)

        # Create filename
        self.filename = fileContainer(self.filenamePrefix + ".root")

        # Processing options
        # Implemented by the detector to note how it was processed that may be changed during time slice processing
        # This allows us return full processing when appropriate
        # Same as the type of options implemented in the subsystemContainer!
        self.processingOptions = persistent.mapping.PersistentMapping()

    def timeInMinutes(self, inputTime):
        """ Return the time from the input unix time to the start of the run in minutes.

        Args:
            inputTime (int): Unix time to be compared to the start of run time.
        Returns:
            int: Minutes from the start of run to the given time.
        """
        #logger.debug("inputTime: {0}, startOfRun: {1}".format(inputTime, self.startOfRun))
        return (inputTime - self.startOfRun)//60

    def timeInMinutesRounded(self, inputTime):
        """ Return the time from the input unix time to start of the run in minutes, rounded to
        the nearest minute.

        Note:
            I believe this was created due to some float vs int issues in the Jinja templating
            system. Although the purpose of this function isn't entirely clear, it is kept for
            compatibility purposes.

        Args:
            inputTime (int): Unix time to be compared to the start of run time.
        Returns:
            int: Minutes from the start of run to the given time.
        """
        return round(self.timeInMinutes(inputTime))

class fileContainer(persistent.Persistent):
    """ File information container.

    This object wraps a ROOT filename, providing convenient access to relevant properties, such
    as the type of file (combined, timeSlice, standard), and the time stamp. This information
    is often stored in the filename itself, but extraction procedures vary for each file type.
    Note that it *does not* open the file itself - this is still the responsibility of the user.

    Args:
        filenae (str): Filename of the corresponding file.
        startOfRun (int): Start of the run in unix time. Default: ``None``. The default will lead
            to timeIntoRun being set to ``-1``. The default is most commonly used for time slices,
            where the start of run isn't so meaningful.

    Attributes:
        filenae (str): Filename of the corresponding file.
        combinedFile (bool): True if this file corresponds to a combined file. It is set to ``True``
            if "combined" is in the filename.
        timeSlice (bool): True if this file corresponds to a time slice. It is set to ``True`` if
            "timeSlice" in in the filename.
        fileTime (int): Unix time stamp of the file, extracted from the filename.
        timeIntoRun (int): Time in seconds from the start of the run to the file time. Depends on
            startOfRun being a valid time when the object was created.
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

class histogramGroupContainer(persistent.Persistent):
    """ Organizes similar histograms into groups for processing and display.

    Histograms groups are created by providing name substrings of histogram which should be included.
    The name substring is referred to as a ``groupSelectionPattern``. For example, if the pattern was
    "hello", all histograms containing "hello" would be selected. Additional properties related to 
    groups, such as display information, are also stroed.

    Args:
        prettyName (str): Readable name of the group.
        groupSelectionPattern (str): Pattern of the histogram names that will be selected. For example, if
            wanted to select histograms related to EMCal patch amplitude, we would make the pattern something
            like "PatchAmp". The pattern depends on the name of the histograms sent from the HLT.
        plotInGridSelectionPattern (str): Pattern which denotes whether the histograms should be plotted in
            a grid. ``plotInGrid`` is set based on whether this value is in ``groupSelectionPattern``. For
            example, in the EMCal, the ``plotInGridSelectionPattern`` is ``_SM``, since "SM" denotes a
            supermodule.

    Attributes:
        prettyName (str): Readable name of the group. Set via the ``groupName`` in the constructor.
        selectionPattern (str): Pattern of the histogram names that will be selected.
        plotInGridSelectionPattern (str): Pattern (substring) which denotes whether the histograms should be
            plotted in a grid.
        plotInGrid (bool): True when the histograms should be plotted in a grid.
        histList (PersistentList): List of histogram names that should be filled when the ``selectionPattern`` is matched.
    """
    def __init__(self, prettyName, groupSelectionPattern, plotInGridSelectionPattern = "DO NOT PLOT IN GRID"):
        self.prettyName = prettyName
        self.selectionPattern = groupSelectionPattern
        self.plotInGridSelectionPattern = plotInGridSelectionPattern
        self.histList = persistent.list.PersistentList()

        # So that it is not necessary to check the list every time
        if self.plotInGridSelectionPattern in self.selectionPattern:
            self.plotInGrid = True
        else:
            self.plotInGrid = False

class histogramContainer(persistent.Persistent):
    """ Histogram information container.

    Organizes information about a particular histogram (or set of histograms). Manages functions that
    process and otherwise modify the histogram, which are specified through the plugin system. The
    container also manages plotting details.

    Note:
        The histogram container doesn't always have access to the underlying histogram. When constructing
        the container, it is useful to have the histogram available to provide some information, but then
        the histogram should not be needed until final processing is performed and the hist is plotted.
        When this final step is reached, the histogram can be retrieved by ``retrieveHistogram()`` helper
        function.

    Args:
        histName (str): Name of the histogram. Doesn't necessarily need to be the same as `TH1.GetName()`.
        histList (list): List of histogram names that should contribute to this container. Used for stacking
            multiple histograms on onto one canvas. Default: None
        prettyName (str): Name of the histogram that is appropriate for display. Default: ``None``, which
            will lead to be it being set to ``histName``.

    Attributes:
        histName (str): Name of the histogram. Doesn't necessarily need to be the same as `TH1.GetName()`.
        prettyName (str): Name of the histogram that is appropriate for display.
        histList (list): List of histogram names that should contribute to this container. Used for stacking
            multiple histograms on onto one canvas. Default: None. See ``retrieveHistogram()`` for more
            information on how this functionality is utilized.
        information (PersistentMapping): Information that is extracted from the histogram that should be
            stored persistently and displayed. This information will be displayed with the web app, with
            the key shown as a clickable button, and the value information stored behind it.
        hist (ROOT.TH1): The histogram which this container wraps.
        histType (ROOT.TClass): Class of the histogram. For example, ``ROOT.TH1F``. Can be used for functions
            that only apply to 2D hists, etc. It is stored separately from the histogram to allow for it to
            be available even when the underlying histogram is not (as occurs while setting up but not yet
            processing a histogram).
        drawOptions (str): Draw options to be passed to ``TH1.Draw()`` when drawing the histogram.
        canvas (ROOT.TCanvas): Canvas onto which the histogram will be plotted. Available after the histogram
            has been classified (ie in processing functions).
        projectionFunctionsToApply (PersistentList): List-like object of functions that perform projections
            to the histogram that is represented by this container. See the detector system README for more
            information.
        functionsToApply (PersistentList): List-like object of functions that are applied to the histogram
            during the processing step. See the detector subsystem README for more information.
        trendingObjects (PersistentList): List-like object of trending objects which operate on this
            histogram. See the detector system and trending README for more information.
    """
    def __init__(self, histName, histList = None, prettyName = None):
        # Replace any slashes with underscores to ensure that it can be used safely as a filename
        #histName = histName.replace("/", "_")
        self.histName = histName
        # Only assign if meaningful
        if prettyName is not None:
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
        # Functions which will be applied to project an available histogram to a new derived histogram
        self.projectionFunctionsToApply = persistent.list.PersistentList()
        # Functions which will be applied to the histogram each time it is processed
        self.functionsToApply = persistent.list.PersistentList()
        # Trending objects which use this histogram
        self.trendingObjects = persistent.list.PersistentList()

    def retrieveHistogram(self, ROOT, fIn = None, trending = None):
        """ Retrieve the histogram from the given file or trending container.

        This function can retrieve a single histogram from a file, multiple hists from a file
        to create a stack (based on the hist names in ``histList``), or a single trending
        histogram stored in the collection of trending objects.

        Args:
            ROOT (ROOT): ROOT module. Passed into this object so this module doesn't need
                to directly depend on importing ROOT.
            fIn (ROOT.TFile): File in which the histogram(s) is stored. Default: ``None``.
            trending (trendingContainer): Contains the trending objects, including the trending
                histogram which is represented in this histogram container. It is the source
                of the histogram, and therefore similar to the input ROOT file. Default: ``None``.
        Returns:
            bool: True if the histogram was successfully retrieved.
        """
        returnValue = True
        if fIn:
            if not self.histList is None:
                if len(self.histList) > 1:
                    self.hist = ROOT.THStack(self.histName, self.histName)
                    for name in self.histList:
                        logger.debug("HistName in list: {0}".format(name))
                        self.hist.Add(fIn.GetKey(name).ReadObj())
                    self.drawOptions += "nostack"
                    # TODO: Allow for further configuration of THStack, like TLegend and such
                elif len(self.histList) == 1:
                    # Projective histogram
                    histName = next(iter(self.histList))
                    logger.debug("Retrieving histogram {} for projection!".format(histName))
                    # Clone the histogram so restricted ranges don't propagate to other uses of this hist
                    tempHist = fIn.GetKey(histName)
                    if tempHist:
                        self.hist = tempHist.ReadObj().Clone("{}_temp".format(histName))
                    else:
                        returnValue = False
                else:
                    logger.warning("histList for hist {} is defined, but is empty".format(histName))
                    returnValue = False
            else:
                logger.debug("HistName: {0}".format(self.histName))
                tempHist = fIn.GetKey(self.histName)
                if tempHist:
                    self.hist = tempHist.ReadObj()
                else:
                    returnValue = False
        elif trending:
            # Retrieve the trending histogram from the collection of trending objects.
            returnValue = False
            # Not particularly efficient, but it's straightforward.
            for subsystemName, subsystem in iteritems(trending.trendingObjects):
                for name, trendingObject in iteritems(subsystem):
                    if self.histName in trendingObject.hist.histName:
                        # Retrieve the graph and make it available in the trending histogram container
                        trendingObject.retrieveHistogram()
                        returnValue = True
                        #self.hist = trending.trendingObjects[subsystemName][self.histName].trendingHist
        else:
            logger.warning("Unable to retrieve histogram {}".format(self.histName))
            returnValue = False

        return returnValue

class trendingObject(persistent.Persistent):
    """ Base class for trending object.

    Implements storing trending values using a ``TGraphErrors`` based fill method. Each trending object
    should inherit from this class, implementing value extraction in an overridden ``fill()`` method,
    and then call the base class to perform the value storage. Note that this object is designed only
    for trending 1D objects.

    For more information on the trending subsystem, see the detector subsystem and trending README.

    Note:
        We refer to a histogram in this object, but it doesn't actually need to be a histogram.
        A ``TGraph``, ``TGraphErrors``, or other objects are all fine options.

    Args:
        trendingName (str): Name of the trending object.
        prettyTrendingName (str): Name of the trending object that is appropriate for display.
        nEntries (int): Number of entries the trending object should contain.
        histNames (list): List of the names of histograms which are needed to perform the trending.
        trendingHist (ROOT.TH1 or ROOT.TGraphErrors): Hist or graph where the trending values will be stored.
            Default: ``None``, which will cause a ``TGraphErrors`` to be automatically created.

    Attributes:
        name (str): Name of the trending object.
        prettyTrendingName (str): Name of the trending object that is appropriate for display.
        nEntries (int): Number of entries the trending object should contain.
        values (np.array): (nEntries, 2) array which contains the value and error.
        hist (histogramContainer): Container for the trending histogram.
        histNames (list): List of the names of histograms which are needed to perform the trending.
        nextEntry (int): Location where the next trending entry should go.
        canvas (ROOT.TCanvas): Canvas onto which the hist will be plotted.
    """

    def __init__(self, trendingName, prettyTrendingName, nEntries, histNames, trendingHist = None):
        self.name = trendingName
        self.prettyName = prettyTrendingName
        self.nEntries = nEntries
        # Store the trending values
        # TODO: Should the unix time also be included?
        # Tuple of (value, error)
        self.values = np.zeros((nEntries, 2), dtype=np.float)

        self.hist = histogramContainer(trendingName)
        self.hist.hist = trendingHist

        # Set histograms to be included
        if not histNames:
            histNames = []
        # Ensure that a copy is name by wrapping in list
        self.histNames = list(histNames)

        # Where the next entry should go
        self.nextEntry = 1

        # Visualization of the trending object
        self.canvas = None

    def fill(self, value, error):
        """ Base method to store a trended value and its error.

        The name of this method is selected due to the similarity between storing the
        trended value and filling a histogram. Note that it is up to the derived class
        to determine how to actually extract this trended value.

        Args:
            value (float): Trending value to be filled.
            error (float): Trending error value to be filled.
        Returns:
            None
        """
        logger.debug("name: {}, self.nextEntry: {}, value: {}".format(self.name, self.nextEntry, value))
        currentEntry = self.nextEntry - 1
        if self.nextEntry > self.nEntries:
            # Remove the oldest entry
            utilities.removeOldestValueAndInsert(self.values, (value, error))

        self.values[currentEntry] = (value, error)
        logger.debug("name: {}, values: {}".format(self.name, self.values))

        # Keep track to move to the next entry
        self.nextEntry += 1

    def retrieveHistogram(self):
        """ Retrieve or create a graph based on the stored numpy array.

        This method will create a new graph if it doesn't exist. Otherwise, it will
        set the bin contents of an existing ``TH1``. The retrieved histogram is
        stored in the object's histogram container.

        Note:
            We refer to a histogram in this method name, but it doesn't actually need to be a histogram.
            A ``TGraphErrors`` or other objects that supports storing values and errors is a fine options.
            For this function, we return a ``TGraphErrors`` if a histogram was not already passed.

        Args:
            None
        Returns:
            histogramContainer: Container which holds the created graph. It is returned to allow for
                further customization. This histogram container is already stored in the object.
        """
        # The creation of this hist can be overridden by creating the histogram before now
        if not self.hist.hist:
            # Define TGraph
            # TH1's need to be defined more carefully, as they seem to possible cause memory corruption
            # Multiply by 60.0 because it expects the times in seconds
            self.hist.hist = ROOT.TGraphErrors(self.nEntries)

            # Set options
            self.hist.hist.SetName(self.name)
            self.hist.hist.SetTitle(self.prettyName)
            # Ensure that the axis and points are drawn on the TGraph
            self.hist.drawOptions = "AP"

        # Handle histogram, which needs overflow and underflow
        if self.hist.hist.InheritsFrom(ROOT.TH1.Class()):
            logger.debug("GetNbins: {}, GetEntries: {}".format(self.hist.hist.GetXaxis().GetNbins(), self.hist.hist.GetEntries()))

            # Need to pass with zeros for the over and underflow bins values, errors
            valuesWithOverAndUnderflow = np.concatenate([[(0,0)], self.values, [(0,0)]])
            logger.debug("valuesWithOverAndUnderflow: {}".format(valuesWithOverAndUnderflow))

            # Access the ctypes via: https://docs.scipy.org/doc/numpy-1.14.0/reference/generated/numpy.ndarray.ctypes.html
            self.hist.hist.SetContent(valuesWithOverAndUnderflow[:, 0].ctypes.data_as(ctypes.POINTER(ctypes.c_long)))
            self.hist.hist.SetError(valuesWithOverAndUnderflow[:, 1].ctypes.data_as(ctypes.POINTER(ctypes.c_long)))
        else:
            # Handle points in a TGraph
            #logger.debug("Filling TGraph with array values of {}".format(self.values))
            for i in range(0, len(self.values)):
                #logger.debug("Setting point {} to ({}, {}) with error {}".format(i, i, self.values[i, 0], self.values[i,1]))
                self.hist.hist.SetPoint(i, i, self.values[i, 0])
                self.hist.hist.SetPointError(i, i, self.values[i, 1])

        # The hist is already available through the histogram container, but we return the hist
        # container in case the caller wants to do additional customization
        return self.hist
