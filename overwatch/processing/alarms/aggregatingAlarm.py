#!/usr/bin/env python
""" Base class for alarms which manage of aggregation alarms.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""

from overwatch.processing.alarms.alarm import Alarm

try:
    from typing import *  # noqa
except ImportError:
    pass


class AggregatingAlarm(Alarm):
    def __init__(self, children, alarmText=''):  # type: (List[Alarm], str) -> None
        super(AggregatingAlarm, self).__init__(alarmText=alarmText)

        # None - no value, True/False - last value returned from alarm
        self.children = {c: None for c in children}  # type: Dict[Alarm, Optional[bool]]

        for child in children:
            child.parent = self

    def addChild(self, child):  # type: (Alarm) -> None
        assert child.parent is None
        child.parent = self
        self.children[child] = None

    def isAllAlarmsCompleted(self):
        return all(c is not None for c in self.children.values())

    def checkAlarm(self, *args, **kwargs):  # type: () -> (bool, str)
        """abstract method"""
        raise NotImplementedError

    def childProcessed(self, child, result):
        if self.children[child] is not None:
            print("WARNING: last result ignored")

        self.children[child] = result

        if self.isAllAlarmsCompleted():
            self.processCheck()
            self.children = {c: None for c in self.children}
