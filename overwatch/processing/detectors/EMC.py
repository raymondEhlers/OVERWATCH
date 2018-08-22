#/usr/bin/env python

""" EMC detector specific sorting for monitoring, and QA.

The EMCal has substantial sorting for online monitoring. It also has automated QA monitoring functions that apply
every run and true QA functions that only run at selected times.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# Python 2/3 support
from __future__ import print_function
from builtins import range

# Used for QA functions
from ROOT import gStyle, TH1F, TH2, THStack, TF1, TGaxis, SetOwnership, TLegend, TLine, kRed, kBlue, kOpenCircle, kFullCircle

# Used for the outlier detection function
import numpy

# Used to enumerate possible names in a list
import itertools

# General includes
import logging
# Setup logger
logger = logging.getLogger(__name__)

# Basic processing classes
from .. import processingClasses

# For retrieving debug configuration
from ...base import config
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

######################################################################################################
######################################################################################################
# Sorting
######################################################################################################
######################################################################################################

def sortSMsInPhysicalOrder(histList, sortKey):
    """ Sort the SMs according to their physical order in which they are constructed.

    This is a helper function solely used for displaying EMCal and DCal hists in a particularly
    convenient order. The order is bottom-top, left-right. It is as follows

    ::

        EMCal:
        10 11
        8  9
        6  7
        4  5
        2  3
        0  1

        DCal:
        18 19
        16 17
        14 15
        12 13

    This function will extract a prefix (``sortKey``) from the histogram names and then
    sort them according to the reminaing string. As an example,

    .. code-block:: python

        >>> histList = ["prefix2", "prefix1"]
        >>> sortKey = "prefix"
        >>> histList = sortSMsInPhysicalOrder(histList = histList, sortKey = sortKey)
        >>> histList
        ["prefix1", "prefix2"]

    Initially, it sorts the hists into reverse order, and then it performs the SM oritented sort
    as described above.

    Note:
        Since the numbers on which we sort are in strings, the initial sort into reverse order
        is performed carefully, such that the output is 19, 18, ..., (as expected), rather than
        9, 8, 7, ..., 19, 18, ..., 10, 1.

    Args:
        histList (list): List of histogram names which contain the sort key. The sort
            key will be used to sort them according to the proper EMCal order.
        sortKey (str): Substring to be removed from the histograms. The remaining str
            should then be the substring which will be used to sort the hists.
    Returns:
        list: Contains the histogram names sorted according to the scheme specified above
    """
    # Reverse so that we plot SMs in descending order
    # NOTE: If we do not sort carefully, then it will go 1, 10, 11, .., 2, 3, 4,..  since the
    #       numbers are contained in strings.
    # NOTE: This find could cause sorting problems if plotInGridSelectionPattern is not in the hist names!
    #       However, this would mean that the object has been set up incorrectly.
    histList = sorted(histList, key=lambda x: int(x[x.find(sortKey) + len(sortKey):]), reverse=True)

    # Sort according to SM convention.
    tempList = []
    logger.info("Number of hists to be sorted according to SM convention: {}".format(len(histList)))
    for i in range(0, len(histList), 2):
        # Protect against overflowing the list
        if i != (len(histList)-1):
            tempList.append(histList[i+1])
        tempList.append(histList[i])

    return tempList

###################################################
def checkForEMCHistStack(subsystem, histName, skipList, selector):
    if selector in histName and selector.replace("EMCal", "DCal") in subsystem.histsInFile:
        # Don't add to the availableHists
        histNames = [histName, histName.replace("EMCal", "DCal")]
        skipList.extend(histName)
        # Remove hists if they exist (EMCal shouldn't, but DCal could)
        for name in histName:
            # See: https://stackoverflow.com/a/15411146
            subsystem.histsAvailable.pop(histName, None)
        # Add a new hist object for the stack
        subsystem.histsAvailable[histName] = processingClasses.histogramContainer(histName, histNames)

        return True

    # Return false otherwise
    return False

###################################################
def createEMCHistogramStacks(subsystem):
    skipList = []
    for histName in subsystem.histsInFile:
        # Skip if we have already put it into another stack
        if histName in skipList:
            continue
        # Stack for EMCalMaxPatchAmp
        result = checkForEMCHistStack(subsystem, histName, skipList, "EMCalMaxPatchAmpEMC")
        if result:
            continue
        # Stack for EMCalPatchAmp
        result = checkForEMCHistStack(subsystem, histName, skipList, "EMCalPatchAmpEMC")
        if result:
            continue

        # Just add if we don't want need to stack
        subsystem.histsAvailable[histName] = subsystem.histsInFile[histName]

###################################################
def createEMCHistogramGroups(subsystem):
    # Sort the filenames of the histograms into catagories for better presentation
    # The order in which these are added is the order in which they are processed!
    # Plot by SM
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FEE vs TRU", "FEEvsTRU_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FEE vs STU", "FEEvsSTU_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L0 (hits with ADC > 0)", "FastORL0_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L0 Amp (hits weighted with ADC value)", "FastORL0Amp_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L0 Large Amp (hits above 400 ADC)", "FastORL0LargeAmp_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L1 (hits with ADC > 0)", "FastORL1_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L1 Amp (hits weighted with ADC value)", "FastORL1Amp_SM", "_SM"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR L1 Large Amp (hits above 400 ADC)", "FastORL1LargeAmp_SM", "_SM"))
    # Trigger classes
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Gamma Trigger Low", "GAL"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Gamma Trigger High", "GAH"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Jet Trigger Low", "JEL"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Jet Trigger High", "JEH"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("L0", "EMCL0"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Background", "BKG"))
    # FastOR
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("FastOR", "FastOR"))
    # Other EMC
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Other EMC", "EMC"))

    # Catch all of the other hists
    # NOTE: We only want to do this if we are using a subsystem that actually has a file. Otherwise, you end up with lots of irrelevant histograms
    if subsystem.subsystem == subsystem.fileLocationSubsystem:
        subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non EMC", ""))

###################################################
def setEMCHistogramOptions(subsystem):
    """ Set general hist object options.
    
    Canvas and additional options must be set later."""

    # Set the histogram pretty names
    # We can remove the first 12 characters
    for hist in subsystem.histsAvailable.values():
        # Truncate the prefix off EMC hists, but also protect against truncating non-EMC hists
        if "EMC" in hist.histName:
            hist.prettyName = hist.histName[12:]

        # Set colz for any TH2 hists
        if hist.histType.InheritsFrom(TH2.Class()):
            hist.drawOptions += " colz"

    # Set general processing options
    # Sets the histograms to scale if they are setup to scale by nEvents
    subsystem.processingOptions["scaleHists"] = True
    # Sets the hot channel threshold. 0 uses the default in the defined function
    subsystem.processingOptions["hotChannelThreshold"] = 0

###################################################
def generalEMCOptions(subsystem, hist, processingOptions, **kwargs):
    # Set options for when not debugging
    if processingParameters["debug"] == False:
        # Disable hist stats
        hist.hist.SetStats(False)

    # Disable the title
    gStyle.SetOptTitle(0)

    # Allows curotmization of draw options for 2D hists
    if hist.hist.InheritsFrom(TH2.Class()):
        hist.canvas.SetLogz()

    # Updates the canvas, as Update() does not seem to work
    # See: https://root.cern.ch/root/roottalk/roottalk02/3965.html
    hist.canvas.Modified()

###################################################
#def sortAndGenerateHtmlForEMCHists(outputHistNames, outputFormatting, subsystem = "EMC"):
#    """ Sorts and displays EMC histograms.
#
#    Heavily relies on :func:`~processRuns.generateHtml.generateHtmlForHistLinkOnRunPage`
#    and :func:`~processRuns.generateHtml.generateHtmlForHistOnRunPage`.
#    Check out code for specifics on how the images are sorted and the pages are formatted.
#
#    Args:
#        outputHistNames (list): List of histograms to add to the page. Typically, these have
#            been printed from ROOT files.
#        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
#            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
#            extension. Ex: "img/%s.png"
#        subsystem (str): The current subsystem by three letter, all capital name. Here it should always be ``EMC``.
#            Default: "EMC"
#
#    Returns:
#        str: HTML containing all of the EMC histograms, with proper formatting and links from the top of the page to the named images.
#
#    """

    ## Group filenames
    #for filename in outputHistNames:
    #    for group in groupedHists:
    #        if group.selectionPattern in filename:
    #            group.histList.append(filename)
    #            # Break so that we don't have multiple copies of hists!
    #            break

    ## Sort
    #for group in groupedHists:
    #    if group.histList == []:
    #        continue
    #    if group.plotInGrid == True:
    #        group.histList = sortSMsInPhysicalOrder(histList = group.histList, sortKey = group.plotInGridSelectionPattern)
    #    else:
    #        # Sort hists
    #        group.histList.sort()

    ## Links to histograms
    #htmlText = ""
    #htmlText += "<div class=\"contentDivider\">\n"
    ## Get the proper label for the plots by SM section
    ## This depends on all SM plots being processed first
    #for group in groupedHists:
    #    if group.plotInGrid == True and group.histList != []:
    #        htmlText += "<h3>Plots By SM</h3>\n"
    #        # We only want to make the label once
    #        break

    ## Generate the actual links
    #for group in groupedHists:
    #    # We don't want to generate any links if there are no hists in the category
    #    if group.histList == []:
    #        continue

    #    if group.plotInGrid == True:
    #        # Create a link to the group that will be displayed in a grid
    #        # Seperate out into EMCal and DCal
    #        # EMCal
    #        htmlText += generateHtml.generateHtmlForPlotInGridLinks(group.name + " - EMCal")
    #        # DCal
    #        htmlText += generateHtml.generateHtmlForPlotInGridLinks(group.name + " -  DCal")
    #    else:
    #        # Create label for group
    #        htmlText += "<h3>" + group.name + "</h3>\n"
    #        startOfName = 12
    #        if group.selectionPattern == "":
    #            startOfName = 0
    #        # Create links to all hists in the group
    #        htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(group.histList, startOfName)

    ## Close the div
    #htmlText += "</div>\n"

    ## Display histograms in the same order as anchors
    #for group in groupedHists:
    #    # We don't want to add any images if there are no hists in the category
    #    if group.histList == []:
    #        continue

    #    if group.plotInGrid == True:
    #        # Add images in a grid
    #        # Seperate out into EMCal and DCal
    #        # EMCal
    #        htmlText += generateHtml.generateHtmlForPlotInGrid(group.histList[8:], group.name + " - EMCal", outputFormatting, nColumns = 2)
    #        # DCal
    #        htmlText += generateHtml.generateHtmlForPlotInGrid(group.histList[:8], group.name + " -  DCal", outputFormatting, nColumns = 2)
    #    else:
    #        # This ensures that we don't cut the names of the non-EMC hists
    #        startOfName = 12
    #        if group.selectionPattern == "":
    #            startOfName = 0
    #        # Add images for this group
    #        htmlText += generateHtml.generateHtmlForHistOnRunPage(group.histList, outputFormatting, startOfName)

    #return htmlText


