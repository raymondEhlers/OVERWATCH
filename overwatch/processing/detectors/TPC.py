#!/usr/bin/env python

""" TPC subsystem specific functionality.
The TPC has a variety of monitoring and trending functionality.
.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
.. codeauthor:: Anthony Timmins <anthony.timmins@cern.ch>, University of Houston
.. codeauthor:: Charles Hughes <charles.hughes@cern.ch>, University of Tennessee
.. codeauthor:: Raquel Quishpe <raquel.quishpe@cern.ch>, University of Houston
"""

import ROOT

# General includes
import logging
# Setup logger
logger = logging.getLogger(__name__)

# Used for sorting and generating html
from .. import processingClasses

from overwatch.processing.trending.info import TrendingInfo
import overwatch.processing.trending.objects as trendingObjects
from overwatch.processing.alarms.example import alarmStdConfig, alarmMaxConfig, alarmMeanConfig

try:
    from typing import *  # noqa
except ImportError:
    pass

def getTrendingObjectInfo():  # type: () -> List[TrendingInfo]
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
    # info list has format: ["name", "desc", ["depending histogram name"]]
    infoList = [
        ("TPCClusterTrending", "<TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_0_5_7_restrictedPtEta"]),
        ("TPCFoundClusters", "<Found/Findable TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_2_5_7_restrictedPtEta"]),
        ("TPCdcaR", "<DCAr> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_3_5_7_restrictedPtEta"]),
        ("TPCdcaZ", "<DCAz> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_4_5_7_restrictedPtEta"]),
        ("histvx", "<vx> (cm)", ["TPCQA/h_tpc_event_recvertex_0"]),
        ("histvy", "<vy> (cm)", ["TPCQA/h_tpc_event_recvertex_1"]),
        ("histvz", "<vz> (cm)", ["TPCQA/h_tpc_event_recvertex_2"]),
        ("histMpos", "<Multiplicity of pos. tracks>", ["TPCQA/h_tpc_event_recvertex_4"]),
        ("histMneg", "<Multiplicity of neg. tracks>", ["TPCQA/h_tpc_event_recvertex_5"])
    ]
    trendingNameToObject = {
        "mean": trendingObjects.MeanTrending
    }
    alarms = {
        "mean": alarmMeanConfig()
    }
    trendingInfo = []
    for prefix, cls in trendingNameToObject.items():
        for name, desc, histograms in infoList:
            ti = TrendingInfo(prefix + name, prefix + ": " + desc, histograms, cls)
            if prefix in alarms:
                ti.addAlarm(alarms[prefix])
            trendingInfo.append(ti)
    return trendingInfo

def generalOptions(subsystem, hist, processingOptions):
    """ Processing function where general histograms options that require the underlying histogram and/or canvas
    are set.
    Currently, it ensures that the histogram title is always shown.
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
    # Show TPC titles (by request from Mikolaj)
    # NOTE: Titles are always shown by jsRoot, so this option is only relevant for png images.
    ROOT.gStyle.SetOptTitle(1)

    # drawing options for TH2 hists
    hist.hist.SetOption("COLZ")

def ptSpectra(subsystem, hist, processingOptions, **kwargs):
    """ Processing function for pT spectra.
    Set the y axis labels (x is already set) and log y for a clearer visualization.
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
    hist.hist.GetYaxis().SetTitle("dN/dp_{T}")
    hist.canvas.SetLogy(True)

