from persistent.mapping import PersistentMapping
from persistent import Persistent
from BTrees.OOBTree import BTree
import os
import overwatch.processing.qa as qa
import logging
from .object import TrendingObject

logger = logging.getLogger(__name__)

try:
    from typing import *
    TrendingInfo = Tuple[str, str, List[str]]  # internal name, descriptive name, list of histograms
except ImportError:
    pass


class TrendingManager(Persistent):
    TRENDING = 'trending2'  # TODO remove '2' after migrate
    SUBSYSTEMS = 'subsystemList'
    DIR_PREFIX = 'dirPrefix'
    RECREATE = 'forceRecreateSubsystem'

    def __init__(self, dbRoot, parameters):  # type: (PersistentMapping, dict)->None
        self.subsystem = 'TDG'  # TODO what is this?
        self.parameters = parameters
        self.trendingObjects = None

        self.prepareDataBase(self.TRENDING, dbRoot)
        self.trendingDB = dbRoot[self.TRENDING]

        self.prepareDirStructure()
        self.createTrendingObjects()

    def prepareDirStructure(self):
        trendingDir = os.path.join(self.parameters[self.DIR_PREFIX], self.TRENDING)
        imgDir = os.path.join('{}s', 'img')
        jsonDir = os.path.join('{}s', 'json')

        for subsystemName in self.parameters[self.SUBSYSTEMS] + [self.subsystem]:
            subImgDir = os.path.join(trendingDir, imgDir.format(subsystemName))
            if not os.path.exists(subImgDir):
                os.makedirs(subImgDir)

            subJsonDir = os.path.join(trendingDir, jsonDir.format(subsystemName))
            if not os.path.exists(subJsonDir):
                os.makedirs(subJsonDir)

    @staticmethod
    def prepareDataBase(objName, dbPosition):  # type: (str, PersistentMapping)-> None
        if objName not in dbPosition:
            dbPosition[objName] = BTree()

    def createTrendingObjects(self):
        self.trendingObjects = {}
        for subsystem in self.parameters[self.SUBSYSTEMS] + [self.subsystem]:
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
            if name not in self.trendingDB[subsystemName] or self.parameters[self.RECREATE]:
                self.trendingDB[subsystemName][name] = TrendingObject(name, desc, histogramNames, self.parameters)
                logger.debug(success.format(name, subsystemName))
            else:
                logger.debug(fail.format(self.trendingObjects[subsystemName][name], name, subsystemName))
