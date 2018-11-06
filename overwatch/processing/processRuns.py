#!/usr/bin/env python

""" Steers and executes Overwatch histogram processing.

Takes files received from the HLT, organizes the information within a directory structure,
and processes the histograms within. It provides plugin opportunities throughout the all
processing and trending steps.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

from __future__ import print_function
from future.utils import iteritems
from future.utils import itervalues

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
import copy
import hashlib
import os
import uuid
import logging
logger = logging.getLogger(__name__)

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
from . import pluginManager
from . import processingClasses
from .trending.manager import TrendingManager


def processRootFile(filename, outputFormatting, subsystem, processingOptions = None,
                    forceRecreateSubsystem = False, trendingManager = None):
    """ Given a root file, process all histograms for a given subsystem.

    Processing includes assigning the contained histograms to a subsystem, allowing for customization via
    the plugin system. For a new subsystem, the processing proceeds in the following order:

    - Create histogram containers for histograms in the file.
    - Create new histograms (in addition to those already in the file).
    - Create histogram stacks.
    - Specify histogram options.
    - Create histogram groups.
    - Sort histograms into histogram groups.
    - For each sorted histogram:
        - Determine which processing functions to apply to which histograms.
        - Determine which trending functions require which histograms.

    Processing then proceeds to apply those functions to all sorted histograms. The final histograms are then
    stored as images and as ``json``. In the case that the subsystem already exists, we can skip all of those
    steps and simply apply the processing functions. If a histogram was not sorted then it belongs to another
    subsystem and could be processed by it later (depending on the configured subsystems).

    Note:
        Trending objects are filled (in ``processHist()``) when the relevant hists are processed in this function.

    Args:
        filename (str): The full path to the file to be processed.
        outputFormatting (str): Specially formatted string which contains a generic path to be used when printing
            histograms.  It must contain ``base``, ``name``, and ``ext``, where ``base`` is the base path, ``name``
            is the filename and ``ext`` is the extension. Ex: ``{base}/{name}.{ext}``.
        subsystem (subsystemContainer): Contains information about the current subsystem.
        processingOptions (dict): Implemented by the subsystem to note options used during standard processing. Keys
            are names of options, while values are the corresponding option values. Default: ``None``. Note: In this case,
            it will use the default subsystem processing options.
        forceRecreateSubsystem (bool): True if subsystems will be recreated, even if they already exist.
        trendingManager (TrendingManager): Manages the trending subsystem.
    Returns:
        None. However, the underlying subsystems, histograms, etc, are modified.
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
    # We know it is the first run if there are no histograms for this subsystem.
    if not subsystem.hists:
        for key in keysInFile:
            classOfObject = ROOT.TClass.GetClass(key.GetClassName())
            if classOfObject.InheritsFrom(ROOT.TH1.Class()):
                # Create histogram object
                hist = processingClasses.histogramContainer(key.GetName())
                # Wait to read the object until we are actually going to process it.
                hist.hist = None
                hist.canvas = None
                # However, store the object type so we know how to configure it without the underlying
                # hist being available.
                hist.histType = classOfObject

                # Store the histogram container so we can continue processing.
                subsystem.histsInFile[hist.histName] = hist

                # Extract the number of events if the proper histogram is available.
                # NOTE: This requires other histograms not to have "events" in their name,
                #       but so far (Aug 2018), this seems to be a reasonable assumption.
                if "events" in hist.histName.lower():
                    subsystem.nEvents = key.ReadObj().GetBinContent(1)

        # Create additional histograms
        #logger.debug("pre  create additional histsAvailable: {}".format(", ".join(subsystem.histsAvailable.keys())))
        pluginManager.createAdditionalHistograms(subsystem)
        #logger.debug("post create additional histsAvailable: {}".format(", ".join(subsystem.histsAvailable.keys())))

        # Create the subsystem stacks
        pluginManager.createHistogramStacks(subsystem)

        # Customize histogram traits
        pluginManager.setHistogramOptions(subsystem)

        # Create histogram sorting groups
        if not subsystem.histGroups:
            sortingSuccess = pluginManager.createHistGroups(subsystem)
            if sortingSuccess is False:
                logger.debug("Subsystem {subsystem} does not have a sorting function. Adding all histograms into one group!".format(subsystem = subsystem.subsystem))

                if subsystem.fileLocationSubsystem != subsystem.subsystem:
                    selection = subsystem.subsystem
                else:
                    # NOTE: In addition to being a normal option, this ensures that the HLT will always catch all
                    #       extra histograms from HLT files!
                    #       However, having this selection for other subsystems is dangerous, because it will include
                    #       many unrelated hists
                    selection = ""
                logger.info("selection: {selection}".format(selection = selection))
                subsystem.histGroups.append(processingClasses.histogramGroupContainer(subsystem.subsystem + " Histograms", selection))

        # See how we've done.
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

            # See if we've classified successfully.
            logger.info("{subsystem} hist: {histName} - classified: {classifiedHist}".format(subsystem = subsystem.subsystem, histName = hist.histName, classifiedHist = classifiedHist))

            if classifiedHist:
                # Determine the processing functions to apply
                pluginManager.findFunctionsForHist(subsystem, hist)
                # Add it to the subsystem
                subsystem.hists[hist.histName] = hist
            else:
                # We don't want to process histograms which haven't been defined.
                logger.debug("Skipping histogram {} since it is not classifiable for subsystem {}".format(hist.histName, subsystem.subsystem))

    # Set the proper processing options
    # If it was passed in, it was probably from time slices
    if processingOptions is None:
        processingOptions = subsystem.processingOptions
    logger.debug("processingOptions: {processingOptions}".format(processingOptions = processingOptions))

    # Canvases must have unique names - otherwise they will be replaced, leading to segfaults.
    # Start of run should unique to each run!
    canvas = ROOT.TCanvas("processRunsCanvas{}{}".format(subsystem.subsystem, subsystem.startOfRun),
                          "processRunsCanvas{}{}".format(subsystem.subsystem, subsystem.startOfRun))
    # Loop over histograms and draw
    for histGroup in subsystem.histGroups:
        for histName in histGroup.histList:
            # Retrieve histogram container and underlying histogram
            hist = subsystem.hists[histName]
            retrievedHist = hist.retrieveHistogram(fIn = fIn, ROOT = ROOT)
            if not retrievedHist:
                logger.warning("Could not retrieve histogram for hist {}, histList: {}".format(hist.histName, hist.histList))
                continue
            processHist(subsystem = subsystem, hist = hist, canvas = canvas, outputFormatting = outputFormatting,
                        processingOptions = processingOptions, trendingManager = trendingManager)

    # Since we are done, we can cleanup by closing the file.
    fIn.Close()

