from overwatch.processing.alarms.collectors import printCollector, MailSender, SlackNotification
from overwatch.processing.alarms.impl.andAlarm import AndAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm
from overwatch.processing.alarms.impl.checkLastNAlarm import CheckLastNAlarm
from overwatch.processing.alarms.impl.meanInRangeAlarm import MeanInRangeAlarm


class TrendingObjectMock:
    def __init__(self, alarms):
        self.alarms = alarms
        self.trendedValues = []
        self.alarmsMessages = []

    def addNewValue(self, val):
        self.trendedValues.append(val)
        self.checkAlarms()

    def checkAlarms(self):
        for alarm in self.alarms:
            alarm.processCheck(self)

    def __str__(self):
        return self.__class__.__name__


def alarmConfig():
    # recipients = ["test1@mail", "test2@mail"]
    # mailSender = MailSender(recipients)
    # slackSender = SlackNotification()

    # for example purpose:
    def mailSender(x):
        printCollector("MAIL:" + x)

    def slackSender(x):
        printCollector("Slack: " + x)

    borderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")
    borderWarning.receivers = [printCollector]

    borderError = BetweenValuesAlarm(minVal=0, maxVal=70, alarmText="ERROR")
    borderError.receivers = [mailSender, slackSender]

    bva = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="BETWEEN")
    clna = CheckLastNAlarm(minVal=0, maxVal=70, ratio=0.6, N=3, alarmText="LastN")
    seriousAlarm = AndAlarm([bva, clna], "Serious Alarm")
    seriousAlarm.addReceiver(mailSender)

    return [borderWarning, borderError, bva, clna]


def alarmMeanConfig():
    slack = SlackNotification()
    recipients = ["test@mail"]
    mailSender = MailSender(recipients)
    lastAlarm = CheckLastNAlarm(alarmText="ERROR")
    lastAlarm.receivers = [printCollector, slack, mailSender]

    borderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")
    borderWarning.receivers = [printCollector, mailSender]

    return [lastAlarm, borderWarning]


def alarmStdConfig():
    slack = SlackNotification()
    meanInRangeWarning = MeanInRangeAlarm(alarmText="WARNING", collector=True)
    meanInRangeWarning.receivers = [printCollector, slack]

    return [meanInRangeWarning]


def alarmMaxConfig():
    recipients = ["test@mail"]
    mailSender = MailSender(recipients)
    borderError = BetweenValuesAlarm(minVal=0, maxVal=300, alarmText="ERROR", collector=True)
    borderError.receivers = [printCollector, mailSender]

    return [borderError]


def main():
    to = TrendingObjectMock(alarmConfig())

    values = [3, 14, 15, 92, 65, 35, 89, 79]
    for i, val in enumerate(values):
        print("\nVal number: {i} New value:{val}".format(i=i, val=val))
        to.addNewValue(val)


if __name__ == '__main__':
    main()