######################################################################################################
######################################################################################################
# QA Functions
######################################################################################################
######################################################################################################

###################################################
# Checking for outliers
###################################################
def checkForOutliers(hist):
    """ Checks for outliers in selected histograms.

    Outliers are calculated by looking at the standard deviation. See: :func:`hasSignalOutlier()`.
    This function is mainly a proof of concept, but could become more viable with a bit more work.

    Note:
        This function will add a large TLegend to the histogram noting the mean and the number of
        outliers. It will also display the recalculated mean excluding the outlier(s).

    Args:
        hist (TH1): The histogram to be processed.

    Returns:
        None

    """
    # If outlier data point, print warning banner
    if hist.GetName() == "":
        tempList = hasSignalOutlier(hist) # array of info from hasSignalOutlier function, to print on legend
        numOutliers = tempList[0]
        mean = tempList[1]
        stdev = tempList[2]
        newMean = tempList[3]
        newStdev = tempList[4]
        if(numOutliers):
            # Create TLegend and fill with information if there is an outlier.
            leg = TLegend(0.15, 0.5, 0.7, 0.8)
            SetOwnership(leg, False)

            leg.SetBorderSize(4)
            leg.SetShadowColor(2)
            leg.SetHeader("#splitline{OUTLIER SIGNAL DETECTED}{IN %s BINS!}" % numOutliers)
            leg.AddEntry(None, "Mean: %s, Stdev: %s" % ('%.2f'%mean, '%.2f'%stdev), "")
            leg.AddEntry(None, "New mean: %s, New Stdev: %s" % ('%.2f'%newMean, '%.2f'%newStdev), "")
            leg.SetTextSize(0.04)
            leg.SetTextColor(2)
            leg.Draw()

