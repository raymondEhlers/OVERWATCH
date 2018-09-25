try:
    from typing import *
except ImportError:
    pass

from .object import TrendingObject


class TrendingInfo:
    __slots__ = ['name', 'desc', 'histogramNames', 'trendingClass']

    def __init__(self, name, desc, histogramNames, trendingClass):
        # type: (str, str, List[str],  Type[TrendingObject]) -> None
        self.name = name
        self.desc = desc
        self.histogramNames = histogramNames
        self.trendingClass = trendingClass

    def createTrendingClass(self, subsystemName, parameters):  # type: (str, dict) -> TrendingObject
        return self.trendingClass(self.name, self.desc, self.histogramNames, subsystemName, parameters)

