#!/usr/bin/env python

""" EMC detector specific functionality.

The EMCal has a wide variety of monitoring functions, taking broad advantage of the Overwatch detector
plug-in system. These functions allow for enhanced data extraction, as well as improved presentation.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

# Python 2/3 support
from __future__ import print_function
from future.utils import iteritems
from builtins import range

# General includes
import logging
logger = logging.getLogger(__name__)

import ROOT
# Used to enumerate possible names in a list
import itertools
# Used for the outlier detection function
import numpy

# Basic processing classes
from .. import processingClasses

# For retrieving debug configuration
from ...base import config
(processingParameters, filesRead) = config.readConfig(config.configurationType.processing)

from overwatch.processing.trending.info import TrendingInfo
import overwatch.processing.trending.objects as trendingObjects
from overwatch.processing.alarms.example import alarmStdConfig, alarmMaxConfig, alarmMeanConfig

def getTrendingObjectInfo():
    """ Function create simple data objects - TrendingInfo, from which will be created TrendingObject.

    Format of TrendingInfo constructor arguments:
    name - using in database to map name to trendingObject, must be unique
    desc - verbose description of trendingObject, it is displayed on generated histograms
    histogramNames - list of histogram names from which trendingObject depends
    trendingClass - concrete class of abstract class TrendingObject

     It is possible to catch TrendingInfoException and continue without invalid object
     (for example when TrendingInfo have unavailable histogram [Not implemented in current version])

    Returns:
        list: List of TrendingInfo objects
    """

    # To quick add data we iterate over info list and example trendingObjects
    # info list has format: ["depending histogram name and also trending name", "desc"]
    infoList = [
        ("EMCTRQA_histAmpEdgePosEMCGAHOffline", "Integrated amplitude EMCGAH patch Offline"),
        ("EMCTRQA_histAmpEdgePosEMCGAHOnline", "Integrated amplitude EMCGAH patch Online"),
        ("EMCTRQA_histAmpEdgePosEMCGAHRecalc", "Integrated amplitude EMCGAH patch Recalc"),
        ("EMCTRQA_histAmpEdgePosEMCGALOnline", "Integrated amplitude EMCGAL patch Online"),
        ("EMCTRQA_histAmpEdgePosEMCJEHOffline", "Integrated amplitude EMCJEH patch Offline"),
        ("EMCTRQA_histAmpEdgePosEMCJEHOnline", "Integrated amplitude EMCJEH patch Online"),
        ("EMCTRQA_histAmpEdgePosEMCJEHRecalc", "Integrated amplitude EMCJEH patch Recalc"),
        ("EMCTRQA_histAmpEdgePosEMCJELOnline", "Integrated amplitude EMCJEL patch Online"),
        ("EMCTRQA_histAmpEdgePosEMCL0Offline", "Integrated amplitude EMCL0 patch Offline"),
        ("EMCTRQA_histAmpEdgePosEMCL0Online", "Integrated amplitude EMCL0 patch Online"),
        ("EMCTRQA_histAmpEdgePosEMCL0Recalc", "Integrated amplitude EMCL0 patch Recalc"),
        ("EMCTRQA_histEvents", "Number of events"),
        ("EMCTRQA_histMaxEdgePosEMCGAHOffline", "Edge Position Max EMCGAH patch Offline"),
        ("EMCTRQA_histMaxEdgePosEMCGAHOnline", "Edge Position Max EMCGAH patch Online"),
        ("EMCTRQA_histMaxEdgePosEMCGAHRecalc", "Edge Position Max EMCGAH patch Recalc"),
        ("EMCTRQA_histMaxEdgePosEMCGALOnline", "Edge Position Max EMCGAL patch Online"),
        ("EMCTRQA_histMaxEdgePosEMCJEHOffline", "Edge Position Max EMCJEH patch Offline"),
        ("EMCTRQA_histMaxEdgePosEMCJEHOnline", "Edge Position Max EMCJEH patch Online"),
        ("EMCTRQA_histMaxEdgePosEMCJEHRecalc", "Edge Position Max EMCJEH patch Recalc"),
        ("EMCTRQA_histMaxEdgePosEMCJELOnline", "Edge Position Max EMCJEL patch Online"),
        ("EMCTRQA_histMaxEdgePosEMCL0Offline", "Edge Position Max EMCL0 patch Offline"),
        ("EMCTRQA_histMaxEdgePosEMCL0Online", "Edge Position Max EMCL0 patch Online"),
        ("EMCTRQA_histMaxEdgePosEMCL0Recalc", "Edge Position Max EMCL0 patch Recalc"),
        ("EMCTRQA_histFastORL0", "L0 entries vs FastOR number"),
        ("EMCTRQA_histFastORL0Amp", "L0 amplitudes vs position"),
        ("EMCTRQA_histFastORL0LargeAmp", "L0 (amp>400) vs FastOR number"),
        ("EMCTRQA_histFastORL0Time", "L0 trigger time vs FastOR number"),
        ("EMCTRQA_histFastORL1", "L1 entries vs FastOR number"),
        ("EMCTRQA_histFastORL1Amp", "L1 amplitudes"),
        ("EMCTRQA_histFastORL1LargeAmp", "L1 (amp>400)"),
    ]
    trendingNameToObject = {
        "max": trendingObjects.MaximumTrending,
        "mean": trendingObjects.MeanTrending,
        "stdDev": trendingObjects.StdDevTrending,
    }
    recipients = {
        "max": ["test1@mail", "test2@mail"]
    }
    alarms = {
        "max": alarmMaxConfig(recipients["max"]),
        "mean": alarmMeanConfig(),
        "stdDev": alarmStdConfig()
    }
    trendingInfo = []
    for prefix, cls in trendingNameToObject.items():
        for dependingFile, desc in infoList:
            infoObject = TrendingInfo(prefix + dependingFile, desc, [dependingFile], cls)
            if prefix in alarms:
                infoObject.addAlarm(alarms[prefix])
            trendingInfo.append(infoObject)
    return trendingInfo

def checkForEMCHistStack(subsystem, histName, skipList, selector):
    """ Check for and create histograms stacks from existing histograms.

    This is a helper function for stacking histograms which plot the same quantity,
    but are plotted separately for the EMCal and DCal. It allows both to be plotted
    on the same canvas. It assumes that there will be corresponding EMCal and DCal
    histograms for a particular hist stack.

    Note:
        By including "EMCal" in the ``selector`` string, we can ensure that this function
        will only create the stack when the EMCal hist comes up. If the DCal hist comes up
        first, we will skip over it and then it will be removed from ``subsystem.histsAvailable``
        when the EMCal hist is processed and the hist stack is created.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        histName (str): Name of the histogram currently being considered for inclusion
            in a histogram stack.
        skipList (list): List of histogram names which have already been handled and
            therefore should not be stored later in ``subsystem.histsAvailable``.
        selector (str): Substring which should be used to identify histograms to add
            to a stack.
    Returns:
        bool: True if the histogram was added to the histogram stack.
    """
    # Require both the current hist to be selected, as well as the corresponding DCal hist.
    # NOTE: "EMCal" must be included in the selector name for this function to work properly!
    if selector in histName and selector.replace("EMCal", "DCal") in subsystem.histsInFile:
        histNames = [histName, histName.replace("EMCal", "DCal")]
        # When finished, we only want to store the hist stack, so we add the individual
        # histogram names to the skip list.
        skipList.extend(histName)
        # Remove hists if they exist in the subsystem (EMCal shouldn't, but DCal could) so
        # they are only displayed in the histogram stack.
        for name in histName:
            # See: https://stackoverflow.com/a/15411146
            subsystem.histsAvailable.pop(histName, None)
        # Add a new hist object for the stack
        subsystem.histsAvailable[histName] = processingClasses.histogramContainer(histName = histName, histList = histNames)

        # Ensure that the histogram that we started processing is _not_ stored individually
        # in ``subsystemContainer.histsAvailable``.
        return True

    # If the histogram isn't stored into a stack, we allow it to be included in ``subsystem.histsAvailable``.
    return False

def createEMCHistogramStacks(subsystem):
    """ Create histogram stacks from the existing histograms in the EMCal subsystem.

    Note that although this doesn't necessarily have to be the case, we decided for this function to assume
    that histograms will only be assigned to one stack.

    Note:
        This function is responsible for moving histogram containers from ``subsystem.histsInFile``
        to ``subsystem.histsAvailable``.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. However, see the note above for the side effects.
    """
    skipList = []
    for histName in subsystem.histsInFile:
        # Skip if we have already put it into another stack
        if histName in skipList:
            continue
        # Stack for EMCalMaxPatchAmp
        # Note that this selector _must_ have "EMCal" included for the function to work as expected.
        result = checkForEMCHistStack(subsystem, histName, skipList, "EMCalMaxPatchAmpEMC")
        # Don't store the individual histograms in a stack.
        if result:
            continue
        # Stack for EMCalPatchAmp
        # Note that this selector _must_ have "EMCal" included for the function to work as expected.
        result = checkForEMCHistStack(subsystem, histName, skipList, "EMCalPatchAmpEMC")
        # Don't store the individual histograms in a stack.
        if result:
            continue

        # Just add if it's part of a stack.
        subsystem.histsAvailable[histName] = subsystem.histsInFile[histName]

def setEMCHistogramOptions(subsystem):
    """ Set general EMCal histogram options.

    In particular, these options should apply to all histograms, or at least a broad selection
    of them. The list of histograms are accessed through the ``histsAvailable`` field of the
    ``subsystemContainer``. Canvas options and additional histogram specific options must be
    set later.

    Here, we improve the presentation quality of the histograms by setting the pretty name to
    be presented without the shared name "EMC" prefix (which is contained in the first 12 characters),
    set any ``TH2`` derived hists to draw with ``colz``. We also set all histograms to be scaled
    by the number of events collected.

    Note:
        The underlying hists are not yet available for this function. Only information which is stored
        directly in ``histogramContainer`` fields should be used.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. Histogram groups are stored in appropriate field of the ``subsystemContainer``.
    """
    # Set histogram specific options
    for hist in subsystem.histsAvailable.values():
        # Set the histogram pretty names
        # We can remove the first 12 characters to truncate the prefix off of EMC hists.
        # NOTE: The if statement is to protect against truncating non-EMC hists
        removePrefix = "EMCTRQA_hist"
        if hist.histName.startswith(removePrefix):
            hist.prettyName = hist.histName.replace(removePrefix, "")

        # Set `colz` for any TH2 hists
        if hist.histType.InheritsFrom(ROOT.TH2.Class()):
            hist.drawOptions += " colz"

    # Set general processing options
    # Set the subsystem wide preference that we would like for hists to be scaled by the number of events.
    # This option can then be used in the processing functions to decide whether to scale the histogram
    # which is being processed. This is _not_ performed automatically.
    subsystem.processingOptions["scaleHists"] = True
    # Sets the hot channel threshold. 0 uses the default in the defined function
    subsystem.processingOptions["hotChannelThreshold"] = 0

def createEMCHistogramGroups(subsystem):
    """ Create histogram groups for the EMCal subsystem.

    This functions sorts the histograms into categories for better presentation based
    on their names. The names are determined by those specified for each hist in the
    subsystem component on the HLT. Assignments are made by the looking for substrings
    specified in the hist groups in the hist names. Note that each histogram will be
    categorized once, so the first entry will take all histograms which match. Thus,
    histograms should be ordered in such that the most inclusive are specified last.

    Super module differentiated groups are handled first since they would otherwise populate
    in the more general histogram group corresponding to the same plot. Generally, hists are
    sorted as follows:

    - Trigger type: GA vs JE, low vs high threshold.
    - L0 trigger information.
    - Background (ie background subtraction information, luminosity, etc).
    - Fast OR information.
    - Other EMC information (number of events, etc).
    - Catch all others.

    Note:
        Since the EMCal usually has a corresponding receiver and therefore a file source,
        we include a catch all group at the end. However, it is protected such that it will
        only be added for a particular run if there is actually an EMCal file. This avoids
        collecting a bunch of unrelated hists in the case that there isn't a file.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. Histogram groups are stored in ``histGroups`` list of the ``subsystemContainer``.
    """
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
    # Cluster histograms
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("EMCal cluster level", "Cluster"))
    # Cell ID vs Amplitude, Time
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("EMCal cell level", "hIDvs"))
    # Median vs Median
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("EMCal vs DCal Median", "EMCalMedianVsDCalMedian"))
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

    # Catch all of the other hists if we have a dedicated receiver.
    # NOTE: We only want to do this if we are using a subsystem that actually has a file from a
    #       dedicated receiver. Otherwise, you end up with lots of irrelevant histograms.
    if subsystem.subsystem == subsystem.fileLocationSubsystem:
        subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non EMC", ""))

def generalOptionsRequiringUnderlyingObjects(subsystem, hist, processingOptions, **kwargs):
    """ Processing function where general histograms options that require the underlying histogram and/or canvas
    are set.

    The options specified include:

    - Showing histogram stats if running in debug mode.
    - Disabling display of the title for EMC histograms (the title is _not_ set to empty string to ensure that
      it is still available in the future).
    - Set ``logz`` for all ``TH2`` histograms.

    The canvas is also updated when we are finished to ensure that all options are applied successfully. This
    may not actually be required, but it also doesn't hurt anything.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current histogram and canvas are modified.
    """
    # Set options for when not debugging
    if processingParameters["debug"] is False:
        # Disable hist stats
        hist.hist.SetStats(False)

    # Disable the title
    ROOT.gStyle.SetOptTitle(0)

    # Allows customization of draw options for 2D hists
    if hist.hist.InheritsFrom(ROOT.TH2.Class()):
        hist.canvas.SetLogz()

    # Ensure that the canvas is updated, as Update() does not seem to work
    # See: https://root.cern.ch/root/roottalk/roottalk02/3965.html
    hist.canvas.Modified()

def labelSupermodules(hist):
    """ Set of the title of each histogram which is broken out by super module (SM) to the SM number.

    The super module is determined by extracting it out from the end of the histogram name. In particular,
    the name is expected to end in ``_SM10`` for super module 10.

    Args:
        hist (histogramContainer): The histogram to be processed.
    Returns:
        None. The current histogram and canvas are modified.
    """
    if "_SM" in hist.histName[-5:]:
        smNumber = hist.histName[hist.histName.find("_SM") + 3:]
        hist.hist.SetTitle("SM {smNumber}".format(smNumber = smNumber))
        # Show title
        ROOT.gStyle.SetOptTitle(1)

def smOptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for histograms which are broken out by super module (SM).

    It scales the histogram by number of events as as appropriate based on the EMC processing options,
    as well as labeling each histogram by its SM number.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    #canvas.SetLogz(logz)
    if processingOptions["scaleHists"]:
        hist.hist.Scale(1. / subsystem.nEvents)
    labelSupermodules(hist)

def feeSMOptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for Front End Electronics (FEE) related histograms.

    It sets the Z axis to log, as well as restricting the viewable range to more useful values.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    hist.canvas.SetLogz(True)
    hist.hist.GetXaxis().SetRangeUser(0, 250)
    hist.hist.GetYaxis().SetRangeUser(0, 20)

def addTRUGrid(subsystem, hist):
    """ Add a grid of lines representing the TRU regions.

    By making this grid available, it becomes extremely easy to identify and localized problems that
    depend on a particular TRU. The grid is drawn on the current canvas.

    Note:
        This function implicitly assumes that there is already a canvas created. Since the ``histogramContainer``
        already contains a canvas, this is a reasonable assumption. It is explicitly noted because the dependence
        is only implicit.

    Warning:
        The grid is created by allocating a large number of ``TLine`` objects which are owned by ROOT, but not by
        python. Although this hasn't been observed to be a problem, this could in principle lead to memory problems.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
    Returns:
        None. The current canvas is modified.
    """
    # Draw grid for TRUs in full EMCal SMs
    for x in range(8, 48, 8):
        line = ROOT.TLine(x, 0, x, 60)
        ROOT.SetOwnership(line, False)
        line.Draw()
    # 60 + 1 to ensure that 60 is plotted
    for y in range(12, 60 + 1, 12):
        line = ROOT.TLine(0, y, 48, y)
        ROOT.SetOwnership(line, False)
        line.Draw()

    # Draw grid for TRUs in 1/3 EMCal SMs
    line = ROOT.TLine(0, 64, 48, 64)
    ROOT.SetOwnership(line, False)
    line.Draw()
    line = ROOT.TLine(24, 60, 24, 64)
    ROOT.SetOwnership(line, False)
    line.Draw()

    # Draw grid for TRUs in 2/3 DCal SMs
    for x in range(8, 48, 8):
        if (x == 24):
            # skip PHOS hole
            continue
        line = ROOT.TLine(x, 64, x, 100)
        ROOT.SetOwnership(line, False)
        line.Draw()
    for y in range(76, 100, 12):
        line = ROOT.TLine(0, y, 16, y)
        ROOT.SetOwnership(line, False)
        line.Draw()
        # skip PHOS hole
        line = ROOT.TLine(32, y, 48, y)
        ROOT.SetOwnership(line, False)
        line.Draw()

    # Draw grid for TRUs in 1/3 DCal SMs
    line = ROOT.TLine(0, 100, 48, 100)
    ROOT.SetOwnership(line, False)
    line.Draw()
    line = ROOT.TLine(24, 100, 24, 104)
    ROOT.SetOwnership(line, False)
    line.Draw()

def generalClusterOptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for all cluster histograms.

    Note:
        We only remove the cluster name prefix to ensure that the prefix is available to help classify
        it properly.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = hist.prettyName.replace("hCluster", "")

def numberOfCellsPerCluster(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for the number of cells per cluster.

    The y-axis should be plotted as log, and we set the axis labels.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = "Number of cells/cluster"
    hist.hist.GetXaxis().SetTitle("Number of cells/cluster")
    hist.hist.GetYaxis().SetTitle("Number")
    hist.canvas.SetLogy(True)

def clusterEnergyVsNumberOfCells(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster energy vs number of cells per cluster.

    We set the axis labels and set log x and z for a better representation.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = "Cluster E vs # of cells/cluster"
    hist.hist.GetXaxis().SetTitle("Cluster Energy (GeV)")
    hist.hist.GetYaxis().SetTitle("dN_{cells/cluster}/dE")
    hist.canvas.SetLogx(True)
    hist.canvas.SetLogz(True)

def clusterEnergy(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster energy.

    Set the axis labels and log y for a clearer visualization.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = "Cluster E"
    hist.hist.GetXaxis().SetTitle("Cluster Energy (GeV)")
    hist.hist.GetYaxis().SetTitle("dN_{cluster}/dE")
    hist.canvas.SetLogy(True)

def clusterEnergyVsTime(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster energy vs time.

    Set the axis labels.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = "Cluster E vs Time"
    hist.hist.GetXaxis().SetTitle("Cluster Energy (GeV)")
    hist.hist.GetYaxis().SetTitle("Cluster time (ns)")

def clusterEtaVsPhi(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster eta vs phi.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    hist.prettyName = "Cluster Eta vs Phi"
    # As of November 2018, the hist presentation doesn't need any modification
    # However, we keep it here for easy implementation later.

def clusterInvariantMass(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster invariant mass.

    Set axis labels.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist is modified.
    """
    hist.prettyName = "Cluster Invariant Mass"
    hist.hist.GetXaxis().SetTitle("M_{#gamma#gamma} (GeV/#it{c}^{2})")
    hist.hist.GetYaxis().SetTitle("Counts/1 MeV")

