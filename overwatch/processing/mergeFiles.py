#!/usr/bin/env python

""" This module contains functions used to merge histograms and ROOT files.

For further information on functionality and options, see the function docstrings.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# Python 2/3 support
from __future__ import print_function
from __future__ import absolute_import
from future.utils import iteritems

# ROOT
import ROOT

# General
import os
import shutil
import logging
# Setup logger
logger = logging.getLogger(__name__)

from . import processingClasses

def merge(currentDir, run, subsystem, cumulativeMode = True, timeSlice = None):
    """ For a given run and subsystem, handles merging of files into a "combined file" which
    is suitable for processing.

    For a standard subsystem, the "combined file" is the file which stores the most recent data
    for a particular run and subsystem. The merge is only performed if we have received new files
    in the specified run. The details of the merge are determined by the ``cumuluativeMode`` setting.
    This setting, which is determined by the options sent in the data request sent to the HLT by
    the ZMQ receiver, denotes whether the data that we received are reset each time the data is sent.
    If the data is being reset, then the files are not cumulative, and therefore ``cumulativeMode`` should be
    set to ``False``. Note that although this function supports both modes, we tend to operate
    in cumulative mode because resetting the objects would interfere with other subscribes to the HLT
    data. For example, if both Overwatch and another subscriber were set to request data with resets
    every minute and were offset by 30 seconds, they would both only receive approximately half the
    data! Thus, it's preferred to operate in cumulative mode.

    For cumulative mode, the combined objects are created in two different ways: 1) For a standard
    combined file, by simply copying the most recent file (because it contains data covering the entire
    run); 2) For time slices, by subtracting the objects in two corresponding ROOT files. For reset
    mode, ``TFileMerger`` is used to merge all files within the available timestamps together.

    This function also handles merging files for time slices. The relevant parameters should be specified
    in a ``timeSliceContainer``. The min and max requested times are extracted, and this function only
    merges files within the fixed time range corresponding to those values. The output format of this
    file is identical to any other combined file.

    Note:
        As side effects of this function, if it executes successfully for a combined file, the combined
        filename will be updated in ``subsystemContainer``.

    Args:
        dirPrefix (str): Path to the root directory where the data is stored.
        runDir (str): Run directory of current run. Of the form ``Run######``.
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        cumulativeMode (bool): Specifies whether the histograms we receive are cumulative or if they
            have been reset between each acquired ROOT file, i.e. whether we merge in "subscribe mode" or
            "request/reset mode". Default: True.
        timeSlice (processingClasses.timeSliceContainer): Stores the properties of the requested time slice. If not specified,
            it will be ignored and it will create a standard "combined file". Default: None
    Returns:
        None: On success, ``None`` is returned. Otherwise, an exception is raise.

    Raises:
        ValueError: If the number of input files doesn't match the number of files in the merger. Perhaps if a
            file is inaccessible.
    """
    # Determines which files are needed to merge
    if timeSlice:
        filesToMerge = timeSlice.filesToMerge
    else:
        filesToMerge = []
        for fileCont in subsystem.files.values():
            # This is not necessary since combined files are not stored in files anymore
            #if fileCont.combinedFile == False:
            filesToMerge.append(fileCont)

    # Sort files by time
    filesToMerge.sort(key=lambda x: x.fileTime)

    # If in cumulativeMode, we subtract the earliest file from the latest file, unless
    # the beginning of the time slice is the start of the run. In that case, case we don't
    # subtract anything from the most recent
    # (if >0, we should subtract the first file; if =0, we should include everything)
    if cumulativeMode and timeSlice and timeSlice.minUnixTimeAvailable != subsystem.startOfRun:
        earliestFile = filesToMerge[0].filename
        latestFile = filesToMerge[-1].filename
        # Subtract latestFile from earliestFile
        timeSlicesFilename = os.path.join(currentDir, subsystem.baseDir, timeSlice.filename.filename)
        subtractFiles(os.path.join(currentDir, earliestFile),
                      os.path.join(currentDir, latestFile),
                      timeSlicesFilename)
        logger.info("Completed time slicing via subtraction with result stored in {}!\nMerging complete!".format(timeSlicesFilename))
        return None

    if cumulativeMode:
        # Take the most recent file
        filesToMerge = [filesToMerge[-1]]

    # Merging using root. We use this for multiple files, but will skip it
    # if we are only copying one file.
    merger = ROOT.TFileMerger()

    # Determine the files to merge
    if len(filesToMerge) == 1:
        # This is often cumulative mode, but could also be reset mode with only 1 file
        numberOfFiles = len(filesToMerge)
    else:
        # If more than one file (almost assuredly reset mode), merge everything
        for fileCont in filesToMerge:
            logger.info("Added file {} to merger".format(fileCont.filename))
            merger.AddFile(fileCont.filename)

        numberOfFiles = merger.GetMergeList().GetEntries()
        if numberOfFiles != len(filesToMerge):
            errorMessage = "Problems encountered when adding files to merger! Number of input files ({}) do not match number in merger ({})!".format(len(filesToMerge), numberOfFiles)
            logger.error(errorMessage)
            raise ValueError(errorMessage)

    if timeSlice:
        filePath = os.path.join(subsystem.baseDir, timeSlice.filename.filename)
    else:
        # Define convenient variable
        maxFilteredTimeStamp = filesToMerge[-1].fileTime
        filePath = os.path.join(subsystem.baseDir, "hists.combined.{}.{}.root".format(numberOfFiles, maxFilteredTimeStamp))
    outFile = os.path.join(currentDir, filePath)
    logger.info("Number of files to be merged: {}".format(numberOfFiles))
    logger.info("Output file: {}".format(outFile))

    # Set the output and perform the actual merge
    if numberOfFiles == 1:
        # Avoid errors with TFileMerger and only one file.
        # Plus, performance should be better
        shutil.copy(os.path.join(currentDir, filesToMerge[0].filename), outFile)
    else:
        merger.OutputFile(outFile)
        merger.Merge()
    logger.info("Merging complete!")

    # Add combined file to the subsystem
    if not timeSlice:
        subsystem.combinedFile = processingClasses.fileContainer(filePath, startOfRun = subsystem.startOfRun)
    return None

def subtractFiles(minFile, maxFile, outfile):
    """ Subtract histograms in one file from matching histograms in another.

    This function is used for creating time slices in cumulative mode. Since each file is cumulative,
    the later time stamped file needs to be subtracted from the earlier time stamped file. The
    remaining data corresponds to the data stored during the time window ``early-late``.

    This function is **not** used for creating a standard combined file because the cumulative information
    is already stored in the most recent file.

    Note:
        The names of the histograms in each file must match exactly for them to be subtracted.

    Note:
        The output file is opened with "RECREATE", so it will always overwrite an existing
        file with the given filename!

    Args:
        minFile (str): Filename of the ROOT file containing data to be subtracted.
        maxFile (str): Filename of the ROOT file containing data to to subtracted from.
        outfile (str): Filename of the output file which will contain the subtracted histograms.
    Returns:
        None.
    """

    fMin = ROOT.TFile(minFile, "READ")
    fMax = ROOT.TFile(maxFile, "READ")
    fOut = ROOT.TFile(outfile, "RECREATE")

    # Read in available keys in the file
    keysMinFile = fMin.GetListOfKeys()
    keysMaxFile = fMax.GetListOfKeys()

    # Loop through both files, and subtract matching pairs of hists
    for keyMin in keysMinFile:
        # Ensure that we only take histograms (we would expect such, but better to check for safety)
        classOfObject = ROOT.gROOT.GetClass(keyMin.GetClassName())
        if not classOfObject.InheritsFrom(ROOT.TH1.Class()):
            continue

        minHistName = keyMin.GetName()

        for keyMax in keysMaxFile:
            # Ensure that we only take histograms
            classOfObject = ROOT.gROOT.GetClass(keyMin.GetClassName())
            if not classOfObject.InheritsFrom(ROOT.TH1.Class()):
                continue

            maxHistName = keyMax.GetName()
            if minHistName == maxHistName:
                minHist = keyMin.ReadObj()
                maxHist = keyMax.ReadObj()

                # Subtract the earlier hist from the later hist
                maxHist.Add(minHist, -1)
                fOut.cd()
                maxHist.Write()

    fMin.Close()
    fMax.Close()
    fOut.Close()

def mergeRootFiles(runs, dirPrefix, forceNewMerge = False, cumulativeMode = True):
    """ Driver function for creating combined files for each subsystem within a given set of runs.

    For a given list of runs, this function will iterate over all available subsystems, merging or
    moving files as appropriate. To speed up this function, operations will only be performed if
    a new file is available for a particular subsystem (ie. ``subsystemContainer.newFile == True``).
    This function will result in a combined file per subsystem per run. For further information on
    the format of this file, see ``merge()``.

    Args:
        runs (dict): Dict of ``runContainers`` to perform the merge over. The keys are the runDirs,
            in the from of ``Run######``.
        dirPrefix (str): Path to the root directory where the data is stored.
        forceNewMerge (bool): Flag to force merging for all runs, regardless of whether it is supposed
            to be merged.  Default: False.
        cumulativeMode (bool): Specifies whether the histograms we receive are cumulative or if they
            have been reset between each acquired ROOT file, i.e. whether we merge in "subscribe mode" or
            "request/reset mode". See ``merge()`` for further information on this mode. Default: True.
    Returns:
        None
    """
    currentDir = dirPrefix

    # Process runs
    for runDir, run in iteritems(runs):
        for subsystem in run.subsystems:
            # Only merge if we there are new files to merge
            if run.subsystems[subsystem].newFile is True or forceNewMerge:
                # Skip if the subsystem does not have it's own files
                if run.subsystems[subsystem].subsystem != run.subsystems[subsystem].fileLocationSubsystem:
                    continue

                # Perform the merge
                # Check for a combined file. The file has a name of the form hists.combined.(number of uncombined
                #  files in directory).(timestamp of combined file).root
                combinedFile = run.subsystems[subsystem].combinedFile
                # If it doesn't exist then we go directly to merging; otherwise we remove the old one and then merge
                # Previously, we handled the two modes as:
                #   In SUB mode, compare combined file timestamp with latest timestamp of uncombined file
                #   In REQ mode, compare combined file merge count with number of uncombined files

                logger.info("Need to merge {}, {} again".format(runDir, subsystem))
                if combinedFile:
                    logger.info("Removing previous merged file {}".format(combinedFile.filename))
                    os.remove(os.path.join(currentDir, combinedFile.filename))
                    # Remove from the file list
                    run.subsystems[subsystem].combinedFile = None

                # Perform the actual merge
                merge(currentDir, run, run.subsystems[subsystem], cumulativeMode)

                # We have successfully merged
                # Still considered a newFile until we have processed, so don't change state here
                #run.subsystems[subsystem].newFile = False

