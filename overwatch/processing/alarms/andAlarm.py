from .alarm import Alarm

try:
    from typing import *  # noqa
except ImportError:
    pass


class AndAlarm(Alarm):
    def __init__(self, children=None, *args, **kwargs):  # type: (List[Alarm]) -> None
        super(AndAlarm, self).__init__(*args, **kwargs)
        self.children = [] if not children else children

    def checkAlarm(self, trend):
        for child in self.children:
            if not child.checkAlarm(trend):
                return False

        self.announceAlarm(self.formatMessage(trend))
        return True
