#!/usr/bin/env python
""" Example trending object with mean values.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
import numpy as np
import ROOT

from overwatch.processing.trending.objects.object import TrendingObject


class MeanTrending(TrendingObject):
    def initializeTrendingArray(self):
        return np.zeros((0, 2), dtype=np.float)

    def extractTrendValue(self, hist):
        if self.currentEntry > self.maxEntries:
            self.trendedValues = np.delete(self.trendedValues, 0, axis=0)
        else:
            self.currentEntry += 1

        newValue = hist.hist.GetMean(), hist.hist.GetMeanError()
        self.trendedValues = np.append(self.trendedValues, [newValue], axis=0)

    def retrieveHist(self):
        histogram = ROOT.TGraphErrors(self.maxEntries)
        histogram.SetName(self.name)
        histogram.GetXaxis().SetTimeDisplay(True)
        histogram.SetTitle(self.desc)
        histogram.SetMarkerStyle(ROOT.kFullCircle)

        for i in range(len(self.trendedValues)):
            histogram.SetPoint(i, i, self.trendedValues[i, 0])
            histogram.SetPointError(i, 0, self.trendedValues[i, 1])

        return histogram