def processHist(subsystem, hist, canvas, outputFormatting, processingOptions,
                subsystemName = None, trendingManager = None):
    """ Main histogram processing function.

    This function is responsible for taking a given ``histogramContainer``, process the underlying histogram
    via processing functions, fill trending objects (if applicable), and then store the result in images and
    ``json`` for display in the web app. Here, we execute the plug-in functionality assigned earlier and
    perform the actual drawing of the hist onto a canvas.

    In more detail, we processing steps performed here are:

    - Setup the canvas.
    - Apply the projection functions (if applicable) to get the proper histogram.
    - Draw the histogram.
    - Apply the processing functions (if applicable).
    - Write the output to image and ``json``.
    - Cleanup the hist and canvas by removing reference to them.

    Note:
        The hist is drawn **before** calling the processing function to allow the plug-ins to draw on top of the histogram.

    Note:
        The ``json`` that is written is by ``TBufferJSON`` for display via ``jsRoot``. While it stores the information,
        it requires ``jsRoot`` to be displayed meaningfully.

    Note:
        This function is built in such a way that it works for processing both histograms and trending objects.
        For this to work, both the ``subsystemContainer`` and the ``trendingContainer`` must support the following
        methods: ``imgDir()``, which is the image storage directory, and ``jsonDir()``, which is the ``json`` storage
        directory. Both should except to get formatted with `` % {"subsystem": subsystemName}``.

    Args:
        subsystem (subsystemContainer or trendingContainer): Subsystem or trending container which contains the histogram
            being processed. It only uses a subset of either classes methods. See the note for information about the
            requirements of this object.
        hist (histogramContainer): Histogram to be processed.
        canvas (TCanvas): Canvas on which the histogram should be plotted. It will be stored in the ``histogramContainer``
            for the purposes of processing the hist.
        outputFormatting (str): Specially formatted string which contains a generic path to be used when printing histograms.
            It must contain ``base``, ``name``, and ``ext``, where ``base`` is the base path, ``name`` is the filename
            and ``ext`` is the extension. Ex: ``{base}/{name}.{ext}``.
        processingOptions (dict): Implemented by the subsystem to note options used during standard processing. Keys
            are names of options, while values are the corresponding option values. Default: ``None``. Note: In this case,
            it will use the default subsystem or trending processing options.
        subsystemName (str): The current subsystem by three letter, all capital name (ex. ``EMC``).  Default: ``None``.
            In that case of ``None``, the subsystem name is retrieved from ``subsystem.subsystem``. This argument is used
            for processing the trending objects where we don't have access to their corresponding ``subsystemContainer``.
            The subsystem name of the ``trendingContainer`` (``TDG``) does not necessarily correspond to the subsystem
            of the object being processed, so we have to pass it here.
        trendingManager (TrendingManager): Will be notified when as histogram is processed to allow the use of
            the histogram values in trending.
    Returns:
        None. However, the subsystem, histogram, etc are modified and their representations in images
            and ``json`` are written to disk.
    """
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
        logger.debug("Calling projection func: {func}".format(func = func))
        hist.hist = func(subsystem, hist, processingOptions)

    # Setup and draw histogram
    # Turn off title, but store the value
    ROOT.gStyle.SetOptTitle(0)
    logger.debug("hist: {}, hist.hist: {}".format(hist, hist.hist))
    hist.hist.Draw(hist.drawOptions)

    # Call functions for each hist
    #logger.debug("Functions to apply: {functionsToApply}".format(functionsToApply = hist.functionsToApply))
    for func in hist.functionsToApply:
        logger.debug("Calling func: {func}".format(func = func))
        func(subsystem, hist, processingOptions)

    logger.debug("histName: {}, hist: {}".format(hist.histName, hist.hist))

    if trendingManager:
        trendingManager.notifyAboutNewHistogramValue(hist)

    # Save
    outputName = hist.histName
    # Replace any slashes with underscores to ensure that it can be used safely as a filename.
    # For example, the TPC has historically had a `/` in the name. This is fine everywhere except
    # when attempting to use the name as a filename.
    outputName = outputName.replace("/", "_")
    outputFilename = outputFormatting.format(base = os.path.join(processingParameters["dirPrefix"], subsystem.imgDir % {"subsystem": subsystemName}),
                                             name = outputName,
                                             ext = processingParameters["fileExtension"])
    logger.debug("Saving hist to {outputFilename}".format(outputFilename = outputFilename))
    hist.canvas.SaveAs(outputFilename)

    # Write BufferJSON
    jsonBufferFile = outputFormatting.format(base = os.path.join(processingParameters["dirPrefix"], subsystem.jsonDir % {"subsystem": subsystemName}),
                                             name = outputName,
                                             ext = "json")
    #logger.debug("jsonBufferFile: {jsonBufferFile}".format(jsonBufferFile = jsonBufferFile))
    # GZip is performed by the web server, not here!
    with open(jsonBufferFile, "wb") as f:
        f.write(ROOT.TBufferJSON.ConvertToJSON(canvas).Data().encode())

    # Clear hist and canvas so that we can successfully save
    hist.hist = None
    hist.canvas = None