###################################################
def hasSignalOutlier(hist):
    """ Helper function to actually find the outlier from a signal.

    Find mean bin amplitude, and return True if at least one bin is beyond a threshold from this mean.
    Works for both TH1 and TH2 (but note that it computes outlier based on bin content, which may not be 
    desirable for TH1; in that case mean and stdev can easily be applied).

    Args:
        hist (TH1): The histogram to be processed.

    Returns:
        tuple: Tuple containing:

            len(outlierList) (int): Number of outliers

            mean (float): Mean of the histogram

            stdev (float): Standard deviation of the hist

            newMean (float): Recalculated mean after excluding the outlier(s)

            newStdev (float): Recalculated standard deviation after excluding the outlier(S)

    """
    ignoreEmptyBins = False     # whether to include empty bins in mean/stdev calculation
    xbins = hist.GetNbinsX()
    ybins = hist.GetNbinsY()
    totalBins = xbins*ybins
    signal = numpy.zeros(totalBins)
    
    # Get bins for hist
    for binX in range(1, xbins+1):
        for binY in range(1, ybins+1):
            binContent = hist.GetBinContent(binX, binY)
            signal[(binX-1) + (binY-1)*xbins] = binContent #bins start at 1, arrays at 0

    # Change calculation technique depending on option and type of hist
    if ignoreEmptyBins:
        mean = numpy.mean(signal[signal>0])
        stdev = numpy.std(signal[signal>0])
    else:
        mean = numpy.mean(signal)
        stdev = numpy.std(signal)

    # Set thresholds for outliers
    threshUp = mean + stdev
    threshDown = mean - stdev
    
    outlierList = [] # index of outliers in signal array
    # Determine if a bin is an outlier
    for binX in range(1, xbins+1):
        for binY in range(1, ybins+1):
            amp = signal[(binX-1) + (binY-1)*xbins]
            if(amp > threshUp or amp < threshDown):
                if not ignoreEmptyBins or amp > 0: 
                    logger.info("bin (" + repr(binX) + "," + repr(binY) + ") has amplitude " + repr(amp) + "! This is outside of threshold, [" + '%.2f'%threshDown + "," + '%.2f'%threshUp + "]")
                    outlierList.append((binX-1) + (binY-1)*xbins)
    
    # Exclude outliers and recalculate
    newSignal = numpy.delete(signal, outlierList)
    if ignoreEmptyBins:
        newMean = numpy.mean(newSignal[newSignal>0])
        newStdev = numpy.std(newSignal[newSignal>0])
    else:
        newMean = numpy.mean(newSignal)
        newStdev = numpy.std(newSignal)

    return [len(outlierList), mean, stdev, newMean, newStdev] # info for legend

