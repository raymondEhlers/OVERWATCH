
registeredAlarms = dict()


def getOrRegisterAlarm(alarmName, alarm):  # type: (str, 'Alarm') -> 'Alarm'
    """Register global alarm or return existing"""
    return registeredAlarms.setdefault(alarmName, alarm)
