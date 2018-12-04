#!/usr/bin/env python
""" Tests for alarm implementations.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
import pytest

from overwatch.processing.alarms.impl.betweenValuesAlarm import BetweenValuesAlarm


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

# TODO test more class
