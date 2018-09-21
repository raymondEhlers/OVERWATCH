from persistent.mapping import PersistentMapping
from persistent import Persistent
from BTrees.OOBTree import BTree
import os
import overwatch.processing.qa as qa
from .object import TrendingObject
import overwatch.processing.trending.constants as CON
import ROOT

import logging

logger = logging.getLogger(__name__)

try:
    from typing import *

    TrendingInfo = Tuple[str, str, List[str]]  # internal name, descriptive name, list of histograms
except ImportError:
    pass


class TrendingManager(Persistent):

    def __init__(self, dbRoot, parameters):  # type: (PersistentMapping, dict)->None
        self.subsystem = 'TDG'  # TODO what is this?
        self.parameters = parameters
        self.trendingObjects = None

        self.prepareDataBase(CON.TRENDING, dbRoot)
        self.trendingDB = dbRoot[CON.TRENDING]  # type: BTree[str, BTree[str, TrendingObject]]

        self.prepareDirStructure()
        self.createTrendingObjects()

    def prepareDirStructure(self):
        trendingDir = os.path.join(self.parameters[CON.DIR_PREFIX], CON.TRENDING)
        imgDir = os.path.join('{}', CON.IMAGE)
        jsonDir = os.path.join('{}', CON.JSON)

        for subsystemName in self.parameters[CON.SUBSYSTEMS] + [self.subsystem]:
            subImgDir = os.path.join(trendingDir, imgDir.format(subsystemName))
            if not os.path.exists(subImgDir):
                os.makedirs(subImgDir)

            subJsonDir = os.path.join(trendingDir, jsonDir.format(subsystemName))
            if not os.path.exists(subJsonDir):
                os.makedirs(subJsonDir)

    @staticmethod
    def prepareDataBase(objName, dbPosition):  # type: (str, Persistent)-> None
        if objName not in dbPosition:
            dbPosition[objName] = BTree()

    def createTrendingObjects(self):
        self.trendingObjects = {}
        for subsystem in self.parameters[CON.SUBSYSTEMS] + [self.subsystem]:
            self._createTrendingObjectsForSubsystem(subsystem)

    def _createTrendingObjectsForSubsystem(self, subsystemName):  # type: (str) -> None
        functionName = "get{}TrendingObjectInfo".format(subsystemName)
        getTrendingObjectInfo = getattr(qa, functionName, None)  # type: Callable[[], TrendingInfo]
        if getTrendingObjectInfo:
            self.prepareDataBase(subsystemName, self.trendingDB)
            info = getTrendingObjectInfo()
            self._createTrendingObjectFromInfo(subsystemName, info)
        else:
            logger.info("Could not find {}".format(functionName))

    def _createTrendingObjectFromInfo(self, subsystemName, info):  # type: (str, TrendingInfo) -> None
        success = "Trending object {} from subsystem {} added to the trending manager"
        fail = "Trending object {} (name: {}) already exists in subsystem {}"

        for name, desc, histogramNames in info:
            if name not in self.trendingDB[subsystemName] or self.parameters[CON.RECREATE]:
                to = TrendingObject(name, desc, histogramNames, subsystemName, self.parameters)
                self.trendingDB[subsystemName][name] = to
                logger.debug(success.format(name, subsystemName))
            else:
                logger.debug(fail.format(self.trendingObjects[subsystemName][name], name, subsystemName))

    def resetDB(self):
        self.trendingDB.clear()

    def processTrending(self):
        # Cannot have same name as other canvases, otherwise the canvas will be replaced, leading to segfaults
        canvas = ROOT.TCanvas("processTrendingCanvas", "processTrendingCanvas")

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
