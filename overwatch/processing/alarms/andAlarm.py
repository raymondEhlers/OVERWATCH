from .alarm import Alarm

try:
    from typing import *  # noqa
except ImportError:
    pass


class AndAlarm(Alarm):
    def __init__(self, alarmText='', *children):  # type: (str, *Alarm) -> None
        super(AndAlarm, self).__init__(alarmText=alarmText)
        self.children = [] if not children else children

    def checkAlarm(self, trend):
        for child in self.children:
            if not child.checkAlarm(trend):
                return False

        return True
