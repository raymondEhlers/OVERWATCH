#!/usr/bin/env python
""" Alarms aggregation class - will notify if any alarm appeared.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.aggregatingAlarm import AggregatingAlarm

try:
    from typing import List
except ImportError:
    # Imports in this block below here are used solely for typing information
    from overwatch.processing.alarms.alarm import Alarm  # noqa


class OrAlarm(AggregatingAlarm):
    def __init__(self, children, alarmText=''):  # type: (List[Alarm], str) -> None
        super(OrAlarm, self).__init__(children, alarmText=alarmText)

    def checkAlarm(self):
        alarms = [alarm for alarm, val in self.children.items() if val]
        result = len(alarms) > 0
        msg = ", ".join(a.alarmText for a in alarms)
        return result, msg
