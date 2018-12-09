#!/usr/bin/env python
""" Check if minimum ratio*N last N alarms are in range.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm


class CheckLastNAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, ratio=0.6, N=5, *args, **kwargs):
        super(CheckLastNAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = ratio
        self.N = N

    def checkAlarm(self, trend):
        if len(trend) < self.N:
            return False, ''

        trendedValues = trend[-self.N:]
        inBorderValues = [tv for tv in trendedValues if self.maxVal > tv > self.minVal]
        if len(inBorderValues) >= self.ratio * self.N:
            return False, ''

        msg = "(CheckLastNAlarm): less than {} % values of last {} trending values not in [{}, {}]".format(
            self.ratio * 10, self.N, self.minVal, self.maxVal)
        return True, msg
