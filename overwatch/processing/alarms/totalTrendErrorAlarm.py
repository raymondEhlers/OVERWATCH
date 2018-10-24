from .alarm import Alarm


class TotalTrendErrorAlarm(Alarm):

    def __init__(self, limit=1000, *args, **kwargs):
        super(TotalTrendErrorAlarm, self).__init__(*args, **kwargs)
        self.limit = limit

    def checkAlarm(self, trend):
        if sum(trend.trendedValues) < self.limit:
            return False

        self.announceAlarm(self.formatMessage(trend))
        return True
