#!/usr/bin/env python
""" Alarms aggregation class - will notify if all alarms appeared.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.aggregatingAlarm import AggregatingAlarm
try:
    from typing import *  # noqa
except ImportError:
    # Imports in this block below here are used solely for typing information
    from overwatch.processing.alarms.alarm import Alarm   # noqa


class AndAlarm(AggregatingAlarm):
    def __init__(self, children, alarmText=''):  # type: (list[Alarm], str) -> None
        super(AndAlarm, self).__init__(children, alarmText=alarmText)

    def checkAlarm(self):
        alarms = [alarm for alarm, val in self.children.items() if val]
        result = len(alarms) == len(self.children)
        msg = ", ".join(a.alarmText for a in alarms)
        return result, msg
