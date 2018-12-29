#!/usr/bin/env python
""" Check if (new value - old value) is different more than delta.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class AbsolutePreviousValueAlarm(Alarm):
    def __init__(self, maxDelta=1, *args, **kwargs):
        super(AbsolutePreviousValueAlarm, self).__init__(*args, **kwargs)
        self.maxDelta = maxDelta

    def checkAlarm(self, trend):
        if len(trend) < 2:
            return False, ''
        prevValue = trend[-2]
        curValue = trend[-1]

        delta = abs(prevValue - curValue)
        if delta <= self.maxDelta:
            return False, ''

        msg = "(AbsolutePreviousValueAlarm): curValue: {curValue}, prevValue: {prevValue}, change more than: {maxDelta}".format(
            curValue=curValue, prevValue=prevValue, maxDelta=self.maxDelta)
        return True, msg
