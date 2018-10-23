import pytest
import ROOT
from overwatch.processing.trending.objects.object import TrendingObject
from overwatch.processing.trending.constants import *


class CounterTrendingObject(TrendingObject):
    def __init__(self, *args, **kwargs):
        super(CounterTrendingObject, self).__init__(*args, **kwargs)
        self._counter = 0

    def initializeTrendingArray(self):
        return []

    def extractTrendValue(self, hist):
        self.trendedValues.append(self._counter)
        self._counter += 1

    def retrieveHist(self):
        h = ROOT.TH1C("test", "title", 20, 1, 10)

        for i, val in enumerate(self.trendedValues):
            h.Fill(i, val)
        return h


class TestHistogramSaving(object):

    @pytest.fixture(autouse=True)
    def _prepare(self, tmpdir, trendingArgs):
        ROOT.gROOT.SetBatch(True)
        subsystem = trendingArgs[3]
        tmpdir.mkdir(TRENDING)
        tmpdir.mkdir(TRENDING, subsystem)
        self.img = tmpdir.mkdir(TRENDING, subsystem, IMAGE)
        self.json = tmpdir.mkdir(TRENDING, subsystem, JSON)

        self.args = trendingArgs
        self.args[4][DIR_PREFIX] = tmpdir.strpath

    @pytest.mark.parametrize("elem", [10, 50, 120])
    def testHistogramSaving(self, canvas, histogram, elem):
        to = CounterTrendingObject(*self.args)
        for i in range(elem):
            to.extractTrendValue(histogram)
        to.processHist(canvas)

        name = self.args[0].replace("/", "_")
        extension = self.args[4][EXTENSION]
        img = self.img.join("{name}.{ext}".format(name=name, ext=extension))
        json = self.json.join("{name}.{ext}".format(name=name, ext=JSON))

        # check if files exist
        assert img.check(file=True)
        assert json.check(file=True)