###################################################
# Plot Patch Spectra with logy and grad 
###################################################
def properlyPlotPatchSpectra(subsystem, hist, processingOptions):
    """ Sets logy and a grid to gPad for particular histograms.

    These conditions are set for "{EMCal,DCal}(Max)Patch{Energy,Amp}".

    Since ROOT creates gPad as a globally available variable, we do not need to pass it into this function.
    However, this does mean that it needs to be reset when we are not interested in these plots.

    Args:
        hist (TH1): The histogram to be processed.

    Returns:
        None

    """
    hist.canvas.SetLogy()
    hist.canvas.SetGrid(1,1)

###################################################
# Add Energy Axis to Patch Amplitude Spectra
###################################################
def addEnergyAxisToPatches(subsystem, hist, processingOptions):
    """ Adds an additional axis showing the conversion from ADC counts to Energy.

    These conditions are set for "{EMCal,DCal}(Max)PatchAmp".
    It creates a new TGaxis that shows the ADC to Energy conversion. It then draws it on selected
    histogram. 

    Warning:
        This function assumes that there is already a canvas created.

    Note:
        TGaxis removes ownership from Python to ensure that it continues to exist outside of the
        function scope.

    Args:
        hist (TH1): The histogram to be processed.

    Returns:
        None

    """
    kEMCL1ADCtoGeV = 0.07874   # Conversion from EMCAL Level1 ADC to energy
    adcMin = hist.hist.GetXaxis().GetXmin()
    adcMax = hist.hist.GetXaxis().GetXmax()
    EMax = adcMax*kEMCL1ADCtoGeV
    EMin = adcMin*kEMCL1ADCtoGeV
    #yMax = gPad.GetUymax()    # this function does not work here (log problem)
    yMax= 2*hist.hist.GetMaximum()
    energyAxis = TGaxis(adcMin,yMax,adcMax,yMax,EMin,EMax,510,"-")
    SetOwnership(energyAxis, False)
    energyAxis.SetTitle("Energy (GeV)")
    energyAxis.Draw()

