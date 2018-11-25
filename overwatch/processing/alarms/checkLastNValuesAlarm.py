from .alarm import Alarm
import numpy as np


class IncreasingValueAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, *args, **kwargs):
        super(IncreasingValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.N = 5

    def checkAlarm(self, trend):
        trendingValues = trend[-self.N:]
        if len(trendingValues) < self.N:
            return False
        mean = np.mean(trendingValues)
        if self.minVal < np.mean(mean) < self.maxVal:
            return False

        alarm = "value of last: {} values not in {} {}".format(mean, self.minVal, self.maxVal)
        self._announceAlarm(alarm)
        return True
