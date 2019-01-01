from overwatch.processing.alarms.registrator import registeredAlarms, getOrRegisterAlarm
from overwatch.processing.alarms.alarm import Alarm


def test_register():
    assert len(registeredAlarms) == 0
    alarmName = 'register test'

    alarm1 = getOrRegisterAlarm(alarmName, Alarm(alarmText=alarmName))
    assert len(registeredAlarms) == 1

    getOrRegisterAlarm('other alarm', Alarm(alarmText=alarmName))
    assert len(registeredAlarms) == 2

    alarm2 = getOrRegisterAlarm(alarmName, Alarm(alarmText=alarmName))
    assert len(registeredAlarms) == 2
    assert alarm1 is alarm2
