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

######################################################################################################
######################################################################################################
# Sorting
######################################################################################################
######################################################################################################

###################################################
def generateHtmlForTableLinks(groupName):
    returnText = '<a href="#' + groupName.replace(" ","") + '">' + groupName + '</a><br>\n'

    return returnText

###################################################
def generateHtmlForTable(listOfHists, groupName, outputFormatting, nColumns):
    """ Generates a html table for a group of histograms
    
    """
    # Needed to count our position in the table
    index = 0

    # Label
    returnText = "<a class=\"anchor\" name=\"" + groupName.replace(" ","") + "\"></a>\n"
    returnText += "<h2>%s</h2>\n" % groupName

    # Start table
    returnText += "<table>\n"
    #returnText += "<table width=\"100%\">\n"
    for filename in listOfHists:
        # Open row if necessary
        if index % nColumns == 0:
            returnText += "<tr>\n"

        # Add image
        outputFilename = outputFormatting % filename
        returnText += """<td>
            <img width="100%%" src="%s" alt="%s">
        </td>
        """ % (outputFilename, outputFilename)

        # Increment counter
        index += 1

        # Close row if necessary
        # We increment before checking since we have now added an element
        if index % nColumns == 0:
            returnText += "</tr>\n"

    # Close table
    returnText += "</table>\n"

    return returnText

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
    # Trigger classes
    gammaHistNames = []
    jetHistNames = []
    bkgHistNames = []

    # Hists to plot by SM
    feeVsTRUHistNames = []
    feeVsSTUHistNames = []
    fastORL0HistNames = []
    fastORL0AmpHistNames = []
    fastORL0LargeAmpHistNames = []
    fastORL1HistNames = []
    fastORL1AmpHistNames = []
    fostORL1LargeAmpHistNames = []

    # Others
    otherEMCHistNames = []
    nonEMCHistNames = []
    for filename in outputHistNames:
        if "GA" in filename:
            gammaHistNames.append(filename)
        elif "JE" in filename:
            jetHistNames.append(filename)
        elif "BKG" in filename:
            bkgHistNames.append(filename)
        elif "FEEvsTRU_SM" in filename:
            feeVsTRUHistNames.append(filename)
        elif "FEEvsSTU_SM" in filename:
            feeVsSTUHistNames.append(filename)
        elif "EMCal" in filename or "Fast" in filename:
            otherEMCHistNames.append(filename)
        else:
            nonEMCHistNames.append(filename)
    gammaHistNames.sort()
    # If we do not sort more carefully, then it will go 1, 10, 11, .., 2, 3, 4,..
    # since the numbers are contained in strings.
    feeVsTRUHistNames = sorted(feeVsTRUHistNames, key=lambda x: int(x[x.find("_SM")+3:]))
    feeVsSTUHistNames = sorted(feeVsSTUHistNames, key=lambda x: int(x[x.find("_SM")+3:]))
    jetHistNames.sort()
    bkgHistNames.sort()
    otherEMCHistNames.sort()
    nonEMCHistNames.sort()

    # Generate links to histograms below
    htmlText = ""
    htmlText += "<div class=\"contentDivider\">\n"
    htmlText += "<h3>" + "Hists by SM" + "</h3>\n"
    if feeVsTRUHistNames != []:
        htmlText += generateHtmlForTableLinks("FEE vs TRU By SM")
    if feeVsSTUHistNames != []:
        htmlText += generateHtmlForTableLinks("FEE vs STU By SM")
    htmlText += "<h3>" + "Gamma Trigger" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(gammaHistNames, 12)
    htmlText += "<h3>" + "Jet Trigger" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(jetHistNames, 12)
    htmlText += "<h3>" + "Background" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(bkgHistNames, 12)
    htmlText += "<h3>" + "Other EMC" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(otherEMCHistNames, 12)
    htmlText += "<h3>" + "Non-EMC" + "</h3>\n"
    htmlText += generateHtml.generateHtmlForHistLinkOnRunPage(nonEMCHistNames, 0)
    htmlText += "</div>\n"

    # Plot histograms in same order as anchors
    if feeVsTRUHistNames != []:
        htmlText += generateHtmlForTable(feeVsTRUHistNames, "FEE vs TRU By SM", outputFormatting, nColumns = 2)
    if feeVsSTUHistNames != []:
        htmlText += generateHtmlForTable(feeVsSTUHistNames, "FEE vs STU By SM", outputFormatting, nColumns = 2)
    htmlText += generateHtml.generateHtmlForHistOnRunPage(gammaHistNames, outputFormatting, 12)
    htmlText += generateHtml.generateHtmlForHistOnRunPage(jetHistNames, outputFormatting, 12)
    htmlText += generateHtml.generateHtmlForHistOnRunPage(bkgHistNames, outputFormatting, 12)
    htmlText += generateHtml.generateHtmlForHistOnRunPage(otherEMCHistNames, outputFormatting, 12)
    htmlText += generateHtml.generateHtmlForHistOnRunPage(nonEMCHistNames, outputFormatting, 0)

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
        hist.SetStats(False)
    else:
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
        #pad.SetLogz(logz)
        #hist.Scale(1. / events)
        
        # for FEE plots, set a different range
        #if "FEE" in hist.GetName():
        #    hist.GetXaxis().SetRangeUser(0, 250)
        #    hist.GetYaxis().SetRangeUser(0, 20)
            
        #hist.Draw("colz")
        
    # Plot2D plots
    if "EdgePos" in hist.GetName():
        #hist.Scale(1./events)
        #hist.GetZaxis().SetTitle("entries / events")
        #hist.Draw("colz")

    # Plot1D plots
    if "EMCTRQA_histFastORL" in hist.GetName() and "SM" not in hist.GetName(): 
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
