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
from ROOT import ROOT, TH1, TH1F, TProfile, TF1, TAxis, gPad, TAxis, TGaxis, SetOwnership, TPaveText, TLegend

# Used for the outlier detection function
import numpy

# Used to enumerate possible names in a list
import itertools

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
def sortSMsInPhysicalOrder(histList):
    """ Sort the SMs according to their physical order in which they are constructed.

    The order is bottom-top, left-right. It is as follows::

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

    Args:
        histList (list): List of histogram names which are sorted in reversed order
            (ie 19, 18, 17, ..).

    Returns:
        list: Contains the histogram names sorted according to the scheme specified above

    """

    tempList = []
    print(len(histList))
    for i in range(0, len(histList), 2):
        # Protect against overflowing the list
        if i != (len(histList)-1):
            tempList.append(histList[i+1])
        tempList.append(histList[i])

    return tempList

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
    groupedHists.append(generateHtml.sortingGroup("Gamma Trigger Low", "GAL"))
    groupedHists.append(generateHtml.sortingGroup("Gamma Trigger High", "GAH"))
    groupedHists.append(generateHtml.sortingGroup("Jet Trigger Low", "JEL"))
    groupedHists.append(generateHtml.sortingGroup("Jet Trigger High", "JEH"))
    groupedHists.append(generateHtml.sortingGroup("L0", "EMCL0"))
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
            # NOTE: Reverse so that we plot SMs in descending order
            group.histList = sorted(group.histList, key=lambda x: int(x[x.find(group.plotInGridSelectionPattern) + len(group.plotInGridSelectionPattern):]), reverse=True)
            group.histList = sortSMsInPhysicalOrder(group.histList)
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
            # EMCal
            htmlText += generateHtml.generateHtmlForPlotInGridLinks(group.name + " - EMCal")
            # DCal
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
            # Seperate out into EMCal and DCal
            # EMCal
            htmlText += generateHtml.generateHtmlForPlotInGrid(group.histList[8:], group.name + " - EMCal", outputFormatting, nColumns = 2)
            # DCal
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
def setEMCDrawOptions(hist, qaContainer):
    # Get NEvents
    nEvents = 1
    nEventsHist = qaContainer.getHist("NEvents")
    if nEventsHist is not None:
        nEvents = nEventsHist.GetBinContent(1)
        #print("NEvents: {0}".format(nEvents))

    # Reset gPad incase it was changed by any functions
    if processingParameters.debug == False:
                hist.SetStats(False)
    gPad.SetLogy(0)
    gPad.SetGrid(0,0)

    # Plot by SM
    if "SM" in hist.GetName():
        #canvas.SetLogz(logz)
        hist.Scale(1. / nEvents)
        labelSupermodules(hist)
        
        # For FEE plots, set a different range
        if "FEE" in hist.GetName():
            gPad.SetLogz(True)
            hist.GetXaxis().SetRangeUser(0, 250)
            hist.GetYaxis().SetRangeUser(0, 20)
        
    # EdgePos plots
    if "EdgePos" in hist.GetName():
        hist.Scale(1./nEvents)
        hist.GetZaxis().SetTitle("entries / events")

    # Check summary FastOR hists
    # First determine possible fastOR names
    fastORLevels = ["EMCTRQA_histFastORL0", "EMCTRQA_histFastORL1"]
    fastORTypes = ["", "Amp", "LargeAmp"]
    possibleFastORNames = [a + b for a,b in list(itertools.product(fastORLevels, fastORTypes))]
    #print(possibleFastORNames)
    #if "FastORL" in hist.GetName() and "SM" not in hist.GetName(): 
    if any(substring == hist.GetName() for substring in possibleFastORNames):
        # Set threshold for printing
        threshold = 0
        # TODO: These thresholds probably need to be tuned
        if "LargeAmp" in hist.GetName():
            threshold = 7e-7
        elif "Amp" in hist.GetName():
            threshold = 10000
        else:
            threshold = 3e-3
        
        # Set hist options
        hist.Sumw2()
        hist.Scale(1. / nEvents)

        # Set style
        hist.SetMarkerStyle(ROOT.kFullCircle)
        hist.SetMarkerSize(0.8)
        hist.SetMarkerColor(ROOT.kBlue+1)
        hist.SetLineColor(ROOT.kBlue+1)
        
        # Find bins above the threshold
        absIdList = []
        for iBin in range(1, hist.GetXaxis().GetNbins()+1):
            if hist.GetBinContent(iBin) > threshold:
                # Translate back from bin number (1, Nbins() + 1) to fastOR ID (0, Nbins())
                absIdList.append(iBin - 1)
            
        # Create pave text to display above threshold values
        # TODO: This should be saved with the element and written to the page rather than the image.
        #        Such a change will require a change in architecture.
        pave = TPaveText(0.1, 0.7, 0.9, 0.2, "NB NDC")
        pave.SetTextAlign(13)
        pave.SetTextFont(43)
        pave.SetTextSize(12)
        pave.SetFillStyle(0)
        pave.SetTextColor(ROOT.kRed)
        pave.SetBorderSize(0)
        SetOwnership(pave, False)
        
        # Add above threshold values to the pave text
        absIdText = ""
        for absId in absIdList:
            if absIdText:
                absIdText = "{0}, {1}".format(absIdText, absId)
            else:
                absIdText = "{0}".format(absId)
            if len(absIdText) > 110:
                pave.AddText(absIdText)
                #print(absIdText)
                absIdText = ""
        #print(hist.GetName())

        # Only draw if we have enough statistics!
        if nEvents > 10000: 
            #print("Drawing hot fastORs!")
            pave.Draw("same")
    
    # PlotMaxPatch plots
    # Ideally EMCal and DCal histos should be plot on the same plot
    # However, sometimes they are unpaired and must be printed individually
    # Subtracted ensures that unpaired subtracted histograms are still printed
    # "EMCRE" ensures that early unpaired histograms are still printed
    if "PatchAmp" in hist.GetName() and "Subtracted" not in hist.GetName() and "EMCRE" not in hist.GetName():
        # Setup canvas as desired
        gPad.SetLogy(True)
        gPad.SetGrid(1,1)

        # Check for the corresponding hist
        if "DCal" in hist.GetName():
            nameToCheck = hist.GetName().replace("DCal", "EMCal")
        else:
            nameToCheck = hist.GetName().replace("EMCal", "DCal")
        otherHist = qaContainer.getHist(nameToCheck)

        # Plot both on the same canvas if they both exist
        if otherHist is not None:

            # List of hists to plot
            hists = []

            # Ensure that the EMCal is plotted first for consistency
            if "DCal" in hist.GetName():
                # Plot EMCal first
                hists.append(otherHist)
                hists.append(hist)
            else:
                # Plot EMCal first
                hists.append(hist)
                hists.append(otherHist)

            #print(hists)

            # Add legend
            legend = TLegend(0.6, 0.9, 0.9, 0.7)
            legend.SetBorderSize(0)
            legend.SetFillStyle(0)
            SetOwnership(legend, False)

            # Lists to use to plot
            detectors = ["EMCal", "DCal"]
            colors = [ROOT.kRed+1, ROOT.kBlue+1]
            markers = [ROOT.kFullCircle, ROOT.kOpenCircle]
            options = ["", "same"]

            # Plot elements
            for tempHist, detector, color, marker, option in zip(hists, detectors, colors, markers, options):
                tempHist.Sumw2()
                tempHist.SetMarkerSize(0.8)
                tempHist.SetMarkerStyle(marker)
                tempHist.SetLineColor(color)
                tempHist.SetMarkerColor(color)

                tempHist.Scale(1./nEvents)
                tempHist.GetYaxis().SetTitle("entries / events")

                # Draw hists
                # This is not the usual philosophy. We are clearing the canvas and then plotting
                # the second hist on it
                tempHist.Draw(option)
                legend.AddEntry(tempHist, detector, "pe")

            # Add legend
            legend.Draw()

            # Add energy axis
            addEnergyAxisToPatches(hists[0])

            # Remove from QA container! (Not currently possible)

            # NOTE: the histogram is named after the EMCal (we have sorted the order of hists so that DCal comes before EMCal)
        else:
            if processingParameters.beVerbose == True:
                print("Adding hist {0} for PatchAmp".format(hist.GetName()))
            # Add histogram to save for later
            # We clone to ensure there are no memory issues
            qaContainer.addHist(hist.Clone(), hist.GetName())

            if "EMCal" in hist.GetName():
                # Needed to print EMC hist if the DCal equivalent does not exist
                # Since the hists are sorted, the EMCal should never come up before the DCal one.
                print("Keeping EMCal hist {0} since it seems to be unpaired with a DCal hist".format(hist.GetName()))

                # Add energy axis
                addEnergyAxisToPatches(hist)

                # Still print the hist
                return False
            else:
                # Don't print the individual histogram
                # WARNING: This could cause unpaired DCal hists to disappear!
                return True

    # Essentially only for legacy support. Newer instances of this plot are handled above
    properlyPlotPatchSpectra(hist)
    addEnergyAxisToPatches(hist)
