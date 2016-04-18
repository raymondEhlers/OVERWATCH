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
from ROOT import TH1, TH1F, TProfile, TF1, TAxis, gPad, TAxis, TGaxis, SetOwnership

# Used for the outlier detection function
import numpy

# Used for sorting and generating html
from processRunsModules import generateHtml

# For retrieving debug configuration
from config.processingParams import processingParameters

######################################################################################################
######################################################################################################
# Sorting
######################################################################################################
######################################################################################################

###################################################
def sortAndGenerateHtmlForEMCHists(outputHistNames, outputFormatting, subsystem = "EMC"):
    """ Sorts and displays EMC histograms.

    Heavily relies on :func:`~processRunsModules.generateHtml.generateHtmlForHistLinkOnRunPage`
    and :func:`~processRunsModules.generateHtml.generateHtmlForHistOnRunPage`.
    Check out code for specifics on how the images are sorted and the pages are formatted.

    Args:
        outputHistNames (list): List of histograms to add to the page. Typically, these have
            been printed from ROOT files.
        outputFormatting (str): Specially formatted string which contains a generic path to the printed histograms.
            The string contains "%s" to print the filename contained in listOfHists. It also includes the file
            extension. Ex: "img/%s.png"
        subsystem (str): The current subsystem by three letter, all capital name. Here it should always be ``EMC``.
            Default: "EMC"

    Returns:
        str: HTML containing all of the EMC histograms, with proper formatting and links from the top of the page to the named images.

    """

    # Sort the filenames of the histograms into catagories for better presentation
    groupedHists = []
    # The order in which these are added is the order in which they are processed!
    # Plot by SM
    groupedHists.append(generateHtml.sortingGroup("FEE vs TRU", "FEEvsTRU_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FEE vs STU", "FEEvsSTU_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L0 (hits with ADC > 0)", "FastORL0_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L0 Amp (hits weighted with ADC value)", "FastORL0Amp_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L0 Large Amp (hits above 400 ADC)", "FastORL0LargeAmp_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L1 (hits with ADC > 0)", "FastORL1_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L1 Amp (hits weighted with ADC value)", "FastORL1Amp_SM", "_SM"))
    groupedHists.append(generateHtml.sortingGroup("FastOR L1 Large Amp (hits above 400 ADC)", "FastORL1LargeAmp_SM", "_SM"))
    # Trigger classes
    groupedHists.append(generateHtml.sortingGroup("Gamma Trigger", "GA"))
    groupedHists.append(generateHtml.sortingGroup("Jet Trigger", "JE"))
    groupedHists.append(generateHtml.sortingGroup("Background", "BKG"))
    # Other EMC
    groupedHists.append(generateHtml.sortingGroup("FastOR", "FastOR"))
    groupedHists.append(generateHtml.sortingGroup("Other EMC", "EMC"))
    # Catch all of the other hists
    groupedHists.append(generateHtml.sortingGroup("Non EMC", ""))

    # Group filenames
    for filename in outputHistNames:
        for group in groupedHists:
            if group.selectionPattern in filename:
                group.histList.append(filename)
                # Break so that we don't have multiple copies of hists!
                break

    # Sort
    for group in groupedHists:
        if group.histList == []:
            continue
        if group.plotInGrid == True:
            # If we do not sort more carefully, then it will go 1, 10, 11, .., 2, 3, 4,..
            # since the numbers are contained in strings.
            # NOTE: This find could cause sorting problems if plotInGridSelectionPattern is not in the hist names!
            # However, this would mean that the object has been set up incorrectly
            group.histList = sorted(group.histList, key=lambda x: int(x[x.find(group.plotInGridSelectionPattern) + len(group.plotInGridSelectionPattern):]))
            # NOTE: Reverse so that we plot SMs in descending order
            group.histList.reverse()
        else:
            # Sort hists
            group.histList.sort()

    # Links to histograms
    htmlText = ""
    htmlText += "<div class=\"contentDivider\">\n"
    # Get the proper label for the plots by SM section
    # This depends on all SM plots being processed first
    for group in groupedHists:
        if group.plotInGrid == True and group.histList != []:
            htmlText += "<h3>Plots By SM</h3>\n"
            # We only want to make the label once
            break

    # Generate the actual links
    for group in groupedHists:
        # We don't want to generate any links if there are no hists in the category
        if group.histList == []:
            continue

        if group.plotInGrid == True:
            # Create a link to the group that will be displayed in a grid
            # Seperate out into EMCal and DCal
            htmlText += generateHtml.generateHtmlForPlotInGridLinks(group.name + " - EMCal")
            htmlText += generateHtml.generateHtmlForPlotInGridLinks(group.name + " -  DCal")
        else:
            # Create label for group
            htmlText += "<h3>" + group.name + "</h3>\n"
            startOfName = 12
            if group.selectionPattern == "":
                startOfName = 0
            # Create links to all hists in the group
            htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(group.histList, startOfName)

    # Close the div
    htmlText += "</div>\n"

    # Display histograms in the same order as anchors
    for group in groupedHists:
        # We don't want to add any images if there are no hists in the category
        if group.histList == []:
            continue

        if group.plotInGrid == True:
            # Add images in a grid
            htmlText += generateHtml.generateHtmlForPlotInGrid(group.histList[8:], group.name + " - EMCal", outputFormatting, nColumns = 2)
            htmlText += generateHtml.generateHtmlForPlotInGrid(group.histList[:8], group.name + " -  DCal", outputFormatting, nColumns = 2)
        else:
            # This ensures that we don't cut the names of the non-EMC hists
            startOfName = 12
            if group.selectionPattern == "":
                startOfName = 0
            # Add images for this group
            htmlText += generateHtml.generateHtmlForHistOnRunPage(group.histList, outputFormatting, startOfName)

    return htmlText


