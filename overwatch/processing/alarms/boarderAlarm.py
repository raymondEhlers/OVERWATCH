from .alarm import Alarm


class BorderAlarm(Alarm):
    def __init__(self, minVal=0, maxVal=100, *args, **kwargs):
        super(BorderAlarm, self).__init__(*args, **kwargs)
        self.minVal = minVal
        self.maxVal = maxVal

    def checkAlarm(self, trend):
        testedValue = trend.trendedValues[-1]
        if self.minVal <= testedValue <= self.maxVal:
            return False

        alarm = "value: {} not in [{}, {}]".format(testedValue, self.minVal, self.maxVal)
        self.announceAlarm(self.formatMessage(trend, alarm))
        return True
