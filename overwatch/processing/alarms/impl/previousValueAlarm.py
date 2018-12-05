#!/usr/bin/env python
""" Check if last value is different more than ratio*previous value.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class PreviousValueAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, ratio=2.0, *args, **kwargs):
        super(PreviousValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = ratio

    def checkAlarm(self, trend):
        if len(trend) < 2:
            return False, ''
        prevValue = trend[-2]
        curValue = trend[-1]

        if (curValue > 0 and prevValue > 0 and
                (curValue <= self.ratio * prevValue or
                 prevValue * self.ratio <= curValue)):
            return False, ''
        if (curValue < 0 and prevValue < 0 and
                (abs(prevValue) <= self.ratio * abs(curValue) or
                 abs(curValue) * self.ratio <= abs(prevValue))):
            return False, ''

        msg = "value: {}, prev: {}, change more than: {}".format(curValue, prevValue, self.ratio)
        return True, msg