######################################################################################################
######################################################################################################
# QA Functions
######################################################################################################
######################################################################################################

###################################################
# Checking for outliers
###################################################
def checkForOutliers(hist, qaContainer):
    """ Checks for outliers in selected histograms.

    Outliers are calculated by looking at the standard deviation. See: :func:`hasSignalOutlier()`.
    This function is mainly a proof of concept, but could become more viable with a bit more work.

    Note:
        This function will add a large TLegend to the histogram noting the mean and the number of
        outliers. It will also display the recalculated mean excluding the outlier(s).

    Args:
        hist (TH1): The histogram to be processed.
        qaContainer (:class:`~processRunsModules.qa.qaFunctionContainer`): Contains information
            about the QA function and histograms, as well as the run being processed.

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
                    print("bin (" + repr(binX) + "," + repr(binY) + ") has amplitude " + repr(amp) + "! This is outside of threshold, [" + '%.2f'%threshDown + "," + '%.2f'%threshUp + "]")
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
# Median Slope Value
###################################################
def determineMedianSlope(hist, qaContainer):
    """ Determines the slope of EMCal vs DCal Median and plots it in a histogram.

    This is a fairly simple function, but it performs the desired example. It also serves as
    an example for more complicated QA functions. It shows how to create a histogram, extract
    a value for each run, and then save out the final histogram during the last run.

    Selects the histogram "EMCTRQA_histEMCalMedianVsDCalMedianRecalc".

    Args:
        hist (TH1): The histogram to be processed.
        qaContainer (:class:`~processRunsModules.qa.qaFunctionContainer`): Contains information
            about the QA function and histograms, as well as the run being processed.

    Returns:
        bool: True if the histogram passed to the function should not be printed. For QA
            functions, this is the desired default.

    """
    if qaContainer is not None:
        #print hist.GetName()
        medianHistName = "medianSlope"
        if hist.GetName() == "EMCTRQA_histEMCalMedianVsDCalMedianRecalc":
            print("qaContainer.currentRun:", qaContainer.currentRun)
            # Create histogram if it is the first run
            #if qaContainer.currentRun == qaContainer.firstRun:
            # Can check for the first run as in the commented line above, but this will not work if the first run does not contain
            # the deisred histogram. This could also be achieved by creating the necessary histogram before checking the passed
            # hists name and then setting a flag (could also override the filledValueInRun flag) to note that it is created.
            print("getHist:", qaContainer.getHist(medianHistName))
            if qaContainer.getHist(medianHistName) is None:
                print("Creating hist", medianHistName)
                medianHist = TH1F(medianHistName, "Median vs Median Slope", len(qaContainer.runDirs), 0, len(qaContainer.runDirs))
                # Save the histogram to the qaContainer.
                qaContainer.addHist(medianHist, medianHist.GetName())

                # Set bin labels
                for i in range(0, len(qaContainer.runDirs)):
                    medianHist.GetXaxis().SetBinLabel(i+1, qaContainer.runDirs[i].replace("Run",""))

            # Fill profile hist and perform a linear fit
            prof = hist.ProfileX()
            linearFit = TF1("fit", "[0]*x+[1]")
            linearFit.SetParameter(0, float(1))
            linearFit.SetParameter(1, float(0))
            prof.Fit(linearFit)

            print("qaContainer.hists:", qaContainer.getHists())
            print("Entries:", qaContainer.getHist(medianHistName).GetEntries())
            #medianHist.SetBinContent(qaContainer.runDirs.index(qaContainer.currentRun) + 1, linearFit.GetParameter("0"))
            # Extract the slope and fill it into the histogram
            qaContainer.getHist(medianHistName).SetBinContent(qaContainer.runDirs.index(qaContainer.currentRun) + 1, linearFit.GetParameter(0))

            # Possible to fill only a single value per run by using this flag.
            # Set this bool so that we know a value was filled.
            #qaContainer.filledValueInRun = True

        # Always want to skip printing the normal histograms when processing.
        return True
    else:
        print("qaContainer must exist to determine the median slope.")

###################################################
# Plot Patch Spectra with logy and grad 
###################################################
def properlyPlotPatchSpectra(hist):
    """ Sets logy and a grid to gPad for particular histograms.

    These conditions are set for "{EMCal,DCal}(Max)Patch{Energy,Amp}".

    Since ROOT creates gPad as a globally available variable, we do not need to pass it into this function.
    However, this does mean that it needs to be reset when we are not interested in these plots.

    Args:
        hist (TH1): The histogram to be processed.

    Returns:
        None

    """
    if any(substring in hist.GetName() for substring in ["EMCalPatchEnergy", "EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalPatchEnergy", "DCalMaxPatchAmp"]):
        gPad.SetLogy()
        gPad.SetGrid(1,1)
    else:
        if processingParameters.debug == False:
            hist.SetStats(False)
        gPad.SetLogy(0)
        gPad.SetGrid(0,0)

###################################################
# Add Energy Axis to Patch Amplitude Spectra
###################################################
def addEnergyAxisToPatches(hist):
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
    if any(substring in hist.GetName() for substring in ["EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalMaxPatchAmp"]):
        kEMCL1ADCtoGeV = 0.07874   # Conversion from EMCAL Level1 ADC to energy
        adcMin = hist.GetXaxis().GetXmin()
        adcMax = hist.GetXaxis().GetXmax()
        EMax = adcMax*kEMCL1ADCtoGeV
        EMin = adcMin*kEMCL1ADCtoGeV
        #yMax = gPad.GetUymax()    # this function does not work here (log problem)
        yMax= 2*hist.GetMaximum()
        energyAxis = TGaxis(adcMin,yMax,adcMax,yMax,EMin,EMax,510,"-")
        SetOwnership(energyAxis, False)
        energyAxis.SetTitle("Energy (GeV)")
        energyAxis.Draw()

###################################################
# Label each individual super module (SM) plot
###################################################
def labelSupermodules(hist):
    if "_SM" in hist.GetName()[-5:]:
        smNumber = hist.GetName()[hist.GetName().find("_SM")+3:]
        hist.SetTitle("SM {0}".format(smNumber))

###################################################
# Add drawing options to plots
# Plots come in 4 types: PlotbySM, Plot2D, Plot1D, PlotMaxMatch
###################################################
def setDrawOptions(hist):
    # somehow need to get the number of events; it is stored in the below histogram
    #if hist.GetName() == "EMCTRQA_histEvents":
    #    events = hist.GetBinContent(1)

    # PlotbySM plots
    if "SM" in hist.GetName():
        pass
        #pad.SetLogz(logz)
        #hist.Scale(1. / events)
        
        # for FEE plots, set a different range
        #if "FEE" in hist.GetName():
        #    hist.GetXaxis().SetRangeUser(0, 250)
        #    hist.GetYaxis().SetRangeUser(0, 20)
            
        #hist.Draw("colz")
        
    # Plot2D plots
    if "EdgePos" in hist.GetName():
        pass
        #hist.Scale(1./events)
        #hist.GetZaxis().SetTitle("entries / events")
        #hist.Draw("colz")

    # Plot1D plots
    if "EMCTRQA_histFastORL" in hist.GetName() and "SM" not in hist.GetName(): 
        pass
        #hist.Sumw2()
        #hist.Scale(1. / events)
        
        #hist.SetMarkerStyle(ROOT.kFullCircle)
        #hist.SetMarkerSize(0.8)
        #hist.SetMarkerColor(ROOT.kBlue+1)
        #hist.SetLineColor(ROOT.kBlue+1)
        
        #absIdList = []
        
        #for ibin in range(1, hist.GetXaxis().GetNbins()+1):
        #    if hist.GetBinContent(ibin) > th:
        #        absIdList.append(ibin-1)
            
        #pave = ROOT.TPaveText(0.1, 0.7, 0.9, 0.2, "NB NDC")
        #pave.SetTextAlign(13)
        #pave.SetTextFont(43)
        #pave.SetTextSize(12)
        #pave.SetFillStyle(0)
        #pave.SetTextColor(ROOT.kRed)
        #pave.SetBorderSize(0)
        
        #absIdText = ""
        
        #for absId in absIdList:
        #    if absIdText:
        #        absIdText = "{0}, {1}".format(absIdText, absId)
        #    else:
        #        absIdText = "{0}".format(absId)
        #    if len(absIdText) > 110:
        #        pave.AddText(absIdText)
        #        print absIdText
        #        absIdText = ""
        #pave.Draw()
    
    # PlotMaxPatch plots
    # Ideally EMCal and DCal histos should be plot on the same plot
    if "MaxPatch" in hist.GetName():
        pass
        #canvas.SetLogy(True)
        
        #legend = ROOT.TLegend(0.6, 0.9, 0.9, 0.7)
        #legend.SetBorderSize(0)
        #legend.SetFillStyle(0)
        #for det,col,marker,opt in zip(detectors,colors,markers,options):
        #    hist.Sumw2()
        #    hist.SetMarkerSize(0.8)
        #    hist.SetMarkerStyle(marker)
        #    hist.SetLineColor(col)
        #    hist.SetMarkerColor(col)
        #    hist.Scale(1./events)
        #    hist.GetYaxis().SetTitle("entries / events")
        #    legend.AddEntry(hist, det, "pe")
        #legend->Draw()
