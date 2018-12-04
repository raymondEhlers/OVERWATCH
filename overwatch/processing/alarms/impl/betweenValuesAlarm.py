#!/usr/bin/env python
""" Check if trend is between minimal and maximal allowed values.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class BetweenValuesAlarm(Alarm):
    def __init__(self, centerValue=50., maxDistance=50., minVal=None, maxVal=None, alarmText=''):
        super(BetweenValuesAlarm, self).__init__(alarmText=alarmText)
        self.minVal = minVal if minVal is not None else centerValue - maxDistance
        self.maxVal = maxVal if maxVal is not None else centerValue + maxDistance

    def checkAlarm(self, trend):
        testedValue = trend.trendedValues[-1]
        if self.minVal <= testedValue <= self.maxVal:
            return False, ''

        msg = "value: {} not in [{}, {}]".format(testedValue, self.minVal, self.maxVal)
        return True, msg
