from .alarm import Alarm
import numpy as np


class IncreasingValueAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, *args, **kwargs):
        super(IncreasingValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = 0.6
        self.N = 5

    def checkAlarm(self, trend):
        trendingValues = trend[-self.N:]
        if (len(trendingValues) < self.N):
            return False
        notInBorderValues = [trendValue for trendValue in trendingValues if self.maxVal > trendingValues > self.minVal]
        if (len(notInBorderValues) > (1 - self.ratio) * self.N):
            return False

        alarm = "more than {} % values of last: {} values not in {} {}".format(self.ratio * 10, self.N, self.minVal,
                                                                               self.maxVal)
        self.announceAlarm(self.formatMessage(trend, alarm))
        return True
