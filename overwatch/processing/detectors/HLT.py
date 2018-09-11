""" HLT subsystem specific functions.

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

def generalHLTOptions(subsystem, hist, processingOptions):
    # Show HLT titles (by request from Mikolaj)
    if "EMC" not in hist.histName:
        ROOT.gStyle.SetOptTitle(1)

def findFunctionsForHLTHistogram(subsystem, hist):
    # General HLT Options
    hist.functionsToApply.append(generalHLTOptions)

from ..trendingClasses import createIfNotExist

def defineHLTTrendingObjects(trending, *args, **kwargs):
    names = [['hist_test', "test", ["fHistSPDclusters_SPDrawSize"]],
             ['TestHist', 'ttttt', ["fHistSSDclusters_SDDclusters"]]
             ]
    return createIfNotExist(trending, names)
