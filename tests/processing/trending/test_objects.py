import pytest
import ROOT

import overwatch.processing.trending.objects as to


@pytest.mark.parametrize(
    "trendingClass",
    [to.MeanTrending, to.MaximumTrending, to.StdDevTrending],
    ids=['mean', 'maximum', 'stdDev']
)
def testExampleTrendingObjects(trendingArgs, histogram, trendingClass):
    t = trendingClass(*trendingArgs)
    t.initializeTrendingArray()
    for i in range(50):
        t.extractTrendValue(histogram)
    h = t.retrieveHist()
    assert isinstance(h, ROOT.TObject)
