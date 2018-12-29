#!/usr/bin/env python
""" Tests for alarm implementations.
.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
.. code-author: Jacek Nabywaniec <jacek.nabywaniec@gmail.com>, AGH University of Science and Technology
"""
import pytest

from overwatch.processing.alarms.impl.absolutePreviousValueAlarm import AbsolutePreviousValueAlarm
from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm
from overwatch.processing.alarms.impl.checkLastNAlarm import CheckLastNAlarm
from overwatch.processing.alarms.impl.meanInRangeAlarm import MeanInRangeAlarm
from overwatch.processing.alarms.impl.relativePreviousValueAlarm import RelativePreviousValueAlarm


@pytest.mark.parametrize('alarm', [
    BetweenValuesAlarm(centerValue=50., maxDistance=50.),
    BetweenValuesAlarm(minVal=0., maxVal=100.),
])
def testBetweenValuesAlarm(af_alarmChecker, af_trendingObjectClass, alarm):
    alarm.addReceiver(af_alarmChecker.receiver)
    to = af_trendingObjectClass()
    to.alarms = [alarm]

    def test(val, isAlarm=False):
        af_alarmChecker.addValueAndCheck(to, val, isAlarm)

    test(3)
    test(-10, True)
    test(17)
    test(0)
    test(105, True)
    test(100)
    test(44)
    test(-1, True)
    test(101, True)


def testRelativePreviousValueAlarm(af_alarmChecker, af_trendingObjectClass):
    alarm = RelativePreviousValueAlarm(ratio=2.)
    alarm.addReceiver(af_alarmChecker.receiver)
    to = af_trendingObjectClass()
    to.alarms = [alarm]

    def test(val, isAlarm=False):
        af_alarmChecker.addValueAndCheck(to, val, isAlarm)

    test(6)
    test(7)
    test(14)
    test(7)
    test(15, True)
    test(16)
    test(7, True)
    test(0.1, True)
    test(0, True)
    test(-0.1, True)
    test(2, True)
    test(-2, True)
    test(-1)
    test(-2)
    test(-4)
    test(-1, True)
    test(-3, True)
    test(-6)


def testAbsolutePreviousValueAlarm(af_alarmChecker, af_trendingObjectClass):
    alarm = AbsolutePreviousValueAlarm(maxDelta=3.)
    alarm.addReceiver(af_alarmChecker.receiver)
    to = af_trendingObjectClass()
    to.alarms = [alarm]

    def test(val, isAlarm=False):
        af_alarmChecker.addValueAndCheck(to, val, isAlarm)

    test(34)
    test(33)
    test(35)
    test(32)
    test(36, True)
    test(30, True)
    test(29)
    test(10, True)
    test(9)
    test(15, True)
    test(0, True)
    test(-1)
    test(1)
    test(0)
    test(-17, True)
    test(-15)
    test(-9, True)


def testMeanInRangeAlarm(af_alarmChecker, af_trendingObjectClass):
    alarm = MeanInRangeAlarm(minVal=0, maxVal=10)
    alarm.addReceiver(af_alarmChecker.receiver)
    to = af_trendingObjectClass()
    to.alarms = [alarm]

    def test(val, isAlarm=False):
        af_alarmChecker.addValueAndCheck(to, val, isAlarm)

    test(10)
    test(3)
    test(-1)
    test(2)
    test(5)
    test(30)
    test(20, True)
    test(1, True)
    test(-10)
    test(100, True)
    test(0, True)
    test(0, True)
    test(-10, True)
    test(-2, True)
    test(20)


def testCheckLastNAlarm(af_alarmChecker, af_trendingObjectClass):
    alarm = CheckLastNAlarm(minVal=0, maxVal=10, ratio=0.6)
    alarm.addReceiver(af_alarmChecker.receiver)
    to = af_trendingObjectClass()
    to.alarms = [alarm]

    def test(val, isAlarm=False):
        af_alarmChecker.addValueAndCheck(to, val, isAlarm)

    test(10)
    test(8)
    test(4)
    test(2)
    test(-20)
    test(-10)
    test(12, True)
    test(1, True)
    test(1, True)
    test(2)
    test(0)
    test(-2)
    test(-4, True)
    test(10, True)
