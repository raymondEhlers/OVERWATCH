import pytest

from overwatch.processing.trending.info import TrendingInfoException, TrendingInfo
from overwatch.processing.trending.objects.object import TrendingObject


def testValidData(infoArgs):
    to = TrendingInfo(*infoArgs)
    assert isinstance(to.createTrendingClass('TST', {}), TrendingObject)


def testWrongTypeName(infoArgs):
    infoArgs[0] = 3.14
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testWrongTypeDesc(infoArgs):
    infoArgs[1] = 42
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testValidCollectionType(infoArgs):
    infoArgs[2] = ("foo", "bar")
    to = TrendingInfo(*infoArgs)
    assert isinstance(to.createTrendingClass('TST', {}), TrendingObject)


def testWrongCollectionType(infoArgs):
    infoArgs[2] = 42
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testWrongTypeInCollection(infoArgs):
    infoArgs[2] = ["foo", 1]
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testNoHistograms(infoArgs):
    infoArgs[2] = []
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testWrongClass(infoArgs):
    infoArgs[3] = TrendingInfo
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*infoArgs)


def testWrongAbstractClass(infoArgs):
    infoArgs[3] = TrendingObject
    tInfo = TrendingInfo(*infoArgs)

    with pytest.raises(NotImplementedError):
        tInfo.createTrendingClass('TST', {})


def testMissingFunctions(infoArgs, histogram):
    TrendingObject.initializeTrendingArray = lambda self: None
    infoArgs[3] = TrendingObject
    tInfo = TrendingInfo(*infoArgs)
    to = tInfo.createTrendingClass('TST', {})

    with pytest.raises(NotImplementedError):
        to.extractTrendValue(histogram)

    with pytest.raises(NotImplementedError):
        to.retrieveHist()


def testExceptionDesc(infoArgs):
    infoArgs[1] = 42
    try:
        TrendingInfo(*infoArgs)
    except TrendingInfoException as ex:
        assert 'WrongType' in str(ex)


def testTrendingObjectName(infoArgs):
    testName = "Test Name 123"
    infoArgs[0] = testName
    tInfo = TrendingInfo(*infoArgs)
    to = tInfo.createTrendingClass('TST', {})
    assert str(to) == testName
