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
from overwatch.processing.trending.info import TrendingInfo
from overwatch.processing.trending.objects import maximum, mean, stdDev

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


def getEMCTrendingObjectInfo():
    infoList = [
        ('fHistClusterChargeMax', 'TPC Cluster ChargeMax'),
        ('fHistClusterChargeTot', 'TPC Cluster ChargeTotal'),
        ('fHistHLTInSize_HLTOutSize', 'HLT Out Size vs HLT In Size'),
        ('fHistHLTSize_HLTInOutRatio', 'HLT Out/In Size Ratio vs HLT Input Size'),
        ('fHistSDDclusters_SDDrawSize', 'SDD clusters vs SDD raw size'),
        ('fHistSPDclusters_SDDclusters', 'SDD clusters vs SPD clusters'),
        ('fHistSPDclusters_SPDrawSize', 'SPD clusters vs SPD raw size'),
        ('fHistSPDclusters_SSDclusters', 'SSD clusters vs SPD clusters'),
        ('fHistSSDclusters_SDDclusters', 'SDD clusters vs SSD clusters'),
        ('fHistSSDclusters_SSDrawSize', 'SSD clusters vs SSD raw size'),
        ('fHistTPCAallClustersRowPhi', 'TPCA clusters all, raw cluster coordinates'),
        ('fHistTPCAattachedClustersRowPhi', 'TPCA clusters attached to tracks, raw cluster coordinates'),
        ('fHistTPCCallClustersRowPhi', 'TPCC clusters all, raw cluster coordinates'),
        ('fHistTPCCattachedClustersRowPhi', 'TPCC clusters attached to tracks, raw cluster coordinates'),
        ('fHistTPCClusterFlags', 'TPC Cluster Flags'),
        ('fHistTPCClusterSize_TPCCompressedSize', 'TPC compressed size vs TPC HWCF Size'),
        ('fHistTPCHLTclusters_TPCCompressionRatio', 'Huffman compression ratio vs TPC HLT clusters'),
        ('fHistTPCHLTclusters_TPCFullCompressionRatio', 'Full compression ratio vs TPC HLT clusters'),
        ('fHistTPCHLTclusters_TPCSplitClusterRatioPad', 'TPC Split Cluster ratio pad vs TPC HLT clusters'),
        ('fHistTPCHLTclusters_TPCSplitClusterRatioTime', 'TPC Split Cluster ratio time vs TPC HLT clusters'),
        ('fHistTPCRawSize_TPCCompressedSize', 'TPC compressed size vs TPC Raw Size'),
        ('fHistTPCTrackPt', 'TPC Track Pt'),
        ('fHistTPCdEdxMaxIROC', 'TPC dE/dx v.s. P (qMax, IROC)'),
        ('fHistTPCdEdxMaxOROC1', 'TPC dE/dx v.s. P (qMax, OROC1)'),
        ('fHistTPCdEdxMaxOROC2', 'TPC dE/dx v.s. P (qMax, OROC2)'),
        ('fHistTPCdEdxMaxOROCAll', 'TPC dE/dx v.s. P (qMax, OROC all)'),
        ('fHistTPCdEdxMaxTPCAll', 'TPC dE/dx v.s. P (qMax, full TPC)'),
        ('fHistTPCdEdxTotIROC', 'TPC dE/dx v.s. P (qTot, IROC)'),
        ('fHistTPCdEdxTotOROC1', 'TPC dE/dx v.s. P (qTot, OROC1)'),
        ('fHistTPCdEdxTotOROC2', 'TPC dE/dx v.s. P (qTot, OROC2)'),
        ('fHistTPCdEdxTotOROCAll', 'TPC dE/dx v.s. P (qTot, OROC all)'),
        ('fHistTPCdEdxTotTPCAll', 'TPC dE/dx v.s. P (qTot, full TPC)'),
        ('fHistTPCtracks_TPCtracklets', 'TPC Tracks vs TPC Tracklets'),
        ('fHistTZERO_ITSSPDVertexZ', 'TZERO interaction time vs ITS vertex z'),
        ('fHistVZERO_SPDClusters', 'SPD Clusters vs VZERO Trigger Charge (A+C)'),
        ('fHistZNA_VZEROTrigChargeA', 'ZNA vs. VZERO Trigger Charge A'),
        ('fHistZNC_VZEROTrigChargeC', 'ZNC vs. VZERO Trigger Charge C'),
        ('fHistZNT_VZEROTrigChargeT', 'ZN (A+C) vs. VZERO Trigger Charge (A+C)'),
    ]
    trendingInfo = []
    prefixes = ('max', 'mean', 'stdDev')
    for cls, prefix in zip((maximum.MaximumTrending, mean.MeanTrending, stdDev.StdDevTrending), prefixes):
        for dependingFile, desc in infoList:
            trendingInfo.append(TrendingInfo(prefix + dependingFile, desc, [dependingFile], cls))
    return trendingInfo
