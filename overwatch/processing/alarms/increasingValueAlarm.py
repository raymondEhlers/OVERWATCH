from .alarm import Alarm


class IncreasingValueAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, *args, **kwargs):
        super(IncreasingValueAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal
        self.ratio = 2.0

    def checkAlarm(self, trend):
        prevValue = trend.trendedValues[-2]
        testedValue = trend.trendedValues[-1]
        if testedValue <= self.ratio * prevValue:
            return False

        alarm = "value: {}, prev: {}, increase more than: {}".format(testedValue, prevValue, self.ratio)
        self.announceAlarm(self.formatMessage(trend, alarm))
        return True
