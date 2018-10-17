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
        trendingDir = os.path.join(self.parameters[CON.DIR_PREFIX], CON.TRENDING, '{}', '{}')
        imgDir = trendingDir.format('{}', CON.IMAGE)
        jsonDir = trendingDir.format('{}', CON.JSON)

        for subsystemName in self.parameters[CON.SUBSYSTEMS]:
            subImgDir = imgDir.format(subsystemName)
            if not os.path.exists(subImgDir):
                os.makedirs(subImgDir)

            subJsonDir = jsonDir.format(subsystemName)
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
            logger.info("Could not find {}".format(functionName))

    def _createTrendingObjectFromInfo(self, subsystemName, infoList):
        # type: (str, List[TrendingInfo]) -> None
        success = "Trending object {} from subsystem {} added to the trending manager"
        fail = "Trending object {} already exists in subsystem {}"

        for info in infoList:
            if info.name not in self.trendingDB[subsystemName] or self.parameters[CON.RECREATE]:
                to = info.createTrendingClass(subsystemName, self.parameters)
                self.trendingDB[subsystemName][info.name] = to
                self._subscribe(to, info.histogramNames)

                logger.debug(success.format(info.name, subsystemName))
            else:
                logger.debug(fail.format(self.trendingDB[subsystemName][info.name], subsystemName))

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
            logger.debug("subsystem: {} is going to be trended".format(subsystemName))
            for name, trendingObject in subsystem.items():  # type: (str, TrendingObject)
                logger.debug("trendingObject: {}".format(trendingObject))
                trendingObject.processHist(canvas)

    def notifyAboutNewHistogramValue(self, hist):  # type: (histogramContainer) -> None
        """ADD DOC"""
        for trend in self.histToTrending.get(hist.histName, []):
            trend.extractTrendValue(hist)