def compareProcessingOptionsDicts(inputProcessingOptions, processingOptions, errors):
    """ Compare an input and existing processing options dictionaries.

    Compare the dictionary values stored in the input (``inputProcessingOptions``) to those in the reference
    (``processingOptions``). Both the keys and values are compared. For both dictionaries, keys are names of
    options, while values are the corresponding option values.

    Note:
        The existing processing options can have more entries than the input. Only the keys and values in the
        input are checked.

    Note:
        For the error format in ``errors``, see the :doc:`web app README </webAppReadme>`.

    Args:
        inputProcessingOptions (dict): Processing options specified in the time slice.
        processingOptions (dict): Processing options used during standard processing which serve as the reference options.
            These usually should be the subsystem processing options.
    Returns:
        tuple: (processingOptionsAreTheSame, errors) where ``processingOptionsAreTheSame`` (bool) is ``True`` if all input
            options are the same values as in the existing options and ``errors`` (dict) is an error dictionary in the
            proper format.
    """
    processingOptionsAreTheSame = True
    for key, val in iteritems(inputProcessingOptions):
        # Return the error immediately, as we can't properly compare the keys if they don't exist.
        if key not in processingOptions:
            errors.setdefault("Processing option error", []).append("Key \"{key}\" in inputProcessingOptions ({inputProcessingOptions}) is not in subsystem processingOptions {processingOptions}!".format(key = key, inputProcessingOptions = inputProcessingOptions, processingOptions = processingOptions))
            processingOptionsAreTheSame = False
            break
        if val != processingOptions[key]:
            processingOptionsAreTheSame = False
            break

    return (processingOptionsAreTheSame, errors)

def validateAndCreateNewTimeSlice(run, subsystem, minTimeMinutes, maxTimeMinutes, inputProcessingOptions):
    """ Validate and create a ``timeSliceContainer`` based on the given inputs.

    Validate the given time slice options, check the options to determine if we've already create the time
    slice, and then return the proper ``timeSliceContainer`` (either an existing container or a new one based
    on the result of the checks). By comparing the requested options and times with those that we have already
    processed, we can avoid having to reprocess existing data when nothing has changed. This effectively allows
    us to cache the processing results.

    The resulting ``timeSliceContainer`` is stored under a ``UUID`` generated string to ensure that they never
    overwrite each other.

    Note:
        For the error format in ``errors``, see the :doc:`web app README </webAppReadme>`.

    Args:
        run (runContainer): Run for which the time slice was requested.
        subsystem (subsystemContainer): Subsystem for which the time slice was requested.
        minTimeMinutes (int): Minimum time for the time slice in minutes.
        maxTimeMinutes (int): Maximum time for the time slice in minutes.
        inputProcessingOptions (dict): Processing options requested for the time slice.
    Returns:
        tuple: (timeSliceKey, newlyCreated, errors) where timeSliceKey (str) is the key under which the  relevant
            ``timeSliceContainer`` is stored in the ``subsystemContainer.timesSlices`` dict, newlyCreated (bool) is
            ``True`` if the ``timeSliceContainer`` was newly created (as opposed to already existing), and
            errors (dict) is an error dictionary in the proper format.
    """
    # Setup error dict
    errors = {}

    # User filter time, in unix time. This makes it possible to compare to the ``startOfRun`` and ``endOfRun`` times
    minTimeCutUnix = minTimeMinutes * 60 + subsystem.startOfRun
    maxTimeCutUnix = maxTimeMinutes * 60 + subsystem.startOfRun

    # If max filter time is greater than max file time, merge up to and including the last file
    if maxTimeCutUnix > subsystem.endOfRun:
        logger.warning("Input max time exceeds data! It has been reset to the maximum allowed.")
        maxTimeMinutes = subsystem.runLength
        maxTimeCutUnix = subsystem.endOfRun

    # Compare requested processing options to avoid additional computation if possible.
    processingOptionsAreTheSame, errors = compareProcessingOptionsDicts(inputProcessingOptions, subsystem.processingOptions, errors)
    # Handle errors immediately if they are returned.
    if errors != {}:
        return (None, None, errors)
    # Return immediately if it is just a full time request with the normal processing options
    # If all of the options are the same and the time range is the full run length, then the request is just
    # for the normal processing. Indicate this by returning ``"fullProcessing"``.
    if minTimeMinutes == 0 and maxTimeMinutes == round(subsystem.runLength) and processingOptionsAreTheSame:
        return ("fullProcessing", False, None)

    # If input time range is invalid, then return an error.
    logger.info("Filtering time window! Min:{minTimeMinutes}, Max: {maxTimeMinutes}".format(minTimeMinutes = minTimeMinutes, maxTimeMinutes = maxTimeMinutes))
    if minTimeMinutes < 0:
        logger.info("Minimum input time less than 0!")
        return (None, None, {"Request Error": ["Miniumum input time of \"{minTimeMinutes}\" is less than 0!".format(minTimeMinutes = minTimeMinutes)]})
    if minTimeCutUnix > maxTimeCutUnix:
        logger.info("Max time must be greater than Min time!")
        return (None, None, {"Request Error": ["Max time of \"{maxTimeMinutes}\" must be greater than the min time of {minTimeMinutes}!".format(maxTimeMinutes = maxTimeMinutes, minTimeMinutes = minTimeMinutes)]})

    # Filter files by input time range. We will use the files which pass the filtering for the time slice.
    filesToMerge = []
    for fileCont in subsystem.files.values():
        #logger.info("fileCont.fileTime: {fileTime}, minTimeCutUnix: {minTimeCutUnix}, maxTimeCutUnix: {maxTimeCutUnix}".format(fileTime = fileCont.fileTime, minTimeCutUnix = minTimeCutUnix, maxTimeCutUnix = maxTimeCutUnix))
        logger.info("fileCont.timeIntoRun (minutes): {timeIntoRun}, minTimeMinutes: {minTimeMinutes}, maxTimeMinutes: {maxTimeMinutes}".format(timeIntoRun = round(fileCont.timeIntoRun / 60), minTimeMinutes = minTimeMinutes, maxTimeMinutes = maxTimeMinutes))
        # It is important to make this check in such a way that we can round to the nearest minute.
        # This is because the exact second when the receiver records the file can vary from file to file.
        if round(fileCont.timeIntoRun / 60) >= minTimeMinutes and round(fileCont.timeIntoRun / 60) <= maxTimeMinutes and fileCont.combinedFile is False:
            # The file is in the time range, so we keep it
            filesToMerge.append(fileCont)

    # If filesToMerge is empty, then the time range has no files. We need to report as such
    if filesToMerge == []:
        return (None, None, {"Request Error": ["No files are available in requested range of {minTimeMinutes}-{maxTimeMinutes}! Please make another request with a different range".format(minTimeMinutes = minTimeMinutes, maxTimeMinutes = maxTimeMinutes)]})

    # Sort files by time
    filesToMerge.sort(key=lambda x: x.fileTime)
    #logger.info("filesToMerge: {filesToMerge}, times: {times}".format(filesToMerge = filesToMerge, times = [x.fileTime for x in filesToMerge]))

    # Get min and max time stamp remaining
    minFilteredTimeStamp = filesToMerge[0].fileTime
    maxFilteredTimeStamp = filesToMerge[-1].fileTime

    # Check if the time slice already exists and return if that is the case
    #logger.info("subsystem.timeSlice: {timeSlices}".format(timeSlices = subsystem.timeSlices))
    for key, timeSlice in iteritems(subsystem.timeSlices):
        #logger.info("minFilteredTimeStamp: {minFilteredTimeStamp}, maxFilteredTimeStamp: {maxFilteredTimeStamp}, timeSlice.minTime: {minTime}, timeSlice.maxTime: {maxTime}".format(minFilteredTimeStamp = minFilteredTimeStamp, maxFilteredTimeStamp = maxFilteredTimeStamp, minTime = timeSlice.minTime, maxTime = timeSlice.maxTime))
        processingOptionsAreTheSame, errors = compareProcessingOptionsDicts(inputProcessingOptions, timeSlice.processingOptions, errors)
        # Handle errors immediately
        if errors != {}:
            return (None, None, errors)
        if timeSlice.minUnixTimeAvailable == minFilteredTimeStamp and timeSlice.maxUnixTimeAvailable == maxFilteredTimeStamp and processingOptionsAreTheSame:
            # Already exists - we don't need to re-merge or reprocess
            return (key, False, None)

    # Hash processing options to ensure that different options with the same times don't overwrite each other!
    optionsHash = hashlib.sha1(str(inputProcessingOptions).encode()).hexdigest()
    # Determine index by ``UUID`` to ensure that there is no clash in the dict keys.
    timeSliceCont = processingClasses.timeSliceContainer(minUnixTimeRequested = minTimeCutUnix,
                                                         maxUnixTimeRequested = maxTimeCutUnix,
                                                         minUnixTimeAvailable = minFilteredTimeStamp,
                                                         maxUnixTimeAvailable = maxFilteredTimeStamp,
                                                         startOfRun = subsystem.startOfRun,
                                                         filesToMerge = filesToMerge,
                                                         optionsHash = optionsHash)
    # Set the processing options in the time slice container
    # We do it by key, value to be certain that they are copied.
    for key, val in iteritems(inputProcessingOptions):
        timeSliceCont.processingOptions[key] = val

    # Store the final result in the time slices dictionary for future reference.
    uuidDictKey = str(uuid.uuid4())
    subsystem.timeSlices[uuidDictKey] = timeSliceCont

    return (uuidDictKey, True, None)

