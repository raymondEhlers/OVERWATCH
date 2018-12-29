#!/usr/bin/env python
""" Check if mean from N last measurements is in the range.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm
import numpy as np


class MeanInRangeAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, N=5, *args, **kwargs):
        super(MeanInRangeAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.N = N

    def checkAlarm(self, trend):
        if len(trend) < self.N:
            return False, ''

        trendedValues = trend[-self.N:]
        mean = np.mean(trendedValues)
        if self.minVal < np.mean(mean) < self.maxVal:
            return False, ''

        msg = "(MeanInRangeAlarm): mean of last {n} values not in [{min}, {max}]".format(
            n=self.N, min=self.minVal, max=self.maxVal)
        return True, msg
