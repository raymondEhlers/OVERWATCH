from overwatch.processing.alarms.collectors import printCollector, MailSender, SlackNotification
from overwatch.processing.alarms.impl.andAlarm import AndAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm
from overwatch.processing.alarms.impl.checkLastNAlarm import CheckLastNAlarm
from overwatch.processing.alarms.impl.meanInRangeAlarm import MeanInRangeAlarm



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


def alarmConfig(recipients):
    mailSender = MailSender(recipients)
    slackSender = SlackNotification()
    borderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")

    borderWarning.receivers = [printCollector]

    borderError = BetweenValuesAlarm(minVal=0, maxVal=70, alarmText="ERROR")
    borderError.receivers = [mailSender, slackSender]

    bva = BetweenValuesAlarm(minVal=0, maxVal=90, alarmText='BETWEEN')
    # TODO add second alarm to andAlarm
    seriousAlarm = AndAlarm([bva], "Serious Alarm")
    seriousAlarm.addReceiver(mailSender)

    return [borderWarning, borderError, seriousAlarm]

def alarmMeanConfig():
    slack = SlackNotification()
    lastAlarm = CheckLastNAlarm(alarmText="ERROR")
    lastAlarm.receivers = [printCollector, slack]

    return [lastAlarm]

def alarmStdConfig():
    slack = SlackNotification()
    meanInRangeWarning = MeanInRangeAlarm(alarmText="WARNING")
    meanInRangeWarning.receivers = [printCollector, slack]

    return [meanInRangeWarning]

def alarmMaxConfig(recipients):
    mailSender = MailSender(recipients)
    borderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")
    borderWarning.receivers = [printCollector, mailSender]

    return [borderWarning]

def main():
    recipients = ["test1@mail", "test2@mail"]
    to = TrendingObjectMock(alarmConfig(recipients))

    values = [3, 14, 15, 92, 65, 35, 89, 79]
    for i, val in enumerate(values):
        print("\nVal number: {i} New value:{val}".format(i=i, val=val))
        to.addNewValue(val)


if __name__ == '__main__':
    main()
