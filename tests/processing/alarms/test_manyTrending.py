#!/usr/bin/env python
""" Tests for N trending object to N alarms.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""

from overwatch.processing.alarms.impl.andAlarm import AndAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm
from overwatch.processing.alarms.impl.orAlarm import OrAlarm
try:
    from typing import *  # noqa
except ImportError:
    # Imports in this block below here are used solely for typing information
    from tests.unit.fixtures.alarmFixtures import TrendingObjectMock  # noqa


def testManyTrendingObjectToOneAlarm(af_alarmChecker, af_trendingObjectClass):
    tc1 = af_trendingObjectClass('tc1')  # type: TrendingObjectMock
    tc2 = af_trendingObjectClass('tc2')  # type: TrendingObjectMock

    ba1 = BetweenValuesAlarm(minVal=10, maxVal=30, alarmText='ba1')
    ba2 = BetweenValuesAlarm(minVal=40, maxVal=50, alarmText='ba2')
    andAlarm = AndAlarm([ba1, ba2], 'andAlarm')
    andAlarm.addReceiver(af_alarmChecker.receiver)

    tc1.alarms = [ba1]
    tc2.alarms = [ba2]

    af_alarmChecker.addValueAndCheck(tc1, 1, False)
    af_alarmChecker.addValueAndCheck(tc2, 2, True)

    af_alarmChecker.addValueAndCheck(tc1, 3)
    af_alarmChecker.addValueAndCheck(tc2, 45)

    af_alarmChecker.addValueAndCheck(tc1, 25)
    af_alarmChecker.addValueAndCheck(tc2, 4)

    af_alarmChecker.addValueAndCheck(tc1, 26)
    af_alarmChecker.addValueAndCheck(tc2, 46)

    af_alarmChecker.addValueAndCheck(tc1, 100, False)
    af_alarmChecker.addValueAndCheck(tc2, 200, True)

    af_alarmChecker.addValueAndCheck(tc2, 300, False)
    af_alarmChecker.addValueAndCheck(tc1, 400, True)


def testOneTrendingObjectToManyAlarm(af_alarmChecker, af_trendingObjectClass):
    warning = BetweenValuesAlarm(minVal=30, maxVal=40, alarmText='error')
    warning.addReceiver(af_alarmChecker.receiver)
    error = BetweenValuesAlarm(minVal=20, maxVal=50, alarmText='warning')
    error.addReceiver(af_alarmChecker.receiver)

    to = af_trendingObjectClass('to')  # type: TrendingObjectMock
    to.alarms = [error, warning]

    af_alarmChecker.addValueAndCheck(to, 35)
    af_alarmChecker.addValueAndCheck(to, 30)
    af_alarmChecker.addValueAndCheck(to, 40)

    af_alarmChecker.addValueAndCheck(to, 25, 1)
    af_alarmChecker.addValueAndCheck(to, 45, 1)

    af_alarmChecker.addValueAndCheck(to, 15, 2)
    af_alarmChecker.addValueAndCheck(to, 55, 2)


def testManyTrendingObjectToManyAlarm(af_alarmChecker, af_trendingObjectClass):
    error1 = BetweenValuesAlarm(minVal=20, maxVal=50, alarmText='errorTO1')
    error2 = BetweenValuesAlarm(minVal=20, maxVal=50, alarmText='errorTO2')

    warning1 = BetweenValuesAlarm(minVal=30, maxVal=40, alarmText='warningTO1')
    warning2 = BetweenValuesAlarm(minVal=30, maxVal=40, alarmText='warningTO1')

    tc1 = af_trendingObjectClass('tc1')  # type: TrendingObjectMock
    tc1.alarms = [error1, warning1]
    tc2 = af_trendingObjectClass('tc2')  # type: TrendingObjectMock
    tc2.alarms = [error2, warning2]

    # alarm will be if any of errors appear or all warnings
    andAlarm = AndAlarm([warning1, warning2], alarmText='AndWarning')
    orAlarm = OrAlarm([error1, error2], alarmText='OrError')
    rootAlarm = OrAlarm([andAlarm, orAlarm], alarmText='RootAlarm')
    rootAlarm.addReceiver(af_alarmChecker.receiver)

    def check(val1, val2, isAlarm=False):
        af_alarmChecker.addValueAndCheck(tc1, val1)
        af_alarmChecker.addValueAndCheck(tc2, val2, isAlarm)

        # it doesn't matter which trending object will be first
        af_alarmChecker.addValueAndCheck(tc2, val2)
        af_alarmChecker.addValueAndCheck(tc1, val1, isAlarm)

    check(35, 36, False)  # all in range
    check(41, 30, False)  # 1 warning
    check(42, 29, True)  # 2 warnings
    check(53, 35, True)  # 1 error (1 warning)
    check(17, 45, True)  # 1 error (2 warning)
    check(54, 18, True)  # 2 errors (2 warnings)
