#!/usr/bin/env python
""" Fixtures for alarms.

All fixtures for alarms have 'af_' prefix

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""

try:
    from typing import *  # noqa
except ImportError:
    pass

import pytest


class TrendingObjectMock:
    def __init__(self, name=''):
        self.name = name
        self.alarms = []
        self.trendedValues = []
        self.alarmsMessages = []

    def addNewValue(self, val):
        self.trendedValues.append(val)
        self.checkAlarms()

    def checkAlarms(self):
        for alarm in self.alarms:
            alarm.processCheck(self)


@pytest.fixture
def af_trendingObjectClass():
    yield TrendingObjectMock


class AlarmChecker(object):
    def __init__(self):
        self.receivedAlarms = []
        self.counter = 0

    def receiver(self, msg):  # type: (str) -> None
        self.receivedAlarms.append(msg)

    def addValueAndCheck(self, trendingObject, value, isAlarm=False):
        # type: ('to', float, Union[bool, int])->None
        trendingObject.addNewValue(value)
        if isinstance(isAlarm, bool):
            self.counter += 1 if isAlarm else 0
        else:
            self.counter += isAlarm
        assert len(self.receivedAlarms) == self.counter


@pytest.fixture
def af_alarmChecker():
    yield AlarmChecker()
