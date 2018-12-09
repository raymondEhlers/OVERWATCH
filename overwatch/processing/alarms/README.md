
# Alarms

This module is responsible for generating alarms and sending notifications about them.

Class Alarm has an abstract method `checkAlarm()`, which allows us to implement our own alarms.
Examples of alarms can be found in impl package.

Alarms can be aggregated by logic functions or/and.


## Displaying on the webApp
When histogram is processed and alarms are generated, they are displayed above this histogram on the webApp.

# Class Diagram
![Diagram](./doc/alarms_class_diag.png)

# Notifications

Each generated alarm is collected by AlarmCollector. It allows us send notifications about alarms when we want:
after processing trending object, after processing histogram or when all histograms are processed. You have to call
`announceAlarm()` method on alarmCollector object. AlarmCollector also groups alarms.

## Emails

There is possibility to send notifications about alarms via email. To send emails add to configuration file following information:

```yaml
# Email configuration for gmail
emailDelivery:
    smtpSettings:
      address: "smtp.gmail.com"
      port: 587
      userName: "email@address"
      password: "password"
    recipients:
      EMC:
        - "emcExpert1@mail"
        - "emcExpert2@mail"
      HLT:
        - "hltExpert1@mail"
        - "hltExpert2@mail"
      TPC:
        - "tpcExpert1@mail"
        - "tpcExpert2@mail"
```

## Slack

To send messages on Slack add to configuration file:

```yaml
# Slack token
apiToken: 'token'

# Slack channel
slackChannel: "test"
```

# Usage

To specify alarms and receivers write following function:

```python
def alarmConfig(recipients):

    mailSender = MailSender(recipients)
    slackSender = SlackNotification()
    boarderWarning = BetweenValuesAlarm(minVal=0, maxVal=50, alarmText="WARNING")

    boarderWarning.receivers = [printCollector]

    borderError = BetweenValuesAlarm(minVal=0, maxVal=70, alarmText="ERROR")
    borderError.receivers = [mailSender, slackSender]

    bva = BetweenValuesAlarm(minVal=0, maxVal=90, alarmText='BETWEEN')
    # TODO add second alarm to andAlarm
    seriousAlarm = AndAlarm([bva], "Serious Alarm")
    seriousAlarm.addReceiver(mailSender)

    return [boarderWarning, borderError, seriousAlarm]
```

And in manager.py in update `_createTrendingObjectFromInfo` method:

```python
for info in infoList:
    if info.name not in self.trendingDB[subsystemName] or self.parameters[CON.RECREATE]:
        to = info.createTrendingClass(subsystemName, self.parameters)
        to.setAlarms(alarmConfig(to.recipients))     # Update here
        self.trendingDB[subsystemName][info.name] = to
        self._subscribe(to, info.histogramNames)
```