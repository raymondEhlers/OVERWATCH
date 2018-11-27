from .alarm import Alarm


class checkLastNAlarms(Alarm):
    def __init__(self, minVal=0, maxVal=100, ratio=0.6, N=5, *args, **kwargs):
        super(IncreasingValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = ratio
        self.N = N

    def checkAlarm(self, trend):
        if len(trend.trendedValues) < self.N:
            return False
        trendedValues = trend[-self.N:]
        inBorderValues = [trendedValue for trendedValue in trendedValues if self.maxVal > trendedValue > self.minVal]
        if len(inBorderValues) >= self.ratio * self.N:
            return False

        alarm = "less than {} % values of last: {} values not in {} {}".format(self.ratio * 10, self.N, self.minVal,
                                                                               self.maxVal)
        self._announceAlarm(alarm)
        return True
