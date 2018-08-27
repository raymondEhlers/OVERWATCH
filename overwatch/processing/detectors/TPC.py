#/usr/bin/env python

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

# Used for sorting and generating html
from .. import processingClasses

##################
# Trending Classes
##################
class TPCTrendingObjectMean(processingClasses.trendingObject):
    """ Basic trending object which extracts the mean from a 1D histogram.

    This function serves as a proof of principle for a trending object which trends the mean
    value of a 1D histogram vs time. Although it is labeled as TPC, it is actually entirely
    general. It is just labeled as such here because that was its original purpose.

    Most of the heavy lifting is done by the base class. This class simply implements the methods
    to extract the values (values are extracted via the dedicated histogram methods, so this class
    is rather light).

    Args:
        trendingHistName (str): Name of the trending object.
        trendingHistTitle (str): Name of the trending object that is appropriate for display.
        histNames (list): List of the names of histograms which are needed to perform the trending.
        nEntries (int): Number of entries the trending object should contain. Default: 50.

    Attributes:
        Attributes of ``trendingObject``. No attributes are added by this derived class.
    """
    def __init__(self, trendingHistName, trendingHistTitle, histNames, nEntries = 50):
        super(TPCTrendingObjectMean, self).__init__(trendingName = trendingHistName, prettyTrendingName = trendingHistTitle, nEntries = nEntries, trendingHist = None, histNames = histNames)

    def retrieveHistogram(self):
        """ Retrieve or create a graph based on the stored numpy array.

        This function relies on the base class to perform the actual retrieval. This function
        provides additional customization to the object. In particular, we set the x-axis to
        display a time axis, as appropriate for a trended object. We could also customize the
        format of the time stored on the x-axis.

        Args:
            None
        Returns:
            histogramContainer: Container which holds the created graph. It is returned to allow for
                further customization. This histogram container is already stored in the object.
        """
        # This will retrieve the underlying object from the database. Afterwards retrieval,
        # we can customized it.
        super(TPCTrendingObjectMean, self).retrieveHistogram()

        # Set the histogram to display a time axis
        self.hist.hist.GetXaxis().SetTimeDisplay(1)
        # Could also configure the time format.
        #self.trendingHist.GetXaxis().SetTimeFormat()

        # Make the markers more visible
        self.hist.hist.SetMarkerStyle(ROOT.kFullCircle)

        logger.debug("self.hist: {}, self.hist.hist: {}".format(self.hist, self.hist.hist))

        # The hist is already available through the histogram container, but we return the hist
        # container in case the caller wants to do additional customization
        return self.hist

    def fill(self, hist):
        """ Extract the mean and error and store the value in the trending objects.

        The values are extracted directly from the histograms via their dedicated methods. Storage of the
        values is passed onto the ``trendingObject.fill(...)`` method of the base class. Note that the
        method signatures are different!

        The name of this method was inspired by ``TH1.Fill(val)`` in which it fills values into a histogram.

        Args:
            hist (histogramContainer): Histogram from which the trended value should be extracted.
        Returns:
            None. The extracted value is stored in the trending object.
        """
        if len(self.histNames) > 1:
            raise ValueError("Too many histograms passed to the trending object. Expected histograms named: {}!".format(self.histNames))

        logger.debug("Filling hist {}, histNames: {}".format(self.hist, self.histNames))
        fillVal = 0
        fillValError = 0
        #for histName in self.histNames:
        #    hist = hists[histName]
        # Could do something more complicated here, but we really only want the one value
        fillVal += hist.hist.GetMean()
        fillValError += hist.hist.GetMeanError()

        logger.debug("Filling value: {}, error: {}".format(fillVal, fillValError))
        super(TPCTrendingObjectMean, self).fill(fillVal, fillValError)

