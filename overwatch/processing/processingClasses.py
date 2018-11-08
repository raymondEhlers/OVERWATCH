#!/usr/bin/env python

""" Classes that define the processing structure of Overwatch.

Classes that define the structure of processing. This information can be created and processed,
or read from file.

Note:
    For the ``__repr__`` and ``__str__`` methods defined here, they can throw ``KeyError`` for class attributes
    if the these methods rely on ``__dict__`` and the objects have just been loaded from ZODB. Presumably, ``__dict__``
    doesn't cause ZODB to fully load the object. To work around this issue, any methods using ``__dict__`` first
    call some attribute (ideally, something simple) to ensure that the object is fully loaded. The result of that call
    is ignored.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

from __future__ import print_function
from __future__ import absolute_import
from future.utils import iteritems
from future.utils import itervalues

# Database
import BTrees.OOBTree
import persistent

import os
import numpy as np
import pendulum
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
            formatted as ``Run123456``.
        fileMode (bool): If true, the run data was collected in cumulative mode. See the
            :doc:`processing README </processingReadme>` for further information.
        hltMode (str): String containing the HLT mode used for the run.

    Attributes:
        runDir (str): String containing the run number. For an example run 123456, it should be
            formatted as ``Run123456``
        runNumber (int): Run number extracted from the ``runDir``.
        prettyName (str): Reformatting of the ``runDir`` for improved readability.
        fileMode (bool): If true, the run data was collected in cumulative mode. See the
            :doc:`processing README </processingReadme>` for further information. Set via ``fileMode``.
        subsystems (BTree): Dict-like object which will contain all of the subsystem containers in
            an event. The key is the corresponding subsystem three letter name.
        hltMode (str): Mode the HLT operated in for this run. Valid HLT modes are "B", "C", "E", and "U".
            Further information on the various modes is in the :doc:`processing README </processingReadme>`.
            Default: ``None`` (which will be converted to "U", for "unknown").
    """
    def __init__(self, runDir, fileMode, hltMode = None):
        self.runDir = runDir
        self.runNumber = int(runDir.replace("Run", ""))
        self.prettyName = "Run {runNumber}".format(runNumber = self.runNumber)
        self.mode = fileMode
        self.subsystems = BTrees.OOBTree.BTree()
        self.hltMode = hltMode

        # Try to retrieve the HLT mode if it was not passed
        runDirectory = os.path.join(processingParameters["dirPrefix"], self.runDir)
        if not hltMode:
            self.hltMode = utilities.retrieveHLTModeFromStoredRunInfo(runDirectory = runDirectory)

        # Write run information
        utilities.writeRunInfoToFile(runDirectory = runDirectory, hltMode = hltMode)

    def __repr__(self):
        """ Representation of the object. """
        # Dummy call. See note at the top of the module.
        self.runDir
        return "{}(runDir = {runDir}, fileMode = {mode}, hltMode = {hltMode})".format(self.__class__.__name__, **self.__dict__)

    def __str__(self):
        """ Print many of the elements of the object. """
        return "{}: runDir: {runDir}, runNumber: {runNumber}, prettyName: {prettyName}, fileMode: {mode}," \
               " subsystems: {subsystems}, hltMode: {hltMode}".format(self.__class__.__name__,
                                                                      runDir = self.runDir,
                                                                      runNumber = self.runNumber,
                                                                      prettyName = self.prettyName,
                                                                      mode = self.mode,
                                                                      subsystems = list(self.subsystems.keys()),
                                                                      hltMode = self.hltMode)

    def isRunOngoing(self):
        """ Checks if a run is ongoing.

        The ongoing run check is performed by looking checking for a new file in
        any of the subsystems. If they have just received a new file, then the run
        is ongoing.

        Note:
            If ``subsystem.newFile`` is false, this is not a sufficient condition to say that
            the run has ended. This is because ``newFile`` will be set to false if the subsystem
            didn't have a file in the most recent processing run, even if the run is still
            ongoing. This can happen for many reasons, including if the processing is executed
            more frequently than the data transfer rate or receiver request rate, for example.
            However, if ``newFile`` is true, then it is sufficient to know that the run is ongoing.

        Args:
            None
        Returns:
            bool: True if the run is ongoing.
        """
        returnValue = False
        try:
            for subsystem in itervalues(self.subsystems):
                if subsystem.newFile is True:
                    # We know we have a new file, so nothing else needs to be done. Just return it.
                    returnValue = True
                    break

            # If we haven't found a new file yet, we'll check the time stamps.
            if returnValue is False:
                logger.debug("Checking timestamps for whether the run in ongoing.")
                minutesSinceLastTimestamp = self.minutesSinceLastTimestamp()
                logger.debug("{minutesSinceLastTimestamp} minutes since the last timestamp.".format(minutesSinceLastTimestamp = minutesSinceLastTimestamp))
                # Compare the unix timestamps with a five minute buffer period.
                # This buffer time is arbitrarily selected, but the value is motivated by a balance to ensure
                # that a missed file doesn't cause the run to appear over, while also not claiming that the
                # run continues much longer than it actually does.
                if minutesSinceLastTimestamp < 5:
                    returnValue = True
        except KeyError:
            returnValue = False

        return returnValue

    def minutesSinceLastTimestamp(self):
        """ Determine the time since the last file timestamp in minutes.

        Args:
            None.
        Returns:
            float: Minutes since the timestamp of the most recent file. Default: -1.
        """
        timeSinceLastTimestamp = -1
        try:
            mostRecentTimestamp = -1
            for subsystem in itervalues(self.subsystems):
                newestFile = subsystem.files[subsystem.files.keys()[-1]]
                if newestFile.fileTime > mostRecentTimestamp:
                    mostRecentTimestamp = newestFile.fileTime

            # The timestamps of the files are set in Geneva, so we need to construct the timestamp in Geneva
            # to compare against. The proper timezone for this is "Europe/Zurich".
            geneva = pendulum.from_timestamp(mostRecentTimestamp, tz = "Europe/Zurich")
            now = pendulum.now()
            # Return in minutes
            timeSinceLastTimestamp = now.diff(geneva).in_minutes()
        except KeyError:
            # If there is a KeyError somewhere, we just ignore it and pass back the default value.
            pass

        return timeSinceLastTimestamp

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
    :doc:`processing README </processingReadme>`.

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
            can be uniquely identified), while a timeSliceContainer with the corresponding time slice properties
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
        self.subsystem = subsystem
        self.showRootFiles = showRootFiles

        # If data does not exist for this subsystem then it is dependent on HLT data
        # Detect it automatically if not passed to the initialization.
        if fileLocationSubsystem is None:
            # Use the subsystem directory as proxy for whether it exists.
            # NOTE: This detection works, but it isn't so flexible.
            if os.path.exists(os.path.join(processingParameters["dirPrefix"], runDir, subsystem)):
                self.fileLocationSubsystem = self.subsystem
            else:
                self.fileLocationSubsystem = "HLT"
        else:
            self.fileLocationSubsystem = fileLocationSubsystem

        if self.showRootFiles is True and self.subsystem != self.fileLocationSubsystem:
            logger.info("\tIt is requested to show ROOT files for subsystem {subsystem}, but the subsystem does not have specific data files. Using HLT data files!".format(subsystem = subsystem))

        # Files
        # Be certain to set these after the subsystem has been created!
        # Contains all files for that particular run
        self.files = BTrees.OOBTree.BTree()
        self.timeSlices = persistent.mapping.PersistentMapping()
        # Only one combined file, so we do not need a dict!
        self.combinedFile = None

        # Directories
        self.setupDirectories(runDir)

        # Times
        self.startOfRun = startOfRun
        self.endOfRun = endOfRun
        # The run length is in minutes
        self.runLength = (endOfRun - startOfRun) // 60

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

    def setupDirectories(self, runDir):
        """ Helper function to setup the subsystem directories.

        Defines the base, img, and JSON directories, as well as creating the them if necessary.

        Args:
            runDir (str): String containing the run number. For an example run 123456, it should be
                formatted as ``Run123456``
        Returns:
            None. However, it sets the ``baseDir``, ``imgDir``, and ``jsonDir`` properties of the ``subsystemContainer``.
        """
        # Depends on whether the subsystem actually contains the files!
        self.baseDir = os.path.join(runDir, self.fileLocationSubsystem)
        self.imgDir = os.path.join(self.baseDir, "img")
        self.jsonDir = os.path.join(self.baseDir, "json")
        # Ensure that they exist
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.imgDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.imgDir))
        if not os.path.exists(os.path.join(processingParameters["dirPrefix"], self.jsonDir)):
            os.makedirs(os.path.join(processingParameters["dirPrefix"], self.jsonDir))

    def __repr__(self):
        """ Representation of the object. """
        return "{}(subsystem = {subsystem}, runDir = {runDir}, startOfRun = {startOfRun}," \
               " endOfRun = {endOfRun}, showRootFiles = {showRootFiles}," \
               " fileLocationSubsystem = {fileLocationSubsystem})".format(self.__class__.__name__,
                                                                          subsystem = self.subsystem,
                                                                          runDir = os.path.dirname(self.baseDir),
                                                                          startOfRun = self.startOfRun,
                                                                          endOfRun = self.endOfRun,
                                                                          showRootFiles = self.showRootFiles,
                                                                          fileLocationSubsystem = self.fileLocationSubsystem)

    def __str__(self):
        """ Print many of the elements of the object. """
        return "{}: subsystem: {subsystem}, fileLocationSubsystem: {fileLocationSubsystem}," \
               " showRootFiles: {showRootFiles}, startOfRun: {startOfRun}, endOfRun: {endOfRun}," \
               " newFile: {newFile}, hists: {hists}".format(self.__class__.__name__,
                                                            subsystem = self.subsystem,
                                                            fileLocationSubsystem = self.fileLocationSubsystem,
                                                            showRootFiles = self.showRootFiles,
                                                            startOfRun = self.startOfRun,
                                                            endOfRun = self.endOfRun,
                                                            newFile = self.newFile,
                                                            hists = list(self.hists.keys()))

    @staticmethod
    def prettyPrintUnixTime(unixTime):
        """ Converts the given time stamp into an appropriate manner ("pretty") for display.

        The time is returned in the format: "Tuesday, 6 Nov 2018 20:55:10". This function is
        mainly needed in Jinja templates were arbitrary functions are not allowed.

        Note:
            We display this in the CERN time zone, so we convert it here to that timezone.

        Args:
            unixTime (int): Unix time to be converted.
        Returns:
            str: The time stamp converted into an appropriate manner for display.
        """
        d = pendulum.from_timestamp(unixTime, tz = "Europe/Zurich")
        return d.format("dddd, D MMM YYYY HH:mm:ss")

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

    def __repr__(self):
        """ Representation of the object. """
        # Dummy call. See note at the top of the module.
        self.minUnixTimeRequested
        return "{}(minUnixTimeRequested = {minUnixTimeRequested}, maxUnixTimeRequested = {maxUnixTimeRequested}," \
               " minUnixTimeAvailable = {minUnixTimeAvailable}, maxUnixTimeAvailable = {maxUnixTimeAvailable}," \
               " startOfRun = {startOfRun}, filesToMerge = {filesToMerge}," \
               " optionsHash = {optionsHash}".format(self.__class__.__name__, **self.__dict__)

    def __str__(self):
        """ Print many of the elements of the object. """
        return "{}: minUnixTimeRequested = {minUnixTimeRequested}, maxUnixTimeRequested = {maxUnixTimeRequested}," \
               " minUnixTimeAvailable = {minUnixTimeAvailable}, maxUnixTimeAvailable = {maxUnixTimeAvailable}," \
               " filenamePrefix: {filenamePrefix}, startOfRun = {startOfRun}, filesToMerge = {filesToMerge}," \
               " optionsHash = {optionsHash}".format(self.__class__.__name__,
                                                     minUnixTimeRequested = self.minUnixTimeRequested,
                                                     maxUnixTimeRequested = self.maxUnixTimeRequested,
                                                     minUnixTimeAvailable = self.minUnixTimeAvailable,
                                                     maxUnixTimeAvailable = self.maxUnixTimeAvailable,
                                                     filenamePrefix = self.filenamePrefix,
                                                     startOfRun = self.startOfRun,
                                                     filesToMerge = self.filesToMerge,
                                                     optionsHash = self.optionsHash)

    def timeInMinutes(self, inputTime):
        """ Return the time from the input unix time to the start of the run in minutes.

        Args:
            inputTime (int): Unix time to be compared to the start of run time.
        Returns:
            int: Minutes from the start of run to the given time.
        """
        #logger.debug("inputTime: {inputTime}, startOfRun: {startOfRun}".format(inputTime = inputTime, startOfRun = self.startOfRun))
        return (inputTime - self.startOfRun) // 60

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
        filenae (str): Filename of the corresponding file. This is expected to the full path
            from the ``dirPrefix`` to the file.
        startOfRun (int): Start of the run in unix time. Default: ``None``. The default will lead
            to timeIntoRun being set to ``-1``. The default is most commonly used for time slices,
            where the start of run isn't so meaningful.

    Attributes:
        filenae (str): Filename of the corresponding file. This is expected to the full path
            from the ``dirPrefix`` to the file.
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

    def __repr__(self):
        """ Representation of the object. """
        return "{}(filename = {filename}, startOfRun = {startOfRun})".format(self.__class__.__name__,
                                                                             filename = self.filename,
                                                                             startOfRun = self.fileTime - self.timeIntoRun)

    def __str__(self):
        """ Print the elements of the object. """
        # Dummy call. See note at the top of the module.
        self.filename
        return "{}: filename = {filename}, combinedFile: {combinedFile}, timeSlice: {timeSlice}," \
               " fileTime: {fileTime}, timeIntoRun: {timeIntoRun}".format(self.__class__.__name__, **self.__dict__)

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

    def __repr__(self):
        """ Representation of the object. """
        # Dummy call. See note at the top of the module.
        self.prettyName
        return "{}(prettyName = {prettyName}, groupSelectionPattern = {groupSelectionPattern}," \
               " plotInGridSelectionPattern = {plotInGridSelectionPattern}".format(self.__class__.__name__, **self.__dict__)

    def __str__(self):
        """ Print the elements of the object. """
        # Dummy call. See note at the top of the module.
        self.prettyName
        return "{}: prettyName = {prettyName}, groupSelectionPattern = {groupSelectionPattern}," \
               " plotInGridSelectionPattern = {plotInGridSelectionPattern}, histList: {histList}," \
               " plotInGrid: {plotInGrid}".format(self.__class__.__name__, **self.__dict__)

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
        histName (str): Name of the histogram. Doesn't necessarily need to be the same as ``TH1.GetName()``.
        histList (list): List of histogram names that should contribute to this container. Used for stacking
            multiple histograms on onto one canvas. Default: None
        prettyName (str): Name of the histogram that is appropriate for display. Default: ``None``, which
            will lead to be it being set to ``histName``.

    Attributes:
        histName (str): Name of the histogram. Doesn't necessarily need to be the same as ``TH1.GetName()``.
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
            to the histogram that is represented by this container. See the :doc:`detector subsystem README </detectorPluginsReadme>`
            for more information.
        functionsToApply (PersistentList): List-like object of functions that are applied to the histogram
            during the processing step. See the :doc:`detector subsystem README </detectorPluginsReadme>`
            for more information.
        trendingObjects (PersistentList): List-like object of trending objects which operate on this
            histogram. See the :doc:`detector subsystem and trending README </detectorPluginsReadme>`
            for more information.
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

    def __repr__(self):
        """ Representation of the object. """
        # Dummy call. See note at the top of the module.
        self.histName
        return "{}(histName = {histName}, histList = {histList}, prettyName = {prettyName})".format(self.__class__.__name__, **self.__dict__)

    def __str__(self):
        """ Print many of the elements of the object. """
        # Dummy call. See note at the top of the module.
        self.histName
        return "{}: histName = {histName}, histList = {histList}, prettyName = {prettyName}," \
               " information: {information}, hist: {hist}, histType: {histType}, drawOptions: {drawOptions}," \
               " canvas: {canvas}, projectionFunctionsToApply: {projectionFunctionsToApply}," \
               " functionsToApply: {functionsToApply}".format(self.__class__.__name__, **self.__dict__)

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
            if self.histList is not None:
                if len(self.histList) > 1:
                    self.hist = ROOT.THStack(self.histName, self.histName)
                    for name in self.histList:
                        logger.debug("HistName in list: {name}".format(name = name))
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
                    logger.warning("histList for hist {} is defined, but is empty".format(self.histName))
                    returnValue = False
            else:
                logger.debug("HistName: {histName}".format(histName = self.histName))
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