def processTimeSlices(runs, runDir, minTimeRequested, maxTimeRequested, subsystemName, inputProcessingOptions):
    """ Creates a time slice or performs user directed reprocessing.

    Time slices are created by processing a given run using only data in a given time range (and potentially modifying the
    processing options). User directed reprocessing uses the same infrastructure by varying the processing arguments and
    selecting the full time range available for a given run. While the external interface is different, this capabilities
    are performed using the same underlying infrastructure as in the standard processing.

    This function is usually invoked via the web app on a particular run page.

    Note:
        For the format of the errors that are returned, see the :doc:`web app README </webAppReadme>`.

    Args:
        runs (BTree): Dict-like object which stores all run, subsystem, and hist information. Keys are the
            in the ``runDir`` format ("Run123456"), while the values are ``runContainer`` objects.
        runDir (str): String containing the requested run number. For an example run 123456, it
            should be formatted as ``Run123456``.
        minTimeRequested (int): The requested start time of the merge in minutes.
        maxTimeRequested (int): The requested end time of the merge in minutes.
        subsystemName (str): The subsystem of the time slice request by three letter, all capital name (ex. ``EMC``).
        inputProcessingOptions (dict): Processing options requested for the time slice. Keys are the names of
        the options, while values are the actual values of the processing options.
    Returns:
        str or dict: If successful, we return the time slice key (str) under which the requested time slice is stored
            in the ``subsystemContainer.timeSlices`` dictionary. If an error was encountered, we return an error
            dictionary in the proper format.
    """
    logger.info("Processing time slice for {runDir}".format(runDir = runDir))

    # Load run information and subsystem
    if runDir in runs:
        run = runs[runDir]
    else:
        return {"Request Error": ["Requested {runDir}, but there is no run information on it! Please check that it is a valid run and retry in a few minutes!".format(runDir = runDir)]}
    subsystem = run.subsystems[subsystemName]

    # Move any new files into the Overwatch run directory structure and add them into the database.
    # Along this may be a bit slow, we do it here so that the most up to date information is available for
    # the time slice - particularly in the case of an ongoing run.
    runDict = utilities.moveRootFiles(processingParameters["dirPrefix"], processingParameters["subsystemList"])
    processMovedFilesIntoRuns(runs, runDict)

    # Validate and create (or retrieve) the ``timeSliceContainer``.
    (timeSliceKey, newlyCreated, errors) = validateAndCreateNewTimeSlice(run, subsystem, minTimeRequested, maxTimeRequested, inputProcessingOptions)
    # Handle any errors immediately.
    if errors:
        return errors
    # It if already exists, we want to skip the processing and return immediately.
    if not newlyCreated:
        return timeSliceKey
    timeSlice = subsystem.timeSlices[timeSliceKey]

    # Merge the files that are included in the time slice.
    # Return if there were errors in merging
    try:
        mergeFiles.merge(processingParameters["dirPrefix"], run, subsystem,
                         cumulativeMode = processingParameters["cumulativeMode"],
                         timeSlice = timeSlice)
    except ValueError as e:
        # Return the merge error to the user.
        # We want to return a list, so we just return all of the args.
        return {"Merge Error": e.args}

    # Print time slice request variables for log
    logger.debug("Time slice request values:")
    logger.debug("subsystem.subsystem: {subsystem}, subsystem.fileLocationSubsystem: {fileLocationSubsystem}, minTimeRequested: {minTimeRequested}, maxTimeRequested: {maxTimeRequested}".format(subsystem = subsystem.subsystem, fileLocationSubsystem = subsystem.fileLocationSubsystem, minTimeRequested = minTimeRequested, maxTimeRequested = maxTimeRequested))

    # Generate the histograms
    outputFormattingSave = os.path.join("{base}", "%(prefix)s.{name}.{ext}" % {"prefix": timeSlice.filenamePrefix})
    logger.debug("outputFormattingSave: {}".format(outputFormattingSave))
    logger.debug("path: {}".format(os.path.join(processingParameters["dirPrefix"],
                                                subsystem.baseDir,
                                                timeSlice.filename.filename)))
    logger.debug("timeSlice.processingOptions: {}".format(timeSlice.processingOptions))
    processRootFile(os.path.join(processingParameters["dirPrefix"],
                                 subsystem.baseDir,
                                 timeSlice.filename.filename),
                    outputFormattingSave, subsystem,
                    processingOptions = timeSlice.processingOptions)

    logger.info("Finished processing {prettyName}!".format(prettyName = run.prettyName))

    # No errors, so return the key
    return timeSliceKey

