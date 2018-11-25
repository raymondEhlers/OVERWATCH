try:
    from typing import *  # noqa
except ImportError:
    pass
else:
    from ..trending.objects.object import TrendingObject  # noqa


class Alarm:
    def __init__(self, alarmText=''):
        self.alarmText = alarmText
        self.receivers = []

    def addReceiver(self, receiver):  # type: (callable) -> None
        self.receivers.append(receiver)

    def checkAlarm(self, trend):  # type: (TrendingObject) -> bool
        """abstract method"""
        raise NotImplementedError

    def _announceAlarm(self, msg):  # type: (str) -> None
        msg = "[{alarmText}]: {msg}".format(alarmText=self.alarmText, msg=msg)
        for receiver in self.receivers:
            receiver(msg)
