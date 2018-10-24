try:
    from typing import *  # noqa
except ImportError:
    pass
else:
    from ..trending.objects.object import TrendingObject  # noqa


class Alarm:
    def __init__(self, *args, alarmText='', **kwargs):
        self.alarmText = alarmText
        self.receivers = []

    def addReceiver(self, receiver):  # type: (callable) -> None
        self.receivers.append(receiver)

    def checkAlarm(self, trend):  # type: (TrendingObject) -> bool
        """abstract method"""
        raise NotImplementedError

    def announceAlarm(self, msg):
        for receiver in self.receivers:
            receiver(msg)

    def formatMessage(self, trend='', msg=''):  # type: (TrendingObject) -> str
        return "{alarmText} {trend} {msg}".format(
            alarmText=self.alarmText, trend=trend, msg=msg)