def createNewSubsystemFromMovedFilesInformation(runs, subsystem, runDict, runDir):
    """ Creates a new subsystem based on the information from the moved files.

    This function determines the ``fileLocationSubsystem`` and then creates a new subsystem based on the
    given information, including adding the files to the subsystem. It also ensures that the subsystem
    will be processed by enabling the ``newFile`` flag in the subsystem.

    Note:
        In the case of a subsystem which doesn't have it's own files in a run where the ``HLT`` is not available
        (for example, and ``EMC`` standalone run), the ``ValueError`` exception will be raised. If the run has
        just been created, this is just fine - the subsystem just won't be created (as it shouldn't be). In this
        case, it's advisable to catch and log exception and continue with standard execution. However, in other
        cases (such as adding a file later in the run), this shouldn't be possible, so we want the exception to
        be raised and it needs to be handled carefully (in such a case, it likely indicates that something is broken).

    Args:
        runs (BTree): Dict-like object which stores all run, subsystem, and hist information. Keys are the
            in the ``runDir`` format ("Run123456"), while the values are ``runContainer`` objects.
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).  Default: ``None``.
        runDict (dict): Nested dict which contains the new filenames and the HLT mode. For the precise
            structure, ``base.utilities.moveFiles()``.
        runDir (str): String containing the requested run number. For an example run 123456, it
            should be formatted as ``Run123456``.
    Returns:
        None. However, the run container is modified to store the newly created subsystem.

    Raises:
        ValueError: If the subsystem requests doesn't have it's own receiver files and files from the HLT receiver
            are also not available.
    """
    if subsystem in runDict[runDir]:
        fileLocationSubsystem = subsystem
    else:
        # First check is applicable for an entirely new run, while the second is for handling an
        # existing subsystem which where the `runDict` doesn't have any HLT files, but there may
        # already by some which exist. In particular, this may be possible if the data sync the HLT
        # receiver hasn't written it's first file yet. This shouldn't be terribly likely, but it
        # certainly is possible.
        if "HLT" in runDict[runDir] or "HLT" in runs[runDir].subsystems:
            fileLocationSubsystem = "HLT"
        else:
            # Cannot create subsystem, since the HLT doesn't exist as a fall back
            # This isn't fatal, since it can happen to many subsystems if the HLT doesn't exist.
            # However, it needs to be caught explicitly. And in cases where it isn't acceptable,
            # don't catch the exception.
            raise ValueError("Could not create subsystem {subsystem} in {runDir} due to lacking {subsystem} and HLT files.".format(subsystem = subsystem, runDir = runDir))

    # Sort the filenames by time stamp for easy access (they are stored in an ordered dict).
    filenames = sorted(runDict[runDir][fileLocationSubsystem])
    startOfRun = utilities.extractTimeStampFromFilename(filenames[0])
    endOfRun = utilities.extractTimeStampFromFilename(filenames[-1])
    logger.info("For subsystem {subsystem}, end of run filename: {filename}".format(subsystem = subsystem, filename = filenames[-1]))

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

    # Store the file(s) information
    # `subsystemFiles` is a reference, so it will be updated when we add the files to the dictionary.
    subsystemFiles = runs[runDir].subsystems[subsystem].files
    for filename in filenames:
        filename = os.path.join(runs[runDir].subsystems[subsystem].baseDir, filename)
        subsystemFiles[utilities.extractTimeStampFromFilename(filename)] = processingClasses.fileContainer(filename, startOfRun)

    # Flag that there are new files
    runs[runDir].subsystems[subsystem].newFile = True