def findFunctionsForTPCHistogram(subsystem, hist):
    """ Find processing functions for TPC histograms based on their names.
    This plug-in function steers the histograms to the right set of processing functions. These functions
    will then be executed later when the histograms are actually processed. This function only executes
    when the subsystem is created at the start of each new run. By doing so, we can minimize inefficient
    string comparison each time we process a file in the same run.
    The processing functions which are assigned here include those related to the processing of:
    - General TPC histogram options which require the underlying histogram and canvas.
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
    # General TPC Options.
    hist.functionsToApply.append(generalOptions)

    # Improve pt spectra visualization.
    if "pT_" in hist.histName:
        hist.functionsToApply.append(ptSpectra)

def createTPCHistogramGroups(subsystem):
    """ Create histogram groups for the TPC subsystem.
    This functions sorts the histograms into categories for better presentation based on their names.
    The names are determined by those specified for each hist in the subsystem component on the HLT.
    Assignments are made by the looking for substrings specified in the hist groups in the hist names.
    Note that each histogram will be categorized once, so the first entry will take all histograms
    which match. Thus, histograms should be ordered in such that the most inclusive are specified last.
    Generally, hists are sorted as follows:
    - Cluster related histograms
    - Match tracking efficiency
    - Vertex position
    However, as of August 2018, the above list isn't comprehensive due to some difficulty in deciphering
    the histogram names! This can be resolved by a TPC expert.
    Note:
        Since the TPC usually has a corresponding receiver and therefore a file source,
        we include a catch all group at the end. However, it is protected such that it will
        only be added for a particular run if there is actually an TPC file. This avoids
        collecting a bunch of unrelated hists in the case that there isn't a file.
    Args:
        subsystem (subsystemContainer): The subsystem for the current run.
    Returns:
        None. Histogram groups are stored in ``histGroups`` list of the ``subsystemContainer``.
    """
    # Sort the filenames of the histograms into categories for better presentation
    # The order in which these are added is the order in which they are processed!
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("DCAr vs Phi", "DCAr_vs_Phi"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("DCAz vs Phi", "DCAz_vs_Phi"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("TPC Cluster Eta vs Phi", "Eta_vs_Phi"))
    # Must got below "Eta_vs_Phi" because the "Eta_" selection is greedy
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("TPC Cluster Eta", "Eta_"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Pt spectra", "pT_"))
    # Base histograms
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("TPC Cluster", "tpc_clust"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("TPC Constrain", "tpc_constrain"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("TPC Event RecVertex", "event_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Match Tracking Efficiency", "match_trackingeff"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("All RecVertex", "all_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Negative RecVertex", "neg_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Positive RecVertex", "pos_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("event_6", "event_6"))

    # Catch all other TPC hists
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Other TPC", "TPC"))

    # Catch all of the other hists if we have a dedicated receiver.
    # NOTE: We only want to do this if we are using a subsystem that actually has a file from a
    #       dedicated receiver. Otherwise, you end up with lots of irrelevant histograms.
    if subsystem.subsystem == subsystem.fileLocationSubsystem:
        subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non TPC", ""))

def createAdditionalTPCHistograms(subsystem):
    """ Create new TPC histograms by defining new histogram containers and their projection functions.
    New histogram containers for the given subsystem should be created here. The projection function which
    will be used to project from an existing histogram should also be assigned here. The actual histograms
    will be created later when the projection function is executed.
    Here, we define a set of histograms related to:
    - The DCAr and DCAz vs phi for positive and negative tracks separately. In particular, we project
      those histograms to the A side and the C side to determine their performance at the readouts on each side.
    - The DCAz vs phi for all tracks. We restrict the eta and pt ranges. This is just as an example.
    - The eta, phi and pT projection histograms for positive and negative tracks.
    Note:
        Older histograms has an additional "TPCQA " in front of their names (ie. "TPCQA TPCQA/h_tpc_track_pos_recvertex_3_5_6").
        The name was changed in the TPC HLT component. For simplicity, we only consider the current name (ie. without
        the extra "TPCQA ").
    Args:
        subsystem (subsystemContainer): Subsystem for which the additional histograms are to be created.
    Returns:
        None. Newly created histograms are added to ``subsystemContainer.histsAvailable``.
    """
    # Only create the new histograms if the TPC subsystem data is available. Otherwise, the underlying data won't
    # be available, which will cause warnings.
    if subsystem.subsystem != subsystem.fileLocationSubsystem:
        return

    # DCAz and DCAr vs phi
    # Of the form ("Histogram name", "input histogram name")
    # Just for convenience.
    # NOTE: Older histograms has an additional "TPCQA " in front of their names (ie. "TPCQA TPCQA/h_tpc_track_pos_recvertex_3_5_6").
    #       The name was changed in the TPC HLT component. For simplicity, we only consider the current name (ie. without
    #       the extra "TPCQA ").
    names = [("DCAz_vs_Phi_postracks", "TPCQA/h_tpc_track_pos_recvertex_3_5_6"),
             ("DCAz_vs_Phi_negtracks", "TPCQA/h_tpc_track_neg_recvertex_3_5_6"),
             ("DCAr_vs_Phi_postracks", "TPCQA/h_tpc_track_pos_recvertex_4_5_6"),
             ("DCAr_vs_Phi_negtracks", "TPCQA/h_tpc_track_neg_recvertex_4_5_6")]

    for tempName, inputHistName in names:
        # Assign the projection functions (and label for convenience)
        for label, projFunction in [("aSide", aSideProjectToXZ), ("cSide", cSideProjectToXZ)]:
            # For example, "DCAz_vs_Phi_postracks_aSide"
            histName = "{histName}_{label}".format(histName = tempName, label = label)
            # ``histList`` must be a list, so we pass the histogram name as a single entry list
            histCont = processingClasses.histogramContainer(histName = histName, histList = [inputHistName])
            # Provide a more readable name
            tempPrettyName = tempName.split("_")[:-1]
            histCont.prettyName = "{name} for {sign} tracks on {side} side".format(name = " ".join(tempPrettyName), sign = "positive" if "pos" in tempName else "negative", side = "A" if label == "aSide" else "C")
            histCont.projectionFunctionsToApply.append(projFunction)
            subsystem.histsAvailable[histName] = histCont

    #eta, phi and pT projections
    #eta vs. phi pos/neg tracks
    names = [
        ("Eta_vs_Phi_postracks", "TPCQA/h_tpc_track_pos_recvertex_2_5_6"),
        ("Eta_vs_Phi_negtracks", "TPCQA/h_tpc_track_neg_recvertex_2_5_6"),
    ]

    for histName, inputHistName in names:
        histCont = processingClasses.histogramContainer(histName = histName, histList = [inputHistName])
        # Provide a more readable name
        histCont.prettyName = "Eta vs Phi of {sign} tracks".format(sign = "positive" if "pos" in tempName else "negative")
        histCont.projectionFunctionsToApply.append(projectToYZ)
        subsystem.histsAvailable[histName] = histCont

    #eta of pos/neg tracks nclust>70
    names = [
        ("postracks", "TPCQA/h_tpc_track_pos_recvertex_0_5_7"),
        ("negtracks", "TPCQA/h_tpc_track_neg_recvertex_0_5_7"),
    ]

    for tempName, inputHistName in names:
        for label in [("pT"), ("Eta")]:
            histName = "{label}_{histName}".format(histName = tempName, label = label)
            histCont = processingClasses.histogramContainer(histName = histName, histList = [inputHistName])
            # Provide a more readable name
            histCont.prettyName = "{label} of {sign} tracks".format(label = label, sign = "positive" if "pos" in tempName else "negative")
            histCont.projectionFunctionsToApply.append(projectTo1D)
            subsystem.histsAvailable[histName] = histCont

def restrictInclusiveDCAzVsPhiPtEtaRangeAndProjectTo1D(subsystem, hist, processingOptions, **kwargs):
    """ Projection function to restrict the pt and eta ranges of the DCAz vs Phi inclusive histogram.
    This function was built as an example, so the details may not be entirely correct or ideal.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
        kwargs (dict): Additional possible future arguments.
    Returns:
        ROOT.TH1: The projected histogram
    """
    # Restrict pt and eta ranges
    # Pt
    hist.hist.GetZaxis().SetRangeUser(0.25, 10)
    # Eta
    hist.hist.GetYaxis().SetRangeUser(-1, 1)

    # Project and store the projection
    logger.debug("Projecting hist {} with hist container {} (names shouldn't match!)".format(hist.hist.GetName(), hist.histName))
    # NOTE: The ``histName`` of the ``histogramContainer`` corresponds to the name of the histogram (container) that we
    #       created. Thus, we can use it here to set the projection to the proper histogram name.
    tempHist = hist.hist.ProjectionX(hist.histName)
    # Check that we actually have something. We can't assert that it's non-zero because it's possible that at times it actually
    # might be zero. However, we usually expect it to be non-zero.
    logger.debug("Projection entries: {}".format(tempHist.GetEntries()))

    return tempHist

def aSideProjectToXZ(subsystem, hist, processingOptions):
    """ Projection function to provide a TPC histogram onto the A side.
    Particularly built to project the DCAz and DCAr vs Phi histograms onto each readout side. This
    function is a simple wrapper which specifies projecting onto the A side. The actual projection
    work is delegated to ``projectToXZ()``.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
        kwargs (dict): Additional possible future arguments.
    Returns:
        ROOT.TH1: The projected histogram
    """
    return projectToXZ(subsystem, hist, processingOptions, aSide = True)

def cSideProjectToXZ(subsystem, hist, processingOptions):
    """ Projection function to provide a TPC histogram onto the C side.
    Particularly built to project the DCAz and DCAr vs Phi histograms onto each readout side. This
    function is a simple wrapper which specifies projecting onto the C side. The actual projection
    work is delegated to ``projectToXZ()``.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
        kwargs (dict): Additional possible future arguments.
    Returns:
        ROOT.TH1: The projected histogram
    """
    return projectToXZ(subsystem, hist, processingOptions, aSide = False)

def projectToXZ(subsystem, hist, processingOptions, aSide):
    """ Project a given TH3 histogram onto the XZ axis.
    This function was particularly built for projecting DCAz and DCAr vs Phi TH3 histograms,
    where we expect the y axis to correspond to the eta direction. Given this convention, we can
    restrict the y axis to select objects which are on the A side or the C side of the TPC.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
        aSide (bool): True if we should project to the A side. Otherwise, we will project to the
            C side.
    Returns:
        ROOT.TH1: The projected histogram
    """
    if aSide is True:
        hist.hist.GetYaxis().SetRangeUser(15, 29)
    else:
        hist.hist.GetYaxis().SetRangeUser(0, 14)

    # Project to XZ
    tempHist = hist.hist.Project3D("XZ")
    # NOTE: The ``histName`` of the ``histogramContainer`` corresponds to the name of the histogram (container) that we
    #       created. Thus, we can use it here to set the projection to the proper histogram name.
    tempHist.SetName(hist.histName)
    tempHist.SetTitle(hist.histName)
    if "DCAr" in hist.histName:
        tempHist.GetYaxis().SetTitle("DCAr (cm)")
    if "DCAz" in hist.histName:
        tempHist.GetYaxis().SetTitle("DCAz (cm)")

    return tempHist

def projectToYZ(subsystem, hist, processingOptions):
    """ Project a given TH3 histogram onto the YZ axis.
    This function was built to get an eta vs. phi histograms for positive and negative tracks.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
    Returns:
        ROOT.TH2: The projected histogram
    """

    tempHist = hist.hist.Project3D("YZ")
    tempHist.SetName(hist.histName)
    tempHist.SetTitle(hist.histName)

    return tempHist

def projectTo1D(subsystem, hist, processingOptions):
    """ Project a given TH3 histogram onto the Z or Y axis.
    This function was built to get P_T or eta histograms for positive and negative tracks.
    Args:
        subsystem (subsystemContainer): Subsystem which contains the projected histogram.
        hist (histogramContainer): Histogram container corresponding to the projected histogram.
            When this function is called, it contains the histogram to project from, so the hist
            to project from can be retrieved via ``hist.hist``.
        processingOptions (dict): Dictionary of processing options for the given subsystem.
    Returns:
        ROOT.TH1: The projected histogram
    """
    if "pT" in hist.histName:
        tempHist = hist.hist.ProjectionZ(hist.histName, 71, 160, 1, 30)

    if "Eta" in hist.histName:
        tempHist = hist.hist.ProjectionY(hist.histName, 71, 160, 1, 25)

    tempHist.SetTitle("{histName} (ncl>70)".format(histName = hist.histName))

    return tempHist
