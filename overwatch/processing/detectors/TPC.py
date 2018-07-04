""" TPC subsystem specific functions.

This currently serves as a catch all for unsorted histograms. No additional QA functions are applied.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

import ROOT

# General includes
import logging
# Setup logger
logger = logging.getLogger(__name__)

from .. import processingClasses

from ..trendingClasses import TPCTrendingObjectMean, createIfNotExist

def defineTPCTrendingObjects(trending, *args, **kwargs):
    # Being a bit clever so we don't have to repeat too much code
    names = [["TPCClusterTrending", "<TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_0_5_7_restrictedPtEta"]],
             ["TPCFoundClusters", "<Found/Findable TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_2_5_7_restrictedPtEta"]],
             ["TPCdcaR", "<DCAr> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_3_5_7_restrictedPtEta"]],
             ["TPCdcaZ", "<DCAz> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_4_5_7_restrictedPtEta"]],
             ["histvx", "<vx> (cm)", ["TPCQA/h_tpc_event_recvertex_0"]],
             ["histvy", "<vy> (cm)", ["TPCQA/h_tpc_event_recvertex_1"]],
             ["histvz", "<vz> (cm)", ["TPCQA/h_tpc_event_recvertex_2"]],
             ["histMpos", "<Multiplicity of pos. tracks>", ["TPCQA/h_tpc_event_recvertex_4"]],
             ["histMneg", "<Multiplicity of neg. tracks>", ["TPCQA/h_tpc_event_recvertex_5"]]]

    return createIfNotExist(trending, names)

######################################################################################################
######################################################################################################
# Monitoring functions
######################################################################################################
######################################################################################################
def generalTPCOptions(subsystem, hist, processingOptions):
    # Show TPC titles (by request from Mikolaj)
    if "EMC" not in hist.histName:
        ROOT.gStyle.SetOptTitle(1)

def findFunctionsForTPCHistogram(subsystem, hist):
    # General TPC Options
    hist.functionsToApply.append(generalTPCOptions)

    #names = ["TPCQA/h_tpc_track_all_recvertex_0_5_7",
    #         "TPCQA/h_tpc_track_all_recvertex_2_5_7",
    #         "TPCQA/h_tpc_track_all_recvertex_3_5_7",
    #         "TPCQA/h_tpc_track_all_recvertex_4_5_7"]
    #if hist.histName in names:
    #    hist.functionsToApply.append(restrictRangeAndProjectTo1D)

    names = ["TPCQA/h_tpc_track_pos_recvertex_3_5_6",
             "TPCQA/h_tpc_track_neg_recvertex_3_5_6",
             "TPCQA/h_tpc_track_pos_recvertex_4_5_6",
             "TPCQA/h_tpc_track_neg_recvertex_4_5_6"]
    if hist.histName in names:
        hist.functionsToApply.append(aSideProjectToXZ)
        hist.functionsToApply.append(cSideProjectToXZ)

def createTPCHistogramGroups(subsystem):
    # Sort the filenames of the histograms into catagories for better presentation
    # The order in which these are added is the order in which they are processed!    

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

    # Catch all of the other hists
    # NOTE: We only want to do this if we are using a subsystem that actually has a file. Otherwise, you end up with lots of irrelevant histograms
    if subsystem.subsystem == subsystem.fileLocationSubsystem:
        subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non TPC", ""))

def createAdditionalTPCHistograms(subsystem):
    # DCA vs Phi
    # NOTE: This is just an example and may not be the right histogram!
    histCont = processingClasses.histogramContainer("dcaVsPhi", ["TPCQA/h_tpc_track_all_recvertex_4_5_7"])
    histCont.projectionFunctionsToApply.append(restrictRangeAndProjectTo1D)
    subsystem.histsAvailable["dcaVsPhi"] = histCont

def restrictRangeAndProjectTo1D(subsystem, hist, processingOptions):
    # Restrict pt and eta ranges
    # Pt
    #hist.hist.GetZaxis().SetRangeUser(0.25,10);
    ## Eta
    #hist.hist.GetYaxis().SetRangeUser(-1,1);

    # Project and store the projection
    logger.debug("Projecting hist {}".format(hist.hist.GetName()))
    tempHist = hist.hist.ProjectionX("{}_{}".format(hist.hist.GetName(), "restrictedPtEta"))
    logger.debug("Projection entries: {}".format(tempHist.GetEntries()))
    hist.hist = tempHist

# Helper for projectToXZ
def aSideProjectToXZ(subsystem, hist, processingOptions):
    return projectToXZ(subsystem, hist, processingOptions, aSide = True)

# Helper for projectToXZ
def cSideProjectToXZ(subsystem, hist, processingOptions):
    return projectToXZ(subsystem, hist, processingOptions, aSide = False)

def projectToXZ(subsystem, hist, processingOptions, aSide):
    if aSide:
        hist.hist.GetYaxis().SetRangeUser(0, 1)
    else:
        hist.hist.GetYaxis().SetRangeUser(-1, 0)

    # TODO: Reset range after projection (if needed)!!

    # Project to xz
    tempHist = hist.hist.Project3D("xz")
    tempHist.SetName("{0}_xz".format(hist.hist.GetName()))

    # TODO: Create histogram container and save the projected hist
    #       Include axis labels, etc

