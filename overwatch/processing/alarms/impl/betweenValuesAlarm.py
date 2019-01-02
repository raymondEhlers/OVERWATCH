#!/usr/bin/env python
""" Check if trend is between minimal and maximal allowed values.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class BetweenValuesAlarm(Alarm):
    def __init__(self, centerValue=50., maxDistance=50., minVal=None, maxVal=None, alarmText='', *args, **kwargs):
        super(BetweenValuesAlarm, self).__init__(alarmText=alarmText, *args, **kwargs)
        self.minVal = minVal if minVal is not None else centerValue - maxDistance
        self.maxVal = maxVal if maxVal is not None else centerValue + maxDistance

    def checkAlarm(self, trend):
        testedValue = trend[-1]
        if self.minVal <= testedValue <= self.maxVal:
            return False, ''

        msg = "(BetweenValuesAlarm): value {} not in [{}, {}]".format(testedValue, self.minVal, self.maxVal)
        return True, msg
