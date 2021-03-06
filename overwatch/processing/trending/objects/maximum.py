#!/usr/bin/env python
""" Trending object to extract the maximum value of a histogram.

.. codeauthor:: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology

"""

import numpy as np
import ROOT

from overwatch.processing.trending.objects.object import TrendingObject


class MaximumTrending(TrendingObject):
    def initializeTrendingArray(self):
        return np.zeros(0, dtype=np.float)

    def extractTrendValue(self, hist):
        if self.currentEntry > self.maxEntries:
            self.trendedValues = np.delete(self.trendedValues, 0)
        else:
            self.currentEntry += 1

        newValue = hist.hist.GetMaximum()
        self.trendedValues = np.append(self.trendedValues, newValue)

    def retrieveHist(self):
        histogram = ROOT.TGraphErrors(self.maxEntries)
        histogram.SetName(self.name)
        histogram.GetXaxis().SetTimeDisplay(True)
        histogram.SetTitle(self.desc)
        histogram.SetMarkerStyle(ROOT.kFullCircle)

        for i in range(len(self.trendedValues)):
            histogram.SetPoint(i, i, self.trendedValues[i])
            histogram.SetPointError(i, 0, 0)

        return histogram
