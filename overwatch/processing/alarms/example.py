from overwatch.processing.alarms.collectors import workerMail, printCollector, httpCollector, MailSender
from overwatch.processing.alarms.impl.andAlarm import AndAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm


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

    borderError = BetweenValuesAlarm(minVal=0, maxVal=70, alarmText="ERROR")
    borderError.receivers = [workerMail, httpCollector]

    bva = BetweenValuesAlarm(minVal=0, maxVal=90, alarmText='BETWEEN')
    # TODO add second alarm to andAlarm
    seriousAlarm = AndAlarm([bva], "Serious Alarm")
    cernBoss = MailSender("boss@cern")
    seriousAlarm.addReceiver(cernBoss)

    return [boarderWarning, borderError, seriousAlarm]


def main():
    to = TrendingObjectMock(alarmConfig())

    values = [3, 14, 15, 92, 65, 35, 89, 79]
    for i, val in enumerate(values):
        print("\nVal number: {i} New value:{val}".format(i=i, val=val))
        to.addNewValue(val)


if __name__ == '__main__':
    main()
