#!/usr/bin/env python
""" Simple container of parameter for TrendingObject.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
import past.builtins

from overwatch.processing.alarms.alarm import Alarm
from overwatch.processing.trending.objects.object import TrendingObject

try:
    from typing import *  # noqa
except ImportError:
    pass

basestring = past.builtins.basestring


class TrendingInfoException(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __str__(self):
        return ', '.join('{}:{}'.format(k, v) for k, v in self.kwargs.items())


class TrendingInfo:
    """ Container for data for TrendingObject

    When TrendingInfo is initialized, data are validated.
    """

    __slots__ = ['name', 'desc', 'histogramNames', 'trendingClass', '_alarms']

    def __init__(self, name, desc, histogramNames, trendingClass):
        """
        Args:
            name (str): using in database to map name to trendingObject, must be unique
            desc (str): verbose description of trendingObject, it is displayed on generated histograms
            histogramNames (list): list of histogram names from which trendingObject depends
            trendingClass: concrete class of abstract class TrendingObject
        """
        # type: (str, str, List[str],  Type[TrendingObject]) -> None
        # trending objects within subsystem must have different names
        self.name = self._validate(name)
        self.desc = self._validate(desc)
        self.histogramNames = self._validateHist(histogramNames)
        self.trendingClass = self._validateTrendingClass(trendingClass)

        self._alarms = []

    def addAlarm(self, alarm):  # type: (Alarm) -> None
        if isinstance(alarm, Alarm):
            self._alarms.append(alarm)
        else:
            raise TrendingInfoException(msg='WrongAlarmType')

    def createTrendingClass(self, subsystemName, parameters):  # type: (str, dict) -> TrendingObject
        """Create instance of TrendingObject from previously set parameters
        Returns:
            TrendingObject: newly created object
        """
        trend = self.trendingClass(self.name, self.desc, self.histogramNames, subsystemName, parameters)
        trend.setAlarms(self._alarms)
        return trend

    @staticmethod
    def _validate(obj):  # type: (str) -> str
        if not isinstance(obj, basestring):
            raise TrendingInfoException(msg='WrongType', expected=basestring, got=type(obj))
        return obj

    @classmethod
    def _validateHist(cls, objects):  # type: (Collection[str]) -> Collection[str]
        try:
            if len(objects) < 1:
                raise TrendingInfoException(msg='NoHistograms')
        except TypeError:
            raise TrendingInfoException(msg='NotCollection', got=objects)

        for obj in objects:
            cls._validate(obj)
        return objects

    @staticmethod
    def _validateTrendingClass(cls):  # type: (Any) -> Type[TrendingObject]
        if not issubclass(cls, TrendingObject):
            raise TrendingInfoException(msg='WrongTrendingClass', expected=TrendingObject, got=cls)
        return cls