def processMovedFilesIntoRuns(runs, runDict):
    """ Convert the list of moved files into run and subsystem containers stored in the database.

    In the case that the run has not been created, a new run container is created and an attempt is made
    to create all subsystems that were requested in the configuration. If the subsystem already exists,
    the moved files are added to the existing objects. It also includes the capability to add new subsystems
    part of the way through a run in the unlikely event that we pick up new data during the run.

    Args:
        runs (BTree): Dict-like object which stores all run, subsystem, and hist information. Keys are the
            in the ``runDir`` format ("Run123456"), while the values are ``runContainer`` objects.
        runDict (dict): Nested dict which contains the new filenames and the HLT mode. For the precise
            structure, ``base.utilities.moveFiles()``.
    Returns:
        None. Subsystems are created inside of the ``runContainer`` objects for which there are entries in the
            ``runDict``.
    """
    # Copy the dict to avoid modifying the passed copy.
    # Although it is not used after this function as of Oct 2018, since we modify the dict by adding entries for subsystems
    # which are not their own ``fileLocationSubsystem``, as well as popping the ``hltMode``, it is safer to copy it and
    # be certain that there are no adverse impacts.
    runDict = copy.deepcopy(runDict)
    for runDir in runDict:
        # Remove the HLT mode so it doesn't get interpreted as a subsystem.
        hltMode = runDict[runDir].pop("hltMode")

        # It was replay data, so we don't want to process it. Skip it (which will ensure that we don't create)
        # it's corresponding subsystem) and continue.
        if hltMode == "E":
            continue

        # Update existing runs and subsystems or create new ones if necessary
        if runDir in runs:
            run = runs[runDir]

            # Possible scenarios that have to be handled below:
            # - 1) runDir has new data, and the corresponding subsystem exists. -> Update the subsystem.
            # - 1a) We received new data for a subsystem which previously didn't have it's own data, but now it does. -> Notify as having it's own files
            #       and replace the existing ones with the existing data.
            # - 2) runDir has new data, but subsystem doesn't exist in run container -> Create a new subsystem.
            # - 3) runDir has new data, and it is used in a subsystem which doesn't have it's own data -> Update the subsystem with HLT files (but it will be indirect)
            # - 4) runDir doesn't have new data, but the subsystem exists -> Do nothing.

            # Handle scenario 3
            # To handle this scenario, we basically want to copy the HLT (or other fileLocationSubsystem) files to the existing subsystem.
            # When we are done, the run subsystems should be a subset of the runDict subsystems. The runDict subsystems could have additional subsystems
            # if began receiving new data.
            for name, subsystem in iteritems(run.subsystems):
                if name not in runDict[runDir]:
                    newFiles = []
                    if subsystem.fileLocationSubsystem != subsystem.subsystem:
                        # This will almost always be "HLT", but in principle it could be something else!
                        newFiles = runDict[runDir].get(subsystem.fileLocationSubsystem, [])
                    runDict[runDir][name] = newFiles

            # Sanity check to make sure that we've in the desired state to proceed.
            assert set(runDict[runDir]).issuperset(run.subsystems)

            # Update each subsystem and note that it needs to be reprocessed
            for subsystemName in runDict[runDir]:
                # We only want to update files if there are actually new files (and not just an empty list)
                if runDict[runDir][subsystemName]:
                    if subsystemName in run.subsystems:
                        # Scenario 1
                        # Update the subsystem
                        logger.debug("Updating files in existing subsystem {subsystemName}.".format(subsystemName = subsystemName))
                        # Update the existing subsystem
                        subsystem = run.subsystems[subsystemName]
                        # First handle scenario 1A
                        if subsystem.subsystem != subsystem.fileLocationSubsystem:
                            # Use whether the ``fileLocationSubsystem`` name is in the first file as a proxy of whether we
                            # have started receiving data for that subsystem.
                            if subsystem.fileLocationSubsystem not in runDict[runDir][subsystemName][0]:
                                logger.info("Received data for subsystem {subsystem}. Switching the subsystem to having it's own data source, so: fileLocationSubsystem {fileLocationSubsystem} -> {subsystem}.".format(fileLocationSubsystem = subsystem.fileLocationSubsystem, subsystem = subsystem.subsystem))

                                # This should happen fairly early on. If it happens later, we provide a warning.
                                # We define fairly early as having four files.
                                if len(subsystem.files) > 4:
                                    logger.warning("Conversion of subsystem {subsystem} to having it's own data source is occurring later than expected! It already has {nFiles}. Continuing with conversion, but it is worth checking!".format(subsystem = subsystem.subsystem, nFiles = len(subsystem.files)))

                                # Convert by changing the fileLocationSubsystem to the subsystem name and clearing
                                # out the existing files. The new ones will be added in below.
                                subsystem.fileLocationSubsystem = subsystem.subsystem
                                # Also need to update the directories
                                subsystem.setupDirectories(runDir = runDir)
                                logger.debug("Existing files: {filenames}".format(filenames = [f.filename for f in itervalues(subsystem.files)]))
                                subsystem.files.clear()

                        # Add the new files and note them in the subsystem, which will lead to reprocessing.
                        subsystem.newFile = True
                        for filename in runDict[runDir][subsystemName]:
                            # We need the full path to the file (ie everything except for the dirPrefix).
                            filename = os.path.join(subsystem.baseDir, filename)
                            subsystem.files[utilities.extractTimeStampFromFilename(filename)] = processingClasses.fileContainer(filename = filename, startOfRun = subsystem.startOfRun)

                        # Update time stamps
                        fileKeys = subsystem.files.keys()
                        # The start of run time should rarely change, but in principle we could get a new file that we
                        # missed. It also could happen if we change to a subsystem which contains it's own data source.
                        subsystem.startOfRun = fileKeys[0]
                        logger.debug("Previous EOR: {endOfRun}\tNew: {fileKey}".format(endOfRun = subsystem.endOfRun, fileKey = fileKeys[-1]))
                        subsystem.endOfRun = fileKeys[-1]
                    else:
                        # Scenario 2
                        # Create a new subsystem in an existing run.
                        # This may occur if a new run has started, but we haven't yet received data from each subsystem.
                        logger.debug("Creating new subsystem {subsystemName} in existing run.".format(subsystemName = subsystemName))
                        # NOTE: We don't catch the exception here, as we want it to fail if the subsystem doesn't have its own
                        #       files and the HLT receiver data isn't available.
                        createNewSubsystemFromMovedFilesInformation(runs, subsystemName, runDict, runDir)
                else:
                    # Scenario 4
                    # We end up here if there is now new data for subsystemName.
                    # In that case, we have nothing to do and we just continue.
                    logger.debug("No new data for subsystem {subsystemName}, so not updating this subsystem in the run".format(subsystemName = subsystemName))
        else:
            # The run doesn't yet exist, so we'll create a new run and new subsystems.
            # First, create the new run.
            logger.debug("Creating new run and set of subsystems for {runDir}".format(runDir = runDir))
            runs[runDir] = processingClasses.runContainer(runDir = runDir,
                                                          fileMode = processingParameters["cumulativeMode"],
                                                          hltMode = hltMode)
            # Add files and subsystems based on the moved file information. We want to consider all
            # possible subsystems here. Anything for which we don't have available data will either
            # not be shown (if there is not HLT receiver data) or will take advantage of relevant data
            # from the HLT receiver.
            for subsystem in processingParameters["subsystemList"]:
                try:
                    createNewSubsystemFromMovedFilesInformation(runs, subsystem, runDict, runDir)
                except ValueError as e:
                    # This means that the subsystem could not be created.  This is okay - we just want
                    # to log it and continue on. For more information on the conditions that can lead
                    # to such a case, see ``createNewSubsystemFromMovedFilesInformation(...)``.
                    logger.warning(e.args[0])

