#!/usr/bin/env python
""" Class for management of trends.

Prepare trending part of database, create trending objects,
notify appropriate objects about new histograms, manage processing trending histograms.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
.. code-author: Artur Wolak <>, AGH University of Science and Technology
"""
import logging
import os
from collections import defaultdict

import ROOT
from BTrees.OOBTree import BTree
from persistent import Persistent

import overwatch.processing.pluginManager as pluginManager
import overwatch.processing.trending.constants as CON

logger = logging.getLogger(__name__)

try:
    from typing import *  # noqa
except ImportError:
    pass
else:
    from persistent.mapping import PersistentMapping  # noqa
    from overwatch.processing.processingClasses import histogramContainer  # noqa
    from overwatch.processing.trending.info import TrendingInfo  # noqa
    from overwatch.processing.trending.objects.object import TrendingObject  # noqa


class TrendingManager(Persistent):
    """ADD DOC"""

    def __init__(self, dbRoot, parameters):  # type: (PersistentMapping, dict)->None
        self.parameters = parameters
        self.histToTrending = defaultdict(list)  # type: Dict[str, List[TrendingObject]]

        self._prepareDataBase(CON.TRENDING, dbRoot)
        self.trendingDB = dbRoot[CON.TRENDING]  # type: BTree[str, BTree[str, TrendingObject]]

        self._prepareDirStructure()

    def _prepareDirStructure(self):
        trendingDir = os.path.join(self.parameters[CON.DIR_PREFIX], CON.TRENDING, '{{subsystemName}}', '{type}')
        imgDir = trendingDir.format(type=CON.IMAGE)
        jsonDir = trendingDir.format(type=CON.JSON)

        for subsystemName in self.parameters[CON.SUBSYSTEMS]:
            subImgDir = imgDir.format(subsystemName=subsystemName)
            if not os.path.exists(subImgDir):
                os.makedirs(subImgDir)

            subJsonDir = jsonDir.format(subsystemName=subsystemName)
            if not os.path.exists(subJsonDir):
                os.makedirs(subJsonDir)

            self._prepareDataBase(subsystemName, self.trendingDB)

    @staticmethod
    def _prepareDataBase(objName, dbPosition):  # type: (str, Persistent)-> None
        if objName not in dbPosition:
            dbPosition[objName] = BTree()

    def createTrendingObjects(self):
        """ADD DOC"""
        for subsystem in self.parameters[CON.SUBSYSTEMS]:
            self._createTrendingObjectsForSubsystem(subsystem)

    def _createTrendingObjectsForSubsystem(self, subsystemName):  # type: (str) -> None
        functionName = "{subsystem}_getTrendingObjectInfo".format(subsystem=subsystemName)
        getTrendingObjectInfo = getattr(pluginManager, functionName, None)  # type: Callable[[], List[TrendingInfo]]
        if getTrendingObjectInfo:
            info = getTrendingObjectInfo()
            self._createTrendingObjectFromInfo(subsystemName, info)
        else:
            logger.info("Could not find {functionName}".format(functionName=functionName))

    def _createTrendingObjectFromInfo(self, subsystemName, infoList):
        # type: (str, List[TrendingInfo]) -> None
        success = "Trending object {name} from subsystem {subsystemName} added to the trending manager"
        fail = "Trending object {name} already exists in subsystem {subsystemName}"

        for info in infoList:
            if info.name not in self.trendingDB[subsystemName] or self.parameters[CON.RECREATE]:
                to = info.createTrendingClass(subsystemName, self.parameters)
                self.trendingDB[subsystemName][info.name] = to
                self._subscribe(to, info.histogramNames)

                logger.debug(success.format(name=info.name, subsystemName=subsystemName))
            else:
                logger.debug(fail.format(name=self.trendingDB[subsystemName][info.name], subsystemName=subsystemName))

    def _subscribe(self, trendingObject, histogramNames):  # type: (TrendingObject, List[str])->None
        for histName in histogramNames:
            self.histToTrending[histName].append(trendingObject)

    def resetDB(self):  # TODO not used - is it needed?
        self.trendingDB.clear()

    def processTrending(self):
        """ADD DOC"""
        # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
        canvasName = 'processTrendingCanvas'
        canvas = ROOT.TCanvas(canvasName, canvasName)

        for subsystemName, subsystem in self.trendingDB.items():  # type: (str, BTree[str, TrendingObject])
            logger.debug("subsystem: {subsystemName} is going to be trended".format(subsystemName=subsystemName))
            for name, trendingObject in subsystem.items():  # type: (str, TrendingObject)
                logger.debug("trendingObject: {trendingObject}".format(trendingObject=trendingObject))
                trendingObject.processHist(canvas)

    def notifyAboutNewHistogramValue(self, hist):  # type: (histogramContainer) -> None
        """ADD DOC"""
        for trend in self.histToTrending.get(hist.histName, []):
            trend.extractTrendValue(hist)
