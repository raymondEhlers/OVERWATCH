#!/usr/bin/env python

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
import overwatch.processing.trending.objects as trendingObjects
from overwatch.processing.alarms.example import alarmStdConfig, alarmMaxConfig, alarmMeanConfig

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
        ("ClusterChargeMax", "TPC Cluster ChargeMax", ["fHistClusterChargeMax"]),
        ("ClusterChargeTot", "TPC Cluster ChargeTotal", ["fHistClusterChargeTot"]),
        ("HLTInSize_HLTOutSize", "HLT Out Size vs HLT In Size", ["fHistHLTInSize_HLTOutSize"]),
        ("HLTSize_HLTInOutRatio", "HLT Out/In Size Ratio vs HLT Input Size", ["fHistHLTSize_HLTInOutRatio"]),
        ("SDDclusters_SDDrawSize", "SDD clusters vs SDD raw size", ["fHistSDDclusters_SDDrawSize"]),
        ("SPDclusters_SDDclusters", "SDD clusters vs SPD clusters", ["fHistSPDclusters_SDDclusters"]),
        ("SPDclusters_SPDrawSize", "SPD clusters vs SPD raw size", ["fHistSPDclusters_SPDrawSize"]),
        ("SPDclusters_SSDclusters", "SSD clusters vs SPD clusters", ["fHistSPDclusters_SSDclusters"]),
        ("SSDclusters_SDDclusters", "SDD clusters vs SSD clusters", ["fHistSSDclusters_SDDclusters"]),
        ("SSDclusters_SSDrawSize", "SSD clusters vs SSD raw size", ["fHistSSDclusters_SSDrawSize"]),
        ("TPCAallClustersRowPhi", "TPCA clusters all, raw cluster coordinates", ["fHistTPCAallClustersRowPhi"]),
        ("TPCAattachedClustersRowPhi", "TPCA clusters attached to tracks, raw cluster coordinates",
         ["fHistTPCAattachedClustersRowPhi"]),
        ("TPCCallClustersRowPhi", "TPCC clusters all, raw cluster coordinates", ["fHistTPCCallClustersRowPhi"]),
        ("TPCCattachedClustersRowPhi", "TPCC clusters attached to tracks, raw cluster coordinates",
         ["fHistTPCCattachedClustersRowPhi"]),
        ("TPCClusterFlags", "TPC Cluster Flags", ["fHistTPCClusterFlags"]),
        ("TPCClusterSize_TPCCompressedSize", "TPC compressed size vs TPC HWCF Size",
         ["fHistTPCClusterSize_TPCCompressedSize"]),
        ("TPCHLTclusters_TPCCompressionRatio", "Huffman compression ratio vs TPC HLT clusters",
         ["fHistTPCHLTclusters_TPCCompressionRatio"]),
        ("TPCHLTclusters_TPCFullCompressionRatio", "Full compression ratio vs TPC HLT clusters",
         ["fHistTPCHLTclusters_TPCFullCompressionRatio"]),
        ("TPCHLTclusters_TPCSplitClusterRatioPad", "TPC Split Cluster ratio pad vs TPC HLT clusters",
         ["fHistTPCHLTclusters_TPCSplitClusterRatioPad"]),
        ("TPCHLTclusters_TPCSplitClusterRatioTime", "TPC Split Cluster ratio time vs TPC HLT clusters",
         ["fHistTPCHLTclusters_TPCSplitClusterRatioTime"]),
        ("TPCRawSize_TPCCompressedSize", "TPC compressed size vs TPC Raw Size", ["fHistTPCRawSize_TPCCompressedSize"]),
        ("TPCTrackPt", "TPC Track Pt", ["fHistTPCTrackPt"]),
        ("TPCdEdxMaxIROC", "TPC dE/dx v.s. P (qMax, IROC)", ["fHistTPCdEdxMaxIROC"]),
        ("TPCdEdxMaxOROC1", "TPC dE/dx v.s. P (qMax, OROC1)", ["fHistTPCdEdxMaxOROC1"]),
        ("TPCdEdxMaxOROC2", "TPC dE/dx v.s. P (qMax, OROC2)", ["fHistTPCdEdxMaxOROC2"]),
        ("TPCdEdxMaxOROCAll", "TPC dE/dx v.s. P (qMax, OROC all)", ["fHistTPCdEdxMaxOROCAll"]),
        ("TPCdEdxMaxTPCAll", "TPC dE/dx v.s. P (qMax, full TPC)", ["fHistTPCdEdxMaxTPCAll"]),
        ("TPCdEdxTotIROC", "TPC dE/dx v.s. P (qTot, IROC)", ["fHistTPCdEdxTotIROC"]),
        ("TPCdEdxTotOROC1", "TPC dE/dx v.s. P (qTot, OROC1)", ["fHistTPCdEdxTotOROC1"]),
        ("TPCdEdxTotOROC2", "TPC dE/dx v.s. P (qTot, OROC2)", ["fHistTPCdEdxTotOROC2"]),
        ("TPCdEdxTotOROCAll", "TPC dE/dx v.s. P (qTot, OROC all)", ["fHistTPCdEdxTotOROCAll"]),
        ("TPCdEdxTotTPCAll", "TPC dE/dx v.s. P (qTot, full TPC)", ["fHistTPCdEdxTotTPCAll"]),
        ("TPCtracks_TPCtracklets", "TPC Tracks vs TPC Tracklets", ["fHistTPCtracks_TPCtracklets"]),
        ("TZERO_ITSSPDVertexZ", "TZERO interaction time vs ITS vertex z", ["fHistTZERO_ITSSPDVertexZ"]),
        ("VZERO_SPDClusters", "SPD Clusters vs VZERO Trigger Charge (A+C)", ["fHistVZERO_SPDClusters"]),
        ("ZNA_VZEROTrigChargeA", "ZNA vs. VZERO Trigger Charge A", ["fHistZNA_VZEROTrigChargeA"]),
        ("ZNC_VZEROTrigChargeC", "ZNC vs. VZERO Trigger Charge C", ["fHistZNC_VZEROTrigChargeC"]),
        ("ZNT_VZEROTrigChargeT", "ZN (A+C) vs. VZERO Trigger Charge (A+C)", ["fHistZNT_VZEROTrigChargeT"]),
    ]
    trendingNameToObject = {
        "max": trendingObjects.MaximumTrending,
        "mean": trendingObjects.MeanTrending,
        "stdDev": trendingObjects.StdDevTrending,
    }
    alarms = {
        "max": alarmMaxConfig(),
        "mean": alarmMeanConfig(),
        "stdDev": alarmStdConfig()
    }
    trendingInfo = []
    for prefix, cls in trendingNameToObject.items():
        for name, desc, histograms in infoList:
            ti = TrendingInfo(prefix + name, prefix + ": " + desc, histograms, cls)
            if prefix in alarms:
                ti.addAlarm(alarms[prefix])
            trendingInfo.append(ti)
    return trendingInfo