###################################################
# Label each individual super module (SM) plot
###################################################
def labelSupermodules(hist):
    """ Label each individual super module (SM) plot.

    The label is inserted in the title.

    """
    if "_SM" in hist.histName[-5:]:
        smNumber = hist.histName[hist.histName.find("_SM")+3:]
        hist.hist.SetTitle("SM {0}".format(smNumber))
        # Show title
        gStyle.SetOptTitle(1)

###################################################
# Add a grid representing the TRUs to a canvas.
###################################################
def addTRUGrid(subsystem, hist):
    """ Add a grid of TLines representing the TRU on a canvas.

    Note:
        Assumes that the canvas is already created.

    Note:
        Allocates a large number of TLines which have SetOwnership(obj, False),
        so this could lead to memory problems.

    """
    # TEMP
    logger.debug("TRU Grid histName: {0}".format(hist.histName))

    # Draw grid for TRUs in full EMCal SMs
    for x in range(8, 48, 8):
        line = TLine(x, 0, x, 60)
        SetOwnership(line, False)
        line.Draw()
    # 60 + 1 to ensure that 60 is plotted
    for y in range(12, 60+1, 12):
        line = TLine(0, y, 48, y)
        SetOwnership(line, False)
        line.Draw()

    # Draw grid for TRUs in 1/3 EMCal SMs
    line = TLine(0, 64, 48, 64)
    SetOwnership(line, False)
    line.Draw()
    line = TLine(24, 60, 24, 64)
    SetOwnership(line, False)
    line.Draw()

    # Draw grid for TRUs in 2/3 DCal SMs
    for x in range(8, 48, 8):
        if (x == 24):
            # skip PHOS hole
            continue
        line = TLine(x, 64, x, 100);
        SetOwnership(line, False)
        line.Draw();
    for y in range(76, 100, 12):
        line = TLine(0, y, 16, y)
        SetOwnership(line, False)
        line.Draw()
        # skip PHOS hole
        line = TLine(32, y, 48, y)
        SetOwnership(line, False)
        line.Draw()

    # Draw grid for TRUs in 1/3 DCal SMs
    line = TLine(0, 100, 48, 100)
    SetOwnership(line, False)
    line.Draw()
    line = TLine(24, 100, 24, 104)
    SetOwnership(line, False)
    line.Draw()

###################################################
def edgePosOptions(subsystem, hist, processingOptions):
    if processingOptions["scaleHists"]:
        hist.hist.Scale(1. / subsystem.nEvents)
    hist.hist.GetZaxis().SetTitle("entries / events")

    if hist.hist.InheritsFrom("TH2"):
        # Add grid of TRU boundaries
        addTRUGrid(subsystem, hist)

###################################################
def smOptions(subsystem, hist, processingOptions):
    #canvas.SetLogz(logz)
    if processingOptions["scaleHists"]:
        hist.hist.Scale(1. / subsystem.nEvents)
    labelSupermodules(hist)

###################################################
def feeSMOptions(subsystem, hist, processingOptions):
    hist.canvas.SetLogz(True)
    hist.hist.GetXaxis().SetRangeUser(0, 250)
    hist.hist.GetYaxis().SetRangeUser(0, 20)

###################################################
def fastOROptions(subsystem, hist, processingOptions):
    # Handle the 2D hists
    if hist.hist.InheritsFrom("TH2"):
        # Add grid of TRU boundaries
        addTRUGrid(subsystem, hist)

        # Scale hist
        if processingOptions["scaleHists"]:
            hist.hist.Scale(1. / subsystem.nEvents)
        hist.hist.GetZaxis().SetTitle("entries / events")
    else:
        # Check thresholds for hot fastORs in 1D hists
        # Set threshold for printing
        threshold = 0
        # TODO: These thresholds probably need to be tuned
        if "LargeAmp" in hist.histName:
            threshold = 1e-7
        elif "Amp" in hist.histName:
            threshold = 10000
        else:
            threshold = 1e-2

        # Set the threshold from the processing options if it was set!
        if processingOptions["hotChannelThreshold"] > 0:
            # Normalize by 1000, since it is displayed that way on the site to make it readable.
            # ie. Map 0 to 1e3 -> 1e-3 to 1
            threshold = processingOptions["hotChannelThreshold"]/1000.0

        # Set hist options
        hist.hist.Sumw2()
        if processingOptions["scaleHists"]:
            hist.hist.Scale(1. / subsystem.nEvents)

        # Set style
        hist.hist.SetMarkerStyle(kFullCircle)
        hist.hist.SetMarkerSize(0.8)
        hist.hist.SetMarkerColor(kBlue+1)
        hist.hist.SetLineColor(kBlue+1)

        # Find bins above the threshold
        absIdList = []
        for iBin in range(1, hist.hist.GetXaxis().GetNbins()+1):
            if hist.hist.GetBinContent(iBin) > threshold:
                # Translate back from bin number (1, Nbins() + 1) to fastOR ID (0, Nbins())
                absIdList.append(iBin - 1)

        hist.information["Threshold"] = threshold
        hist.information["Fast OR Hot Channels ID"] = absIdList

