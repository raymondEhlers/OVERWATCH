"""
This module contains functions used to merge histograms, including the principal merge function. 

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

from ROOT import gROOT, TH1, TFile, TFileMerger
import os

import utilities

###################################################
def merge(currentDir, runDir, subsystem, cumulativeMode = True, minTimeMinutes = -1, maxTimeMinutes = -1):
    """ Merge function: for a given run and subsystem, merges files appropriately into a combined file.  

    Merge is only performed if we have received new files in specificed run.
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
    filenamePrefix = os.path.join(currentDir, runDir, subsystem)

    # Make directory for time slice histograms
    isTimeSlice = minTimeMinutes != -1 and maxTimeMinutes != -1
    if isTimeSlice:
        timeSliceDir = os.path.join(currentDir, runDir, subsystem, "timeSlices")
        if not os.path.exists(timeSliceDir):
            os.makedirs(timeSliceDir)
            
    # Merging using root
    merger = TFileMerger()

    # Convert filter time to seconds, so it can be added to unix time
    minTimeSec = minTimeMinutes*60
    maxTimeSec = maxTimeMinutes*60

    # Store unmerged filenames and their unix timestamps in dictionary
    [mergeDict, actualMaxTimeMinutes] = utilities.createFileDictionary(currentDir, runDir, subsystem)
    keys = sorted(mergeDict.keys())

    # Get min and max possible time ranges
    minFileTime = keys[0]
    maxFileTime = keys[-1]

    # User filter time, in unix time
    minTimeCutUnix = minTimeSec + minFileTime 
    maxTimeCutUnix = maxTimeSec + minFileTime

    # If max filter time is greater than max file time, merge up to and including last file
    if maxTimeCutUnix > maxFileTime:
        maxTimeCutUnix = maxFileTime
        print "Input max time exceeds data! It has been reset to the maximum allowed."

    # If input time range out of range, return 0
    if isTimeSlice:
        print "Filtering time window! Min: " + `minTimeMinutes` + ", Max: " + `maxTimeMinutes` 
        if not os.path.exists(timeSliceDir):
            os.makedirs(timeSliceDir)
        if minTimeMinutes < 0:
            print "Input time range exceeds time range of data!"
            return 0
        if minTimeCutUnix > maxTimeCutUnix:
            print "Max time must be greater than Min time!"
            return 0

    # Filter mergeDict by input time range
    for unixTimeStamp in keys:
        if isTimeSlice:
            if unixTimeStamp >= minTimeCutUnix and unixTimeStamp <= maxTimeCutUnix:
                continue                   # The file is in the time range, so we keep it
            del mergeDict[unixTimeStamp]   # Otherwise, we remove it
    keys = sorted(mergeDict.keys())

    # Get min and max time stamp remaining
    minFilteredTimeStamp = keys[0]
    maxFilteredTimeStamp = keys[-1]
    if isTimeSlice:
        mergedFile = os.path.join(timeSliceDir, "timeSlice.%i.%i.%i.%i.root" % (minTimeMinutes, maxTimeMinutes, minFilteredTimeStamp, maxFilteredTimeStamp))
    actualFilterTimeMin = (maxFilteredTimeStamp - minFilteredTimeStamp)/60

    # If in cumulativeMode, we subtract the earliest file from the latest file, unless 
    # minTimeMinutes=-1 or 0, in which case we don't subtract anything from the most recent
    # (if >0, we should subtract the first file; if =0, we should include everything)
    if cumulativeMode:
        earliestFile = mergeDict[minFilteredTimeStamp]
        latestFile = mergeDict[maxFilteredTimeStamp]
        if isTimeSlice and minTimeMinutes != 0:
            #subtract latestFile from earliestFile
            subtractFiles(earliestFile, latestFile, mergedFile)
            print("Added file %s to timeSlices!" % mergedFile)
            print("Merging complete!")
            return (actualFilterTimeMin, mergedFile)
        else:
            print("Added file %s to merger" % latestFile)
            merger.AddFile(latestFile)
    # If in reset mode, merge everything
    else:
        for key in keys:
            name = mergeDict[key]
            print("Added file %s to merger" % name)
            merger.AddFile(name)
                
    numberOfFiles = merger.GetMergeList().GetEntries()
    if isTimeSlice:
        outfile = mergedFile
    else:
        outfile = os.path.join(filenamePrefix, "hists.combined.%i.%i.root" % (numberOfFiles, maxFilteredTimeStamp))
    print("Number of files to be merged: %i" % numberOfFiles)
    print("Output file: %s" % outfile)

    # Set the output and perform the actual merge
    merger.OutputFile(outfile)
    merger.Merge()
    print("Merging complete!")
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
def mergeRootFiles(runDirs, subsystemRunDirDict, dirPrefix, subsystemList, forceNewMerge = False, cumulativeMode = True):
    """ Iterates over all runs, all subsystems as specified, and merges histograms according to the merge() function. Results in one combined file per subdirectory.

    Args:
        runDirs (list): List of run directories to perform merge over.
        subsystemRunDirDict (dict): Dictionary containing a list of existing runs for each subsystem.
        dirPrefix (str): Directory prefix necessary to get to all of the folders. 
        subsystemList (list): List of subsystems to perform merge over.
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

    mergedRuns = []
    for runDir in runDirs:
        for subsystem in subsystemList:
            # Check if the run exists for that subsystem
            # If it does not exist, continue on to the next run
            if runDir not in subsystemRunDirDict[subsystem]:
                continue

            filenamePrefix = os.path.join(currentDir, runDir, subsystem)# This is the prefix for working with most files

            # Check for a combined file. The file has a name of the form hists.combined.(number of uncombined
            # files in directory).(timestamp of combined file).root
            # File found via http://stackoverflow.com/a/7006873
            combinedFile = next((name for name in os.listdir(filenamePrefix) if "combined" in name), None)
            # If it doesn't exist then we go directly to merging; otherwise we check if it is up to date, and
            # delete+remerge if it isn't, and return run name for reprocessing
            if combinedFile:
                needRemerge = False
                uncombinedFiles = [name for name in os.listdir(filenamePrefix) if "combined" not in name and ".root" in name ]
                if cumulativeMode: 
                    # In SUB, compare combined file timestamp with latest timestamp of uncombined file
                    print "Checking time stamps to determine if we need to merge..."
                    timeStamps = []
                    for name in uncombinedFiles:
                        timeStamps.append( utilities.extractTimeStampFromFilename(name) )
                    combinedTimeStamp = combinedFile.split(".")[3]
                    needRemerge = (`max(timeStamps)` != combinedTimeStamp)
                else: # In REQ mode, compare combined file merge count with number of uncombined files
                    print "Checking if we have any new files to merge..."
                    numberOfFilesPreviouslyMerged = combinedFile.split(".")[2]
                    print "numberOfFilesPreviouslyMerged = " + numberOfFilesPreviouslyMerged
                    numberOfFilesInDir = len(uncombinedFiles)
                    print "numberOfFilesInDir = " + `numberOfFilesInDir`
                    needRemerge = (`numberOfFilesInDir` > numberOfFilesPreviouslyMerged)
                if needRemerge or forceNewMerge:
                    print("Need to merge %s, %s again" % (runDir, subsystem))
                    print("Removing previous merged file %s" % combinedFile)
                    os.remove(os.path.join(filenamePrefix, combinedFile))
                else:
                    print("No need to merge %s, %s again" % (runDir, subsystem))
                    continue
                    
            # Perform the actual merge
            merge(currentDir, runDir, subsystem, cumulativeMode)

            # Track the runs which have been merged to allow for reprocessing
            # We have successfully merged, so add this to the list
            if runDir not in mergedRuns:
                mergedRuns.append(runDir)

    return mergedRuns

