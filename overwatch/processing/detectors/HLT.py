#/usr/bin/env python

""" HLT subsystem specific functions.

These functions apply to histograms received specifically through the HLT subsystem receiver
(ie. not every single histogram that is sent from the HLT to the various subsystem receivers).

This currently serves as a catch all for unsorted histograms. No processing functions are applied
beyond basic modification of the presentation.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University
"""

import ROOT

def generalHLTOptions(subsystem, hist, processingOptions, **kwargs):
    """ Specify general HLT histogram options.

    Args:
        subsystem (subsystemContainer): The subsystem being processed.
        hist (histogramContainer): The histogram being processed.
        processingOptions (dict): Implemented by the subsystem to note options used during standard
            processing. Keys are names of options, while values are the corresponding option values.
        **kwargs (dict): Reserved for future arguments.
    Returns:
        None
    """
    # Show HLT titles (as requested by Mikolaj)
    # NOTE: Titles are always shown by jsRoot, so this option is only relevant for png images.
    ROOT.gStyle.SetOptTitle(1)

def findFunctionsForHLTHistogram(subsystem, hist, **kwargs):
    """ Determine which processing functions to apply to which HLT histograms.

    Functions should be added to the ``histogramContainer.functionsToApply`` list. This allows those
    functions to applied repeatedly without having to perform the lookup each time a run is processed.

    Args:
        subsystem (subsystemContainer): The subsystem being processed.
        hist (histogramContainer): The histogram being processed.
        **kwargs (dict): Reserved for future arguments.
    Returns:
        None
    """
    # General HLT display options
    hist.functionsToApply.append(generalHLTOptions)


from ..trendingClasses import createIfNotExist

def defineHLTTrendingObjects(trending, *args, **kwargs):
    names = [['hist_test', "test", ["fHistSPDclusters_SPDrawSize"]],
             ['TestHist', 'ttttt', ["fHistSSDclusters_SDDclusters"]]
             ]
    return createIfNotExist(trending, names)