def clusterShape(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cluster shape (M02 and M20).

    Set the axis labels and log y for a clearer visualization.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    # Extract the 02 or 20 from the hist name.
    label = hist.histName[-2:]
    hist.prettyName = "Cluster M{label}".format(label = label)
    hist.hist.GetXaxis().SetTitle("M_{{{label}}}".format(label = label))
    hist.hist.GetYaxis().SetTitle("dN/dM_{{{label}}}".format(label = label))
    hist.canvas.SetLogy(True)

def numberOfClustersVsV0(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for number of clusters vs V0.

    Set the axis range and labels, as well as log z for a clearer visualization.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist and canvas are modified.
    """
    hist.prettyName = "Number of Clusters vs V0 amplitude"
    # NOTE: As of November 2018, the ranges for both axes is too large.
    hist.hist.GetXaxis().SetTitle("Number of clusters")
    hist.hist.GetXaxis().SetRangeUser(0, 1000)
    hist.hist.GetYaxis().SetTitle("V0 amplitude")
    hist.hist.GetYaxis().SetRangeUser(0, 500)
    hist.canvas.SetLogz(True)

def cellIDVsAmplitudeLabels(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cell ID vs amplitude.

    Here, we just set the axis labels.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist is modified.
    """
    hist.prettyName = "Cell ID vs Amplitude - {label}".format(label = hist.histName[-2:])
    hist.hist.GetXaxis().SetTitle("Cell amplitude")
    hist.hist.GetYaxis().SetTitle("Cell ID")

def cellIDVsAmplitudeHighGain(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cell ID vs amplitude for high gain cells.

    Set log x and z for a clearer visualization.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    hist.canvas.SetLogx(True)
    hist.canvas.SetLogz(True)

def cellIDVsTimeLabels(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cell ID vs time.

    Here, we just set the axis labels.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current hist is modified.
    """
    hist.prettyName = "Cell ID vs Time - {label}".format(label = hist.histName[-2:])
    hist.hist.GetXaxis().SetTitle("Cell time (ns)")
    hist.hist.GetYaxis().SetTitle("Cell ID")

def cellIDVsTimeHighGain(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for cell ID vs time for high gain cells.

    Set log x and z for a clearer visualization.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    hist.canvas.SetLogz(True)

def edgePosOptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for patch edge positions histograms.

    It scales the histogram by number of events as as appropriate based on the EMC processing options,
    as well as adding a TRU grid.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    zAxisLabel = "entries"
    if processingOptions["scaleHists"]:
        hist.hist.Scale(1. / subsystem.nEvents)
        zAxisLabel = "entries / events"
    hist.hist.GetZaxis().SetTitle(zAxisLabel)

    if hist.hist.InheritsFrom(ROOT.TH2.Class()):
        # Add grid of TRU boundaries
        addTRUGrid(subsystem, hist)

def fastOROptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for Fast OR based histograms.

    FastOR histograms come in two variates:

    - 1D with cell ID vs amplitude.
    - 2D with cell amplitude vs row, column position.

    For both histogram types, it scales the histogram by number of events as as appropriate based
    on the EMC processing options.

    For the 1D histograms, it can look for hot channels based on a threshold set in the processing options.
    For any channels that are above this threshold, they cell IDs are stored in the ``histogramContainer``.
    This allows for the information for be displayed in the web app for easy reference and action. For applying
    the threshold, it is strongly recommended to scale by the number of events (which is the default for the EMC
    subsystem, but can be modified during time slices). Note that the threshold values passed in from the web app
    are scaled down by ``1e-3`` due to the usually small number of counts exception in hot channels, as well as
    the difficulty in displaying such small numbers.

    For the 2D histograms, it also adds a TRU grid.

    Warning:
        The hot channel thresholds require further tuning. The current (Aug 2018) values are mostly set as a
        proof on concept.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    # Handle the 2D hists
    if hist.hist.InheritsFrom(ROOT.TH2.Class()):
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
            threshold = processingOptions["hotChannelThreshold"] / 1000.0

        # Set hist options
        hist.hist.Sumw2()
        if processingOptions["scaleHists"]:
            hist.hist.Scale(1. / subsystem.nEvents)

        # Set style
        hist.hist.SetMarkerStyle(ROOT.kFullCircle)
        hist.hist.SetMarkerSize(0.8)
        hist.hist.SetMarkerColor(ROOT.kBlue + 1)
        hist.hist.SetLineColor(ROOT.kBlue + 1)

        # Find bins above the threshold
        absIdList = []
        for iBin in range(1, hist.hist.GetXaxis().GetNbins() + 1):
            if hist.hist.GetBinContent(iBin) > threshold:
                # Translate back from bin number (1, Nbins() + 1) to fastOR ID (0, Nbins())
                absIdList.append(iBin - 1)

        hist.information["Threshold"] = threshold
        hist.information["Fast OR Hot Channels ID"] = absIdList

def addEnergyAxisToPatches(subsystem, hist, processingOptions, **kwargs):
    """ Processing function to add an additional axis to patch ADC amplitude spectra showing the conversion from
    ADC counts to energy.

    This function should apply for histograms in which the name matches the rules ``{EMCal,DCal}(Max)PatchAmp``.
    It creates a new ``TGaxis`` that shows the ADC to Energy conversion. It then draws it on selected
    histogram at the top of the plot.

    Note:
        This function implicitly assumes that there is already a canvas created. Since the ``histogramContainer``
        already contains a canvas, this is a reasonable assumption. It is explicitly noted because the dependence
        is only implicit.

    Note:
        The ownership of ``TGaxis`` is given to ROOT to ensure that it continues to exist outside of the
        function scope.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    # Conversion from EMCal L1 ADC to energy
    kEMCL1ADCtoGeV = 0.07874
    adcMin = hist.hist.GetXaxis().GetXmin()
    adcMax = hist.hist.GetXaxis().GetXmax()
    EMax = adcMax * kEMCL1ADCtoGeV
    EMin = adcMin * kEMCL1ADCtoGeV

    # Setup the energy axis.
    # Note that although gPad.GetUymax() seems ideal here, it won't work properly due # to the histogram
    # being plotted as a long. Instead, we need to extract the value based on the maximum.
    yMax = 2 * hist.hist.GetMaximum()
    energyAxis = ROOT.TGaxis(adcMin, yMax, adcMax, yMax, EMin, EMax, 510, "-")
    ROOT.SetOwnership(energyAxis, False)
    energyAxis.SetTitle("Energy (GeV)")
    energyAxis.Draw()

def patchAmpOptions(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for patch ADC amplitude spectra histograms.

    This function supersedes ``properlyPlotPatchSpectra()`` and utilizes ``addEnergyAxisToPatches()``.
    It plots the spectra on a log y axis and adds a grid for easier visualization. In the case of a
    histogram stack containing the EMCal and DCal plots, it is specifically equipped to:

    - Plot the EMCal as red and the DCal as blue.
    - Provide a legend.
    - Scale the histogram by number of events as as appropriate based on the processing options.
    - Add an additional x axis which converts the ADC counts of the patch spectra to energy, thereby
      displaying the spectra in a more familiar unit.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None.
    """
    # Setup canvas as desired
    hist.canvas.SetLogy(True)
    hist.canvas.SetGrid(1, 1)

    # Plot both on the same canvas if they both exist
    #if otherHist is not None:
    if hist.hist.InheritsFrom(ROOT.THStack.Class()):
        # Add legend
        legend = ROOT.TLegend(0.6, 0.9, 0.9, 0.7)
        legend.SetBorderSize(0)
        legend.SetFillStyle(0)
        ROOT.SetOwnership(legend, False)

        # Lists to use to plot
        detectors = ["EMCal", "DCal"]
        colors = [ROOT.kRed + 1, ROOT.kBlue + 1]
        markers = [ROOT.kFullCircle, ROOT.kOpenCircle]
        options = ["", ""]

        # Plot elements
        for tempHist, detector, color, marker, option in zip(hist.hist.GetHists(), detectors, colors, markers, options):
            tempHist.Sumw2()
            tempHist.SetMarkerSize(0.8)
            tempHist.SetMarkerStyle(marker)
            tempHist.SetLineColor(color)
            tempHist.SetMarkerColor(color)

            if processingOptions["scaleHists"]:
                tempHist.Scale(1. / subsystem.nEvents)
            tempHist.GetYaxis().SetTitle("entries / events")

            # Record the entry for the legend.
            legend.AddEntry(tempHist, detector, "pe")

        # Add legend to the canvas.
        legend.Draw()

        # Ensure that canvas is updated to account for the new object colors
        hist.canvas.Update()

        # Add energy axis
        addEnergyAxisToPatches(subsystem, hist, processingOptions, **kwargs)

def properlyPlotPatchSpectra(subsystem, hist, processingOptions, **kwargs):
    """ Processing function to plot patch ADC amplitude spectra with ``logy`` and on a grid.

    Since we are plotting spectra, a log y-axis is helpful for presentation. The grid also
    helps with readability. This function should apply for histograms in which the name matches
    the rules ``{EMCal,DCal}(Max)Patch{Energy,Amp}``.

    This function has been superseded by ``patchAmpOptions()`` but is kept for processing legacy
    histograms.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Processing options to be used in this function. It may be the same
            as the options specified in the subsystem, but it doesn't need to be, such as in the case
            of processing for time slices.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The current canvas is modified.
    """
    hist.canvas.SetLogy(True)
    hist.canvas.SetGrid(1, 1)

def findFunctionsForEMCHistogram(subsystem, hist, **kwargs):
    """ Find processing functions for EMC histograms based on their names.

    This plug-in function steers the histograms to the right set of processing functions. These functions
    will then be executed later when the histograms are actually processed. This function only executes
    when the subsystem is created at the start of each new run. By doing so, we can minimize inefficient
    string comparison each time we process a file in the same run.

    The processing functions which are assigned here include those related to the processing of:

    - General EMC histogram options which require the underlying histogram and canvas.
    - General histograms which are split out by super module.
    - Front end electronics (FEE) oriented histograms.
    - Patch edge position oriented histogram.
    - Fast OR oriented histograms.
    - Patch ADC amplitude oriented histograms (both current and legacy).

    See the particular functions for precisely which options are set.

    Note:
        The rules to select each particular set of histograms have become fairly complicated due to
        the variation of histogram names depending on collision system, changing histograms over time,
        etc. Each group has a fairly detailed describe either through comments or the code itself.
        Due to this complexity, these selections should be modified with care!

    Note:
        The histogram underlying the ``histogramContainer`` which is passed in is not yet available
        for this function. Only information which is stored directly in ``histogramContainer`` fields
        should be used when classifying them and assigning functions.

    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
        hist (histogramContainer): The histogram being processed.
        **kwargs (dict): Reserved for future use.
    Returns:
        None. The hist is modified.
    """
    # General EMC Options
    hist.functionsToApply.append(generalOptionsRequiringUnderlyingObjects)

    # Plot by SM
    if "SM" in hist.histName:
        hist.functionsToApply.append(smOptions)

        # For FEE plots, set a different range
        if "FEE" in hist.histName:
            hist.functionsToApply.append(feeSMOptions)

    # Cluster histograms
    if "hCluster" in hist.histName:
        hist.functionsToApply.append(generalClusterOptions)
    # We need separate functions for pretty much every histogram, so we create a map to avoid too much
    # duplicated code.
    clusterFunctionMap = {
        "hClusterCells": numberOfCellsPerCluster,
        "hClusterEneCells": clusterEnergyVsNumberOfCells,
        "hClusterEneEMCAL": clusterEnergy,
        "hClusterEneVsTime": clusterEnergyVsTime,
        "hClusterEtaVsPhi": clusterEtaVsPhi,
        "hClusterInvariantMass": clusterInvariantMass,
        "hClusterM02": clusterShape,
        "hClusterM20": clusterShape,
        "hClusterNumVsV0": numberOfClustersVsV0,
    }
    for name, func in iteritems(clusterFunctionMap):
        if hist.histName == name:
            hist.functionsToApply.append(func)

    # Cell ID vs Amplitude, Time
    if "hIDvsAmp" in hist.histName:
        hist.functionsToApply.append(cellIDVsAmplitudeLabels)
    if hist.histName == "hIDvsAmpHG":
        hist.functionsToApply.append(cellIDVsAmplitudeHighGain)
    if "hIDvsTime" in hist.histName:
        hist.functionsToApply.append(cellIDVsTimeLabels)
    if hist.histName == "hIDvsTimeHG":
        hist.functionsToApply.append(cellIDVsTimeHighGain)

    # EdgePos plots
    if "EdgePos" in hist.histName:
        hist.functionsToApply.append(edgePosOptions)

    # Check summary FastOR hists
    # First determine possible fastOR names
    fastORLevels = ["EMCTRQA_histFastORL0", "EMCTRQA_histFastORL1"]
    fastORTypes = ["", "Amp", "LargeAmp"]
    possibleFastORNames = [a + b for a, b in list(itertools.product(fastORLevels, fastORTypes))]
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

    # These functions are essentially only for legacy support.
    # The names work out such that newer instances of this plot are handled by ``patchAmpOptions()``.
    if any(substring in hist.histName for substring in ["EMCalPatchEnergy", "DCalPatchEnergy", "EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalMaxPatchAmp"]):
        hist.functionsToApply.append(properlyPlotPatchSpectra)

    if any(substring in hist.histName for substring in ["EMCalPatchAmp", "EMCalMaxPatchAmp", "DCalPatchAmp", "DCalMaxPatchAmp"]):
        hist.functionsToApply.append(addEnergyAxisToPatches)

#### Currently unused functions.
#### However, they are valuable as proof of concepts or for display, such that they could be easily re-added
#### to the subsystem. Thus, they are kept around.

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

    Initially, it sorts the hists into reverse order, and then it performs the SM oriented sort
    as described above. As a practical matter, this function will usually be called via
    ```sortSMsInPhysicalOrder(histList = group.histList, sortKey = group.plotInGridSelectionPattern)``,
    taking advantage of the selection pattern stored in the group.

    Note:
        Since the numbers on which we sort are in strings, the initial sort into reverse order
        is performed carefully, such that the output is 19, 18, ..., (as expected), rather than
        9, 8, 7, ..., 19, 18, ..., 10, 1.

    Note:
        This function isn't currently utilized by the EMC, but it is kept as proof of concept for more complex
        functionality.

    Args:
        histList (list): List of histogram names which contain the sort key. The sort
            key will be used to sort them according to the proper EMCal order.
        sortKey (str): Substring to be removed from the histograms. The remaining str
            should then be the substring which will be used to sort the hists.
    Returns:
        list: Contains the histogram names sorted according to the scheme specified above.
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
        if i != (len(histList) - 1):
            tempList.append(histList[i + 1])
        tempList.append(histList[i])

    return tempList

def checkForOutliers(hist):
    """ Checks for outliers in the provided histogram.

    Outliers are calculated by looking at the standard deviation. See: ```hasSignalOutlier(..)`` for further
    information. This function is mainly a proof of concept, but could become more flexible with a bit more work.

    Note:
        This function will add a large ``TLegend`` to the histogram which notes the mean and the number of
        outliers. It will also display the recalculated mean excluding the outlier(s). This ``TLegend`` is owned
        by ROOT.

    Note:
        This function isn't currently utilized by the EMC, but it is kept as proof of concept for more complex
        functionality.

    Args:
        hist (TH1): The histogram to be processed.
    Returns:
        None. The current canvas is modified.
    """
    (numOutliers, mean, stdev, newMean, newStdev) = hasSignalOutlier(hist)

    # If there are outliers, then print the warning banner.
    if numOutliers:
        # Create TLegend and fill with information if there is an outlier.
        leg = ROOT.TLegend(0.15, 0.5, 0.7, 0.8)
        ROOT.SetOwnership(leg, False)

        leg.SetBorderSize(4)
        leg.SetShadowColor(2)
        leg.SetHeader("#splitline{OUTLIER SIGNAL DETECTED}{IN %s BINS!}" % numOutliers)
        leg.AddEntry(None, "Mean: %s, Stdev: %s" % ('%.2f' % mean, '%.2f' % stdev), "")
        leg.AddEntry(None, "New mean: %s, New Stdev: %s" % ('%.2f' % newMean, '%.2f' % newStdev), "")
        leg.SetTextSize(0.04)
        leg.SetTextColor(2)
        leg.Draw()

def hasSignalOutlier(hist):
    """ Helper function to actually find the outlier from a signal histogram.

    Find mean bin amplitude and standard deviation, remove outliers beyond a particular number of standard
    deviations, and then recalculate the mean and standard deviation. Works for both ``TH1`` and ``TH2``
    (but note that it computes outlier based on bin content, which may not be desirable for ``TH1``; in that
    case mean and std dev can easily be applied).

    Note:
        This function isn't currently utilized by the EMC, but it is kept as proof of concept for more complex
        functionality.

    Args:
        hist (TH1): The histogram to be processed.
    Returns:
        list: [nOutliers, mean, stdev, newMean, newStdev] where nOutliers (int) is the number of outliers,
            mean (float) and stdev (float) are the mean and standard deviation, respectively, of the given
            histogram, and newMean (float) and newStdev (float) are the mean and standard deviation after
            excluding the outlier(s).
    """
    # Whether to include empty bins in mean/std dev calculation
    ignoreEmptyBins = False
    xbins = hist.GetNbinsX()
    ybins = hist.GetNbinsY()
    totalBins = xbins * ybins
    signal = numpy.zeros(totalBins)

    # Get bins for hist
    for binX in range(1, xbins + 1):
        for binY in range(1, ybins + 1):
            binContent = hist.GetBinContent(binX, binY)
            # Bins start at 1, arrays at 0
            signal[(binX - 1) + (binY - 1) * xbins] = binContent

    # Change calculation technique depending on option and type of hist
    if ignoreEmptyBins:
        mean = numpy.mean(signal[signal > 0])
        stdev = numpy.std(signal[signal > 0])
    else:
        mean = numpy.mean(signal)
        stdev = numpy.std(signal)

    # Set thresholds for outliers
    threshUp = mean + stdev
    threshDown = mean - stdev

    # index of outliers in signal array
    outlierList = []
    # Determine if a bin is an outlier
    for binX in range(1, xbins + 1):
        for binY in range(1, ybins + 1):
            amp = signal[(binX - 1) + (binY - 1) * xbins]
            if(amp > threshUp or amp < threshDown):
                if not ignoreEmptyBins or amp > 0:
                    logger.info("bin (" + repr(binX) + "," + repr(binY) + ") has amplitude " + repr(amp) + "! This is outside of threshold, [" + '%.2f' % threshDown + "," + '%.2f' % threshUp + "]")
                    outlierList.append((binX - 1) + (binY - 1) * xbins)

    # Exclude outliers and recalculate
    newSignal = numpy.delete(signal, outlierList)
    if ignoreEmptyBins:
        newMean = numpy.mean(newSignal[newSignal > 0])
        newStdev = numpy.std(newSignal[newSignal > 0])
    else:
        newMean = numpy.mean(newSignal)
        newStdev = numpy.std(newSignal)

    # Info for legend
    return [len(outlierList), mean, stdev, newMean, newStdev]