###################################################
def patchAmpOptions(subsystem, hist, processingOptions):
    # Setup canvas as desired
    hist.canvas.SetLogy(True)
    hist.canvas.SetGrid(1,1)

    # Plot both on the same canvas if they both exist
    #if otherHist is not None:
    if hist.hist.InheritsFrom(THStack.Class()):
        # Add legend
        legend = TLegend(0.6, 0.9, 0.9, 0.7)
        legend.SetBorderSize(0)
        legend.SetFillStyle(0)
        SetOwnership(legend, False)

        # Lists to use to plot
        detectors = ["EMCal", "DCal"]
        colors = [kRed+1, kBlue+1]
        markers = [kFullCircle, kOpenCircle]
        options = ["", ""]

        # Plot elements
        for tempHist, detector, color, marker, option in zip(hist.hist.GetHists(), detectors, colors, markers, options):
            tempHist.Sumw2()
            tempHist.SetMarkerSize(0.8)
            tempHist.SetMarkerStyle(marker)
            tempHist.SetLineColor(color)
            tempHist.SetMarkerColor(color)

            if processingOptions["scaleHists"]:
                tempHist.Scale(1./subsystem.nEvents)
            tempHist.GetYaxis().SetTitle("entries / events")

            # Draw hists
            # This is not the usual philosophy. We are clearing the canvas and then plotting
            # the second hist on it
            #tempHist.Draw(option)
            legend.AddEntry(tempHist, detector, "pe")

        # Add legend
        legend.Draw()

        # Ensure that canvas is updated to account for the new object colors
        hist.canvas.Update()

        # Add energy axis
        addEnergyAxisToPatches(subsystem, hist, processingOptions)

###################################################
# Add drawing options to plots
# Plots come in 4 types: PlotbySM, Plot2D, Plot1D, PlotMaxMatch
###################################################
def findFunctionsForEMCHistogram(subsystem, hist):

    # General EMC Options
    hist.functionsToApply.append(generalEMCOptions)

    # Plot by SM
    if "SM" in hist.histName:
        hist.functionsToApply.append(smOptions)
       
        # For FEE plots, set a different range
        if "FEE" in hist.histName:
            hist.functionsToApply.append(feeSMOptions)
                    
    # EdgePos plots
    if "EdgePos" in hist.histName:
        hist.functionsToApply.append(edgePosOptions)
        
    # Check summary FastOR hists
    # First determine possible fastOR names
    fastORLevels = ["EMCTRQA_histFastORL0", "EMCTRQA_histFastORL1"]
    fastORTypes = ["", "Amp", "LargeAmp"]
    possibleFastORNames = [a + b for a,b in list(itertools.product(fastORLevels, fastORTypes))]
    #logger.debug(possibleFastORNames)
    #if "FastORL" in hist.GetName() and "SM" not in hist.GetName(): 
    if any(substring == hist.histName for substring in possibleFastORNames):
        hist.functionsToApply.append(fastOROptions)
            
    # PlotMaxPatch plots
    # Ideally EMCal and DCal histos should be plot on the same plot
    # However, sometimes they are unpaired and must be printed individually
    # Subtracted ensures that unpaired subtracted histograms are still printed
    # "EMCRE" ensures that early unpaired histograms are still printed
    if "PatchAmp" in hist.histName and "Subtracted" not in hist.histName and "EMCRE" not in hist.histName:
        hist.functionsToApply.append(patchAmpOptions)

    # Essentially only for legacy support. Newer instances of this plot are handled above
    if any(substring in hist.histName for substring in ["EMCalPatchEnergy", "EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalPatchEnergy", "DCalMaxPatchAmp"]):
        hist.functionsToApply.append(properlyPlotPatchSpectra)

    if any(substring in hist.histName for substring in ["EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalMaxPatchAmp"]):
        hist.functionsToApply.append(addEnergyAxisToPatches)

