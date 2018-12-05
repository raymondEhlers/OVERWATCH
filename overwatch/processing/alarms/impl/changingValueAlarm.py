#!/usr/bin/env python
""" TODO add desc.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class ChangingValueAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, ratio=2.0, *args, **kwargs):
        super(ChangingValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = ratio

    def checkAlarm(self, trend):
        if len(trend.trendedValues < 2):
            return False, ''
        prevValue = trend.trendedValues[-2]
        testedValue = trend.trendedValues[-1]

        if (testedValue > 0 and prevValue > 0 and
                (testedValue <= self.ratio * prevValue or
                 prevValue * self.ratio <= testedValue)):
            return False, ''
        if (testedValue < 0 and prevValue < 0 and
                (abs(prevValue) <= self.ratio * abs(testedValue) or
                 abs(testedValue) * self.ratio <= abs(prevValue))):
            return False, ''

        msg = "value: {}, prev: {}, change more than: {}".format(testedValue, prevValue, self.ratio)
        return True, msg
