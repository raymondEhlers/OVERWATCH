try:
    from typing import *
except ImportError:
    pass

from overwatch.processing.trending.objects.object import TrendingObject
import past.builtins

basestring = past.builtins.basestring


class TrendingInfoException(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __str__(self):
        return ', '.join('{}:{}'.format(k, v) for k, v in self.kwargs.items())


class TrendingInfo:
    __slots__ = ['name', 'desc', 'histogramNames', 'trendingClass']

    def __init__(self, name, desc, histogramNames, trendingClass):
        # type: (str, str, List[str],  Type[TrendingObject]) -> None
        self.name = self.validate(name)
        self.desc = self.validate(desc)
        self.histogramNames = self.validateHist(histogramNames)
        self.trendingClass = self.validateTrendingClass(trendingClass)

    def createTrendingClass(self, subsystemName, parameters):  # type: (str, dict) -> TrendingObject
        return self.trendingClass(self.name, self.desc, self.histogramNames, subsystemName, parameters)

    @staticmethod
    def validate(obj):  # type: (str) -> str
        if not isinstance(obj, basestring):
            raise TrendingInfoException(msg='WrongType', expected=basestring, got=type(obj))
        return obj

    @staticmethod
    def validateHist(objects):  # type: (Collection[str]) -> Collection[str]
        try:
            if len(objects) < 1:
                raise TrendingInfoException(msg='NoHistograms')
        except TypeError:
            raise TrendingInfoException(msg='NotCollection', got=objects)

        for obj in objects:
            TrendingInfo.validate(obj)
        return objects

    @staticmethod
    def validateTrendingClass(cls):  # type: (Any) -> Type[TrendingObject]
        if not issubclass(cls, TrendingObject):
            raise TrendingInfoException(msg='WrongTrendingClass', expected=TrendingObject, got=cls)
        return cls