def processAllRuns():
    """ Driver function for processing all available data, storing the results in a database and on disk.

    This function is responsible for driving all processing functionality in Overwatch. This spans from
    initial preprocessing of the received ROOT files to trending information extracted from histograms.
    In particular, it directs:

    - Retrieve the run information or recreate it if it doesn't exist. If recreated, it will be populated
      with existing information already stored in the data directory.
    - Retrieve the trending object or recreate it if it doesn't exist. As of August 2018, the trending
      objects will be empty when recreated.
    - Move new files into the Overwatch file structure and create runs and/or subsystems from those new files.
      If the corresponding objects already exist, then they are updated.
    - Perform the actual processing, which includes executing the subsystem (detector) plug-in functionality.
      The processing will only be performed if necessary (ie if there are new files which need processing).
      This can also be overridden by specifically requesting reprocessing.
    - Perform the trending. It also has subsystem (detector) plug-in functionality.
    - Transferring the processed data if requested.

    For further information on the technical details of how all of this is accomplished, see the
    :doc:`processing README </processingReadme>`, as well as the package documentation. For further information
    on the subsystem (detector) plug-in functionality, see
    the :doc:`detector subsystem and trending README </detectorPluginsReadme>`.

    Note:
        Configuration for this processing is provided by the Overwatch configuration system. For further
        information, see the :doc:`Overwatch base module README </baseReadme>`.

    Args:
        None: See the note above.
    Returns:
        None. However, it has extensive side effects. It changes values in the database related to runs,
            subsystems, etc, as well as writing image and ``json`` files to disk.
    """
    # Get the database.
    (dbRoot, connection) = utilities.getDB(processingParameters["databaseLocation"])

    # Setup the runs dict by either retrieving it or recreating it.
    if "runs" in dbRoot:
        # The objects already exist, so we use the existing information.
        logger.info("Utilizing existing database!")
        runs = dbRoot["runs"]

        # During the previous processing run, new files were marked as new in the subsystem.
        # At the end of the previous processing run, this flag wasn't clear so we can know
        # which files were just processed. Since we are now starting a new processing run,
        # we now must be clear this flag so we don't reprocess those runs again.
        for run in itervalues(runs):
            for subsystem in itervalues(run.subsystems):
                if subsystem.newFile:
                    subsystem.newFile = False
    else:
        # Create the runs tree to store the information
        dbRoot["runs"] = BTrees.OOBTree.BTree()
        runs = dbRoot["runs"]

        # The objects don't exist, so we need to create them.
        # This will be a slow process, so the results should be stored.
        for runDir in utilities.findCurrentRunDirs(processingParameters["dirPrefix"]):
            # Create run objects.
            runs[runDir] = processingClasses.runContainer(runDir = runDir,
                                                          fileMode = processingParameters["cumulativeMode"])

        # Find files and create subsystems based on the existing files.
        for runDir, run in iteritems(runs):
            for subsystem in processingParameters["subsystemList"]:
                # For each subsystem, determine where the files are stored.
                # NOTE: There are some similarities in this section to ``createNewSubsystemFromMovedFilesInformation()``,
                #       but there are enough differences small that the amount of code we can actual combine is rather small,
                #       such that it's not really worth the effort.
                subsystemPath = os.path.join(processingParameters["dirPrefix"], runDir, subsystem)
                if os.path.exists(subsystemPath):
                    fileLocationSubsystem = subsystem
                else:
                    # In this case, the subsystem actual files will be provided by the "HLT", if the subsystem
                    # is supposed to exist at all for this particular run.
                    if os.path.exists(os.path.join(processingParameters["dirPrefix"], runDir, "HLT")):
                        fileLocationSubsystem = "HLT"
                        # Define subsystem path properly for this data arrangement.
                        subsystemPath = subsystemPath.replace(subsystem, "HLT")
                    else:
                        # Cannot create subsystem, since the HLT doesn't exist as a fall back.
                        if subsystem == "HLT":
                            logger.warning("Could not create subsystem {subsystem} in {runDir} due to lacking HLT files.".format(subsystem = subsystem, runDir = runDir))
                        else:
                            logger.warning("Could not create subsystem {subsystem} in {runDir} due to lacking {subsystem} and HLT files.".format(subsystem = subsystem, runDir = runDir))
                        continue

                logger.info("Creating subsystem {subsystem} in {runDir}".format(subsystem = subsystem, runDir = runDir))
                # Retrieve the files for a given subsystem directory.
                [filenamesDict, _] = utilities.createFileDictionary(processingParameters["dirPrefix"], runDir, fileLocationSubsystem)
                # We want them to be ordered by time stamp.
                sortedKeys = sorted(filenamesDict.keys())
                # Extract information necessary for creating the subsystem.
                startOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[0]])
                endOfRun = utilities.extractTimeStampFromFilename(filenamesDict[sortedKeys[-1]])
                logger.info("startOfRun: {startOfRun}, endOfRun: {endOfRun}, runLength: {runLength}".format(startOfRun = startOfRun, endOfRun = endOfRun, runLength = (endOfRun - startOfRun) // 60))

                # Now create the actual subsystem.
                showRootFiles = False
                if subsystem in processingParameters["subsystemsWithRootFilesToShow"]:
                    showRootFiles = True
                run.subsystems[subsystem] = processingClasses.subsystemContainer(subsystem = subsystem,
                                                                                 runDir = run.runDir,
                                                                                 startOfRun = startOfRun,
                                                                                 endOfRun = endOfRun,
                                                                                 showRootFiles = showRootFiles,
                                                                                 fileLocationSubsystem = fileLocationSubsystem)

                # Store the file(s) information.
                # `subsystemFiles` is a reference, so it will be updated when we add the files to the dictionary.
                subsystemFiles = run.subsystems[subsystem].files
                for key in filenamesDict:
                    subsystemFiles[key] = processingClasses.fileContainer(filenamesDict[key], startOfRun)
                logger.debug("Files length: {subsystemFilesLength}".format(subsystemFilesLength = len(subsystemFiles)))

                # Add the combined file to the subsystem if it already exists. If it doesn't it will be created
                # in `mergeFiles.mergeRootFiles()`
                combinedFilename = [filename for filename in os.listdir(subsystemPath) if "combined" in filename and ".root" in filename]
                if len(combinedFilename) > 1:
                    raise ValueError("Number of combined files found in {runDir} for subsystem {subsystem} is {combinedFilenameLength}, but should be 1!".format(runDir = runDir, subsystem = subsystem, combinedFilenameLength = len(combinedFilename)))
                if len(combinedFilename) == 1:
                    run.subsystems[subsystem].combinedFile = processingClasses.fileContainer(os.path.join(runDir, fileLocationSubsystem, combinedFilename[0]), startOfRun)
                else:
                    logger.info("No combined file in {runDir}".format(runDir = runDir))

        # Commit any changes made to the database so we can proceed onto the actual processing.
        transaction.commit()

    # See how we've done so far.
    # This is quite verbose, so we don't want it to be normally enabled.
    #logger.info("runs: {runs}".format(runs = list(runs.keys())))

    # Create the configuration stored in the database if necessary
    # This doesn't exhaustively contain all of the settings, but stores some properties are useful.
    if "config" not in dbRoot:
        dbRoot["config"] = persistent.mapping.PersistentMapping()

    # Set up the trending.
    if processingParameters["trending"]:
        trendingManager = TrendingManager(dbRoot, processingParameters)
        trendingManager.createTrendingObjects()
        transaction.commit()
    else:
        trendingManager = None

    # From here, we start the actual data processing

    # First, we move files that we have received from the receivers into the Overwatch run structure and
    # add them to the database.
    runDict = utilities.moveRootFiles(processingParameters["dirPrefix"], processingParameters["subsystemList"])
    logger.info("Files moved: {runDict}".format(runDict = runDict))
    processMovedFilesIntoRuns(runs, runDict)

    # Potentially helpful debug information
    if processingParameters["debug"]:
        logger.debug("Moved files information:")
        for runDir in runs.keys():
            for subsystem in runs[runDir].subsystems.keys():
                logger.debug("{runDir}, {subsystem} has nFiles: {nFiles}".format(runDir = runDir, subsystem = subsystem, nFiles = len(runs[runDir].subsystems[subsystem].files)))

    # Determine the most recent histograms by merging the relevant files (as determined by the mode
    # in which Overwatch is operating. See more on this in the `mergeFiles` module).
    # Regardless of the mode, this will result in a single "combined" file which contains all of the
    # most up to date files.
    # NOTE: We will only subsystems which contain new files.
    mergeFiles.mergeRootFiles(runs, processingParameters["dirPrefix"],
                              processingParameters["forceNewMerge"],
                              processingParameters["cumulativeMode"])

    # Perform the actual histogram processing
    outputFormattingSave = os.path.join("{base}", "{name}.{ext}")
    for runDir, run in iteritems(runs):
        for subsystem in run.subsystems.values():
            # Process the subsystem if there is a new file or we explicitly ask for
            # processing by forcing it.
            # We can force either generally (`forceReprocess`), or for particular runs (`forceReprocessRuns`)
            if subsystem.newFile or processingParameters["forceReprocessing"] or int(runDir.replace("Run", "")) in processingParameters["forceReprocessRuns"]:
                # Process combined root file: plot histograms and save the results of the processing
                # in both image and `json` on the disk.
                logger.info("About to process {prettyName}, {subsystem}".format(prettyName = run.prettyName, subsystem = subsystem.subsystem))
                processRootFile(
                    filename = os.path.join(processingParameters["dirPrefix"], subsystem.combinedFile.filename),
                    outputFormatting = outputFormattingSave,
                    subsystem = subsystem,
                    forceRecreateSubsystem = processingParameters["forceRecreateSubsystem"],
                    trendingManager = trendingManager,
                )
                # TODO need additional info
                # As of August 2018, this is where the trending container should step in to
                # update the trending objects if they are not entirely up to date (say, if they're
                # missing entries because the trending objects were recreated).
                # TODO: Loop over process root file with various until it is up to date
                pass
            else:
                # We often want to skip processing since most runs won't have new files and will not need to be processed most times.
                logger.debug("Don't need to process {prettyName}. It has already been processed".format(prettyName = run.prettyName))

        # Commit after we have successfully processed each run
        transaction.commit()

    logger.info("Finished standard processing!")

    # Run trending now that we have gotten to the most recent run
    if trendingManager:
        trendingManager.processTrending()
        # Commit after we have successfully processed the trending
        transaction.commit()
        logger.info("Finished trending processing!")

    # Update receiver last modified time if the log exists
    # This allows to keep track of when we last processed a new file.
    # However, it requires that the receiver log file is available on the same machine as where the processing
    # is performed.
    receiverLogFileDir = os.path.join("deploy")
    if os.path.exists(receiverLogFileDir):
        receiverLogFilePath = os.path.join(receiverLogFileDir,
                                           next((name for name in os.listdir(receiverLogFileDir) if "Receiver.log" in name), ""))
        logger.debug("receiverLogFilePath: {receiverLogFilePath}".format(receiverLogFilePath = receiverLogFilePath))

        # Add the receiver last modified time
        if receiverLogFilePath and os.path.exists(receiverLogFilePath):
            logger.debug("Updating receiver log last modified time!")
            receiverLogLastModified = os.path.getmtime(receiverLogFilePath)
            dbRoot["config"]["receiverLogLastModified"] = receiverLogLastModified

    # Add users and secret key if debugging
    # This needs to be done manually if deploying, since this requires some care to ensure that everything is
    # configured properly. However, it's quite convenient for development.
    if processingParameters["debug"]:
        utilities.updateDBSensitiveParameters(dbRoot)

    # Ensure that any additional changes are committed and finish up with the database.
    transaction.commit()
    connection.close()

