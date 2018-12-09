from overwatch.processing.alarms.collectors import printCollector, httpCollector, MailSender
from overwatch.processing.alarms.impl.andAlarm import AndAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm
from overwatch.processing.alarms.impl.checkLastNAlarm import CheckLastNAlarm


class TrendingObjectMock:
    def __init__(self, alarms):
        self.alarms = alarms
        self.trendedValues = []

    def addNewValue(self, val):
        self.trendedValues.append(val)
        self.checkAlarms()

    def checkAlarms(self):
        for alarm in self.alarms:
            alarm.checkAlarm(self)

    def __str__(self):
        return self.__class__.__name__


def alarmConfig():
    boarderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")
    boarderWarning.addReceiver(printCollector)

    lastAlarm = CheckLastNAlarm(alarmText="ERROR")
    lastAlarm.addReceiver(printCollector)

    return [boarderWarning, lastAlarm]


def main():
    to = TrendingObjectMock(alarmConfig())

    values = [3, 14, 15, 92, 65, 35, 89, 79]
    for i, val in enumerate(values):
        print("\nVal number: {i} New value:{val}".format(i=i, val=val))
        to.addNewValue(val)


if __name__ == '__main__':
    main()
