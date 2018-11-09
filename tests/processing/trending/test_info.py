import pytest

from overwatch.processing.trending.info import TrendingInfoException, TrendingInfo
from overwatch.processing.trending.objects.object import TrendingObject


def testValidData(tf_infoArgs):
    to = TrendingInfo(*tf_infoArgs)
    assert isinstance(to.createTrendingClass('TST', {}), TrendingObject)


def testWrongTypeName(tf_infoArgs):
    tf_infoArgs[0] = 3.14
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testWrongTypeDesc(tf_infoArgs):
    tf_infoArgs[1] = 42
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testValidCollectionType(tf_infoArgs):
    tf_infoArgs[2] = ("foo", "bar")
    to = TrendingInfo(*tf_infoArgs)
    assert isinstance(to.createTrendingClass('TST', {}), TrendingObject)


def testWrongCollectionType(tf_infoArgs):
    tf_infoArgs[2] = 42
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testWrongTypeInCollection(tf_infoArgs):
    tf_infoArgs[2] = ["foo", 1]
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testNoHistograms(tf_infoArgs):
    tf_infoArgs[2] = []
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testWrongClass(tf_infoArgs):
    tf_infoArgs[3] = TrendingInfo
    with pytest.raises(TrendingInfoException):
        TrendingInfo(*tf_infoArgs)


def testWrongAbstractClass(tf_infoArgs):
    tf_infoArgs[3] = TrendingObject
    tInfo = TrendingInfo(*tf_infoArgs)

    with pytest.raises(NotImplementedError):
        tInfo.createTrendingClass('TST', {})


def testMissingFunctions(tf_infoArgs, tf_histogram):
    TrendingObject.initializeTrendingArray = lambda self: None
    tf_infoArgs[3] = TrendingObject
    tInfo = TrendingInfo(*tf_infoArgs)
    to = tInfo.createTrendingClass('TST', {})

    with pytest.raises(NotImplementedError):
        to.extractTrendValue(tf_histogram)

    with pytest.raises(NotImplementedError):
        to.retrieveHist()


def testExceptionDesc(tf_infoArgs):
    tf_infoArgs[1] = 42
    try:
        TrendingInfo(*tf_infoArgs)
    except TrendingInfoException as ex:
        assert 'WrongType' in str(ex)


def testTrendingObjectName(tf_infoArgs):
    testName = "Test Name 123"
    tf_infoArgs[0] = testName
    tInfo = TrendingInfo(*tf_infoArgs)
    to = tInfo.createTrendingClass('TST', {})
    assert str(to) == testName
