#!/usr/bin/env python
""" TODO add desc.

.. code-author: Jacek Nabywaniec <>, AGH University of Science and Technology
"""
from overwatch.processing.alarms.alarm import Alarm
import numpy as np


class checkLastNValuesAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, N=5, *args, **kwargs):
        super(checkLastNValuesAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.N = N

    def checkAlarm(self, trend):
        if len(trend.trendedValues) < self.N:
            return False, ''
        trendedValues = np.array(trend.trendedValues)
        mean = np.mean(trendedValues)
        if self.minVal < np.mean(mean) < self.maxVal:
            return False, ''

        msg = "mean value of last: {} values not in {} {}".format(self.N, self.minVal, self.maxVal)
        return True, msg
