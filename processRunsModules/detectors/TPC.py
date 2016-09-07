""" TPC subsystem specific functions.

This currently serves as a catch all for unsorted histograms. No additional QA functions are applied.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

import ROOT

######################################################################################################
######################################################################################################
# QA Functions
######################################################################################################
######################################################################################################

def generalTPCOptions(subsystem, hist):
    # Show TPC titles (by request from Mikolaj)
    if "EMC" not in hist.histName:
        ROOT.gStyle.SetOptTitle(1)

def findFunctionsForTPCHistogram(subsystem, hist):
    # General TPC Options
    hist.functionsToApply.append(generalTPCOptions)

def createEMCHistogramGroups(subsystem):
    # Sort the filenames of the histograms into catagories for better presentation
    # The order in which these are added is the order in which they are processed!    

    subsystem.histGroups.append(processingClasses.histogramGroupContainer("clust", "clust"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("constrain", "constrain"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("event_6", "event_6"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("event_recvertex", "event_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("match_trackingeff", "match_trackingeff"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("all_recvertex", "all_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("neg_recvertex", "neg_recvertex"))
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("pos_recvertex", "pos_recvertex"))

    # Catch all of the other hists
    subsystem.histGroups.append(processingClasses.histogramGroupContainer("Non TPC", ""))

################################################### 
