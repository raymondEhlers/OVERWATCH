#!/usr/bin/env python
""" Check if new value is between (previous value)/ratio and (previous value)*ratio.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class RelativePreviousValueAlarm(Alarm):
    def __init__(self, ratio=2.0, *args, **kwargs):
        super(RelativePreviousValueAlarm, self).__init__(*args, **kwargs)
        assert ratio > 1
        self.ratio = ratio

    def checkAlarm(self, trend):
        if len(trend) < 2:
            return False, ''
        prevValue = trend[-2]
        curValue = trend[-1]

        if prevValue < 0:
            curValue = -curValue
        if abs(prevValue / self.ratio) <= curValue <= abs(prevValue * self.ratio):
            return False, ''

        msg = "(RelativePreviousValueAlarm): curValue: {curValue}, prevValue: {prevValue}, change more than: {ratio}".format(
            curValue=curValue, prevValue=prevValue, ratio=self.ratio)
        return True, msg