def defineTPCTrendingObjects(trending, **kwargs):
    """ Define the TPC trending objects, including the histogram upon which they rely (via the histogram names).

    In particular, we need to define the trending objects, with their names as the keys in the trending
    dictionary. Of particular note are the histogram names which are needed to contribute to the trending
    object. Since in principle this could be more than one histogram, the names must be specified in a list.
    Since the TPC trending histograms only need one histogram, the list is just one entry long.

    While we could define the objects one by one, it would lead to some repeated code. Instead, we define
    a set of nested lists for convenience. The format of the each entry in the list is
    ``["trendingObjectName", "Trending Object Display Name", ["histogramName"]]``. This way, we only call
    the definition of the trending object once, which allows us to easily change it if necessary. We are able
    to utilize this approach because every object defined here is the trend of the mean of a particular
    quantity.

    Args:
        trending (dict): Where the trending objects should be defined. Keys are the name of the trending
            objects, while values are the trending objects themselves.
        **kwargs (dict): Reserved for future use.
    Returns:
        dict: Dictionary filled with the trending objects. Keys are the name of the trending objects, while
            values are the trending objects themselves.
    """
    # Being a bit clever so we don't have to repeat too much code
    # Each list entry is ["trendingObjectName", "Trending Object Display Name", ["histogramName"]]
    names = [["TPCClusterTrending", "<TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_0_5_7_restrictedPtEta"]],
             ["TPCFoundClusters", "<Found/Findable TPC clusters>: (p_{T} > 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_2_5_7_restrictedPtEta"]],
             ["TPCdcaR", "<DCAr> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_3_5_7_restrictedPtEta"]],
             ["TPCdcaZ", "<DCAz> (cm)>: (p_{T}> 0.25 GeV/c, |#eta| < 1)", ["TPCQA/h_tpc_track_all_recvertex_4_5_7_restrictedPtEta"]],
             ["histvx", "<vx> (cm)", ["TPCQA/h_tpc_event_recvertex_0"]],
             ["histvy", "<vy> (cm)", ["TPCQA/h_tpc_event_recvertex_1"]],
             ["histvz", "<vz> (cm)", ["TPCQA/h_tpc_event_recvertex_2"]],
             ["histMpos", "<Multiplicity of pos. tracks>", ["TPCQA/h_tpc_event_recvertex_4"]],
             ["histMneg", "<Multiplicity of neg. tracks>", ["TPCQA/h_tpc_event_recvertex_5"]]]

    # Create and store the object
    for name, title, histNames in names:
        # It may be possible that the object already exists, so be certain that we don't overwrite it.
        # NOTE: The object already existing is not possible as of August 2018.
        if not name in trending.keys():
            # Define and store new trending histogram
            trending[name] = TPCTrendingObjectMean(name, title, histNames)

    return trending

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

    #names = ["TPCQA/h_tpc_track_pos_recvertex_3_5_6",
    #         "TPCQA/h_tpc_track_neg_recvertex_3_5_6",
    #         "TPCQA/h_tpc_track_pos_recvertex_4_5_6",
    #         "TPCQA/h_tpc_track_neg_recvertex_4_5_6"]
    #if hist.histName in names:
    #    hist.functionsToApply.append(aSideProjectToXZ)
    #    hist.functionsToApply.append(cSideProjectToXZ)

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
    # Of the form ("Histogram name", "input histogram name")
    names = [("hist1", "TPCQA/h_tpc_track_pos_recvertex_3_5_6"),
             ("hist2", "TPCQA/h_tpc_track_neg_recvertex_3_5_6"),
             ("hist3", "TPCQA/h_tpc_track_pos_recvertex_4_5_6"),
             ("hist4", "TPCQA/h_tpc_track_neg_recvertex_4_5_6")]

    for histName, inputHistName in names:
        # Assign the projection functions (and label for convenience)
        for label, projFunction in [("aSide", aSideProjectToXZ), ("cSide", cSideProjectToXZ)]:
            # For example, "hist1_aSide"
            histName = "{histName}_{label}".format(histName = histName, label = label)
            histCont = processingClasses.histogramContainer(histName = histName, histList = [inputHistName])
            histCont.projectionFunctionsToApply.append(projFunction)
            subsystem.histsAvailable[histName] = histCont

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

    return tempHist

# Helper for projectToXZ
def aSideProjectToXZ(subsystem, hist, processingOptions):
    return projectToXZ(subsystem, hist, processingOptions, aSide = True)

# Helper for projectToXZ
def cSideProjectToXZ(subsystem, hist, processingOptions):
    return projectToXZ(subsystem, hist, processingOptions, aSide = False)

def projectToXZ(subsystem, hist, processingOptions, aSide):
    if aSide == True:
        hist.hist.GetYaxis().SetRangeUser(15, 29)
    else:
        hist.hist.GetYaxis().SetRangeUser(0, 14)

    # Project to xz
    tempHist = hist.hist.Project3D("xz")
    tempHist.SetName("{0}_xz".format(hist.hist.GetName()))

    return tempHist
