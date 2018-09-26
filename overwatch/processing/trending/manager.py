import logging
import os

import ROOT
from BTrees.OOBTree import BTree
from persistent import Persistent
from persistent.mapping import PersistentMapping

import overwatch.processing.qa as qa
import overwatch.processing.trending.constants as CON
from overwatch.processing.processingClasses import histogramContainer
from overwatch.processing.trending.info import TrendingInfo
from overwatch.processing.trending.object import TrendingObject

logger = logging.getLogger(__name__)

try:
    from typing import *
except ImportError:
    pass


class TrendingManager(Persistent):

    def __init__(self, dbRoot, parameters):  # type: (PersistentMapping, dict)->None
        self.parameters = parameters
        self.histToTrending = {}  # type: Dict[str, List[TrendingObject]]

        self.prepareDataBase(CON.TRENDING, dbRoot)
        self.trendingDB = dbRoot[CON.TRENDING]  # type: BTree[str, BTree[str, TrendingObject]]

        self.prepareDirStructure()

    def prepareDirStructure(self):
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

            self.prepareDataBase(subsystemName, self.trendingDB)

    @staticmethod
    def prepareDataBase(objName, dbPosition):  # type: (str, Persistent)-> None
        if objName not in dbPosition:
            dbPosition[objName] = BTree()

    def createTrendingObjects(self):
        for subsystem in self.parameters[CON.SUBSYSTEMS]:
            self._createTrendingObjectsForSubsystem(subsystem)

    def _createTrendingObjectsForSubsystem(self, subsystemName):  # type: (str) -> None
        functionName = "get{}TrendingObjectInfo".format(subsystemName)
        getTrendingObjectInfo = getattr(qa, functionName, None)  # type: Callable[[], List[TrendingInfo]]
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
                self.subscribe(to, info.histogramNames)

                logger.debug(success.format(info.name, subsystemName))
            else:
                logger.debug(fail.format(self.trendingDB[subsystemName][info.name], subsystemName))

    def subscribe(self, trendingObject, histogramNames):  # type: (TrendingObject, List[str])->None
        for histName in histogramNames:
            self.histToTrending.setdefault(histName, []).append(trendingObject)

    def resetDB(self):
        self.trendingDB.clear()

    def processTrending(self):
        # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
        canvasName = 'processTrendingCanvas2'  # TODO remove '2'
        canvas = ROOT.TCanvas(canvasName, canvasName)

        for subsystemName, subsystem in self.trendingDB.items():  # type: (str, BTree[str, TrendingObject])
            logger.debug("{}: subsystem from trending: {}".format(subsystemName, subsystem))
            for name, trendingObject in subsystem.items():  # type: (str, TrendingObject)
                logger.debug("trendingObject: {}".format(trendingObject))
                # self.printNonZeroValues(trendingObject.retrieveHistogram())
                trendingObject.processHist(canvas)

    @staticmethod
    def printNonZeroValues(hist):
        import ctypes
        x = ctypes.c_double(0.)
        y = ctypes.c_double(0.)
        nonzeroBins = []
        values = []
        for index in range(hist.hist.GetN()):
            hist.hist.GetPoint(index, x, y)
            values.append(y.value)
            if y.value > 0:
                nonzeroBins.append(index)
        logger.debug("nonzeroBins: {}".format(nonzeroBins))
        logger.debug("values: {}".format(values))

    def noticeAboutNewHistogram(self, hist):  # type: (histogramContainer) -> None
        try:
            trendingObjects = self.histToTrending[hist.histName]
        except KeyError:
            return
        else:
            for trend in trendingObjects:
                trend.addNewHistogram(hist)
