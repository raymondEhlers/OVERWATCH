import ROOT
import pytest

from overwatch.processing.trending.constants import EXTENSION, ENTRIES
from overwatch.processing.trending.objects.mean import MeanTrending


@pytest.fixture
def trendingArgs():
    parameters = {
        'test': True, ENTRIES: 20, EXTENSION: 'png',
    }
    yield ["name", "desc", ["h1", "h2"], 'TST', parameters]


@pytest.fixture
def infoArgs():
    yield ["name", "desc", ["hist1", "hist2"], MeanTrending]


class Histogram:
    functionNames = [
        'GetMaximum',
        'GetMean',
        'GetMeanError',
        'GetStdDev',
        'GetStdDevError',
    ]

    def __getattr__(self, item):
        num = self.functionNames.index(item)
        return lambda: num

    @property
    def hist(self):
        return self


@pytest.fixture
def histogram():
    yield Histogram()


@pytest.fixture
def canvas():
    canvasName = 'testCanvas'
    return ROOT.TCanvas(canvasName, canvasName)
