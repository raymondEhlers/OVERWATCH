"""
This module contains functions used to merge histograms, including the principal merge function. 

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

# Python 2/3 support
from __future__ import print_function
from __future__ import absolute_import

# ROOT
from ROOT import gROOT, TH1, TFile, TFileMerger

# General
import os
import shutil

from . import processingClasses
from . import utilities

###################################################
def merge(currentDir, run, subsystem, cumulativeMode = True, minTimeMinutes = -1, maxTimeMinutes = -1):
    """ Merge function: for a given run and subsystem, merges files appropriately into a combined file.  

    Merge is only performed if we have received new files in the specificed run.
    Merges according to "cumulativeMode": See below.
    If minTimeMinutes and maxTimeMinutes are specified, merges only a fixed time range. Otherwise, merges all acquired ROOT files.

    Args:
        currentDir (str): Directory prefix necessary to get to all of the folders. 
        runDir (str): Run directory of current run. 
        subsystem (str): The current subsystem by three letter, all capital name (ex. ``EMC``).
        cumulativeMode (Optional[bool]): Specifies whether the histograms we receive are cumulative or if they 
            have been reset between each acquired ROOT file, i.e. whether we merge in "subscribe mode" or 
            "request/reset mode". Default: True.
        minTimeMinutes (Optional[int]): Min time to merge from, in minutes, starting from 0. Default: -1. Return
            0 if time range unacceptable. 
        maxTimeMinutes (Optional[int]): Max time range to merge to, in minutes. Default: -1. If max filter time 
            is greater than max file time, merge up to and including last file. Return 0 if time range unacceptable.
    
    Returns:
        tuple: Tuple containing:

            actualFilterTimeMin (int): length of time (in minutes) spanned by merged file

            outfile (str): location of merged file 

    """

    # Define convenient variable
    filenamePrefix = os.path.join(currentDir, run.runDir, subsystem)

    # Merging using root
    merger = TFileMerger()

    # Convert filter time to seconds, so it can be added to unix time
    minTimeSec = minTimeMinutes*60
    maxTimeSec = maxTimeMinutes*60

    # Store unmerged filenames and their unix timestamps in dictionary
    #[mergeDict, actualMaxTimeMinutes] = utilities.createFileDictionary(currentDir, runDir, subsystem)
    #keys = sorted(mergeDict.keys())

    # Get min and max possible time ranges
    minFileTime = run.subsystems[subsystem].startOfRun
    maxFileTime = run.subsystems[subsystem].endOfRun

    # User filter time, in unix time
    minTimeCutUnix = minTimeSec + minFileTime 
    maxTimeCutUnix = maxTimeSec + minFileTime

    # If max filter time is greater than max file time, merge up to and including last file
    if maxTimeCutUnix > maxFileTime:
        maxTimeCutUnix = maxFileTime
        print("ERROR: Input max time exceeds data! It has been reset to the maximum allowed.")

    # If input time range out of range, return 0
    isTimeSlice = minTimeMinutes != -1 and maxTimeMinutes != -1
    if isTimeSlice:
        print("Filtering time window! Min: " + int(minTimeMinutes) + ", Max: " + int(maxTimeMinutes)) 
        timeSliceDir = os.path.join(currentDir, run.runDir, subsystem, "timeSlices")
        if not os.path.exists(timeSliceDir):
            os.makedirs(timeSliceDir)
        if minTimeMinutes < 0:
            print("Input time range exceeds time range of data!")
            return 0
        if minTimeCutUnix > maxTimeCutUnix:
            print("Max time must be greater than Min time!")
            return 0

    # Filter mergeDict by input time range
    filesToMerge = []
    for fileCont in run.subsystems[subsystem].files.values():
        if isTimeSlice:
            if fileCont.fileTime >= minTimeCutUnix and fileCont.fileTime <= maxTimeCutUnix and fileCont.combinedFile == False:
                # The file is in the time range, so we keep it
                filesToMerge.append(fileCont)
        else:
            if fileCont.combinedFile == False:
                filesToMerge.append(fileCont)

    # Sort files by time
    filesToMerge.sort(key=lambda x: x.fileTime)

    # Get min and max time stamp remaining
    minFilteredTimeStamp = filesToMerge[0].fileTime
    maxFilteredTimeStamp = filesToMerge[-1].fileTime
    if isTimeSlice:
        mergedFile = os.path.join(timeSliceDir, "timeSlice.%i.%i.%i.%i.root" % (minTimeMinutes, maxTimeMinutes, minFilteredTimeStamp, maxFilteredTimeStamp))
    # // means integer division
    actualFilterTimeMin = (maxFilteredTimeStamp - minFilteredTimeStamp)//60

    # If in cumulativeMode, we subtract the earliest file from the latest file, unless 
    # minTimeMinutes=-1 or 0, in which case we don't subtract anything from the most recent
    # (if >0, we should subtract the first file; if =0, we should include everything)
    if cumulativeMode and isTimeSlice and minTimeMinutes != 0:
        earliestFile = filesToMerge[0].filename
        latestFile = filesToMerge[-1].filename
        #subtract latestFile from earliestFile
        subtractFiles(earliestFile, latestFile, mergedFile)
        print("Added file %s to timeSlices!" % mergedFile)
        print("Merging complete!")
        return (actualFilterTimeMin, mergedFile)

    if cumulativeMode:
        # Take the most recent file
        filesToMerge = [filesToMerge[-1]]

    if len(filesToMerge) == 1:
        # This is often cumulative mode, but could also be reset mode with only 1 file
        numberOfFiles = len(filesToMerge)
    else:
        # If more than one file (almost assuredly reset mode), merge everything
        for fileCont in filesToMerge:
            print("Added file %s to merger" % fileCont.filename)
            merger.AddFile(fileCont.filename)

        numberOfFiles = merger.GetMergeList().GetEntries()
        if numberOfFiles != len(filesToMerge):
            print("ERROR: Problems encountered when adding files to merger!")

    if isTimeSlice:
        outfile = mergedFile
    else:
        outfile = os.path.join(filenamePrefix, "hists.combined.%i.%i.root" % (numberOfFiles, maxFilteredTimeStamp))
    print("Number of files to be merged: %i" % numberOfFiles)
    print("Output file: %s" % outfile)

    # Set the output and perform the actual merge
    if numberOfFiles == 1:
        # Avoid errors with TFileMerger and only one file.
        # Plus, performance should be better
        shutil.copy(filesToMerge[0].filename, outfile)
    else:
        merger.OutputFile(outfile)
        merger.Merge()
    print("Merging complete!")

    # Add file to subsystem file list
    run.subsystems[subsystem].combinedFile = processingClasses.fileContainer(outfile,
                                                                            startOfRun = run.subsystems[subsystem].startOfRun)
    #run.subsystems[subsystem].files.append(processingClasses.fileContainer(outfile,
    #                                                                       startOfRun = run.subsystems[subsystem].startOfRun))
    return (actualFilterTimeMin, outfile)

###################################################
def subtractFiles(minFile, maxFile, outfile):
    """ Subtract histograms in one file from matching histograms in another. 

    Used for time-dependent merge in cumulative mode. 

    Args:
        minFile (str): File to subtract.
        maxFile (str): File to subtract from. 
        outfile (str): Output file with subtracted histograms. 

    Returns:
        None.

    """

    fMin = TFile(minFile, "READ")
    fMax = TFile(maxFile, "READ")
    fOut = TFile(outfile, "RECREATE")

    # Read in available keys in the file
    keysMinFile = fMin.GetListOfKeys();
    keysMaxFile = fMax.GetListOfKeys();

    # Loop through both files, and subtract matching pairs of histos
    for keyMin in keysMinFile:
        # Ensure that we only take histograms (we would expect such, but better to check for safety)
        classOfObject = gROOT.GetClass(keyMin.GetClassName())
        if not classOfObject.InheritsFrom("TH1"):
            continue

        minHistName = keyMin.GetName()

        for keyMax in keysMaxFile:
            # Ensure that we only take histograms
            classOfObject = gROOT.GetClass(keyMin.GetClassName())
            if not classOfObject.InheritsFrom("TH1"):
                continue

            maxHistName = keyMax.GetName()
            if minHistName == maxHistName:
                minHist = keyMin.ReadObj()
                maxHist = keyMax.ReadObj()
                
                # Subtract the earlier hist from the later hist
                maxHist.Add(minHist,-1)
                fOut.cd()
                maxHist.Write()
                
    fMin.Close()
    fMax.Close()
    fOut.Close()

###################################################
def mergeRootFiles(runs, dirPrefix, forceNewMerge = False, cumulativeMode = True):
    """ Iterates over all runs, all subsystems as specified, and merges histograms according to the merge() function. Results in one combined file per subdirectory.

    Args:
        runDirs (list): List of run directories to perform merge over.
        dirPrefix (str): Directory prefix necessary to get to all of the folders. 
        forceNewMerge (Optional[bool]): Flag to force new merge, regardless of whether it has already been merged.
            Default: False. 
        cumulativeMode (Optional[bool]): Specifies whether the histograms we receive are cumulative or if they 
            have been reset between each acquired ROOT file, i.e. whether we merge in "subscribe mode" or 
            "request/reset mode". Default: True.
    
    Returns:
        list: List containing names of all runs that have been merged.

    """

    if dirPrefix == "":
        currentDir = os.getcwd()
    else:
        currentDir = os.path.abspath(dirPrefix)

    # Process runs
    for runDir, run in runs.iteritems():
        for subsystem in run.subsystems:
            # Only merge if we there are new files to merge
            if run.subsystems[subsystem].newFile == True or forceNewMerge:
                # Perform the merge
                # This is the prefix for working with most files
                filenamePrefix = os.path.join(currentDir, runDir, subsystem)

                # Check for a combined file. The file has a name of the form hists.combined.(number of uncombined
                # files in directory).(timestamp of combined file).root
                # File found via http://stackoverflow.com/a/7006873
                combinedFile = run.subsystems[subsystem].combinedFile
                #combinedFile = next((fileCont.filename for fileCont in run.subsystems[subsystem].files if fileCont.combinedFile == True), None)
                #combinedFile = next((name for name in os.listdir(filenamePrefix) if "combined" in name), None)
                # If it doesn't exist then we go directly to merging; otherwise we check if it is up to date, and
                # delete+remerge if it isn't, and return run name for reprocessing
                #if combinedFile:
                    #needRemerge = False
                    #uncombinedFiles = [name for name in run.subsystems[subsystem].files if "combined" not in name]
                    ##uncombinedFiles = [name for name in os.listdir(filenamePrefix) if "combined" not in name and ".root" in name ]
                    ## We should already have to re-merge here since we know we have new files, but it is possible that they do not matter.
                    ## It is best to check to be certain.
                    #if cumulativeMode:
                    #    # In SUB, compare combined file timestamp with latest timestamp of uncombined file
                    #    print("Checking time stamps to determine if we need to merge...")
                    #    timeStamps = []
                    #    for name in uncombinedFiles:
                    #        timeStamps.append( utilities.extractTimeStampFromFilename(name) )
                    #    combinedTimeStamp = utilities.extractTimeStampFromFilename(combinedFile)
                    #    #combinedTimeStamp = combinedFile.split(".")[3]
                    #    needRemerge = (max(timeStamps) != combinedTimeStamp)
                    #    #needRemerge = (repr(max(timeStamps)) != combinedTimeStamp)
                    #else: # In REQ mode, compare combined file merge count with number of uncombined files
                    #    print("Checking if we have any new files to merge...")
                    #    numberOfFilesPreviouslyMerged = int(combinedFile.split(".")[2])
                    #    #numberOfFilesPreviouslyMerged = combinedFile.split(".")[2]
                    #    print("numberOfFilesPreviouslyMerged = {0}".format(numberOfFilesPreviouslyMerged))
                    #    #print("numberOfFilesPreviouslyMerged = " + numberOfFilesPreviouslyMerged)
                    #    numberOfFilesInDir = len(uncombinedFiles)
                    #    print("numberOfFilesInDir = {0}".format(numberOfFilesInDir))
                    #    #print("numberOfFilesInDir = " + repr(numberOfFilesInDir))
                    #    needRemerge = (numberOfFilesInDir > numberOfFilesPreviouslyMerged)
                    #    #needRemerge = (repr(numberOfFilesInDir) > numberOfFilesPreviouslyMerged)

                if combinedFile:
                    print("Need to merge %s, %s again" % (runDir, subsystem))
                    print("Removing previous merged file %s" % combinedFile.filename)
                    os.remove(os.path.join(filenamePrefix, combinedFile.filename))
                    # Remove from the file list
                    run.subsystems[subsystem].combinedFile = None
                else:
                    print("Need to merge %s, %s" % (runDir, subsystem))
                    #print("WARNING: No need to merge %s, %s again. Check this subsystem!" % (runDir, subsystem))
                    #continue

                # Perform the actual merge
                merge(currentDir, run, subsystem, cumulativeMode)

                # We have successfully merged
                # Still considered a newFile until we have processed, so don't change state here
                #run.subsystems[subsystem].newFile = False

