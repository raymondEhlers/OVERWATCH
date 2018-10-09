import numpy as np
import ROOT

from overwatch.processing.trending.objects.object import TrendingObject


class StdDevTrending(TrendingObject):
    def initStartValues(self):
        return np.zeros((self.maxEntries, 2), dtype=np.float)

    def retrieveHist(self):
        histogram = ROOT.TGraphErrors(self.maxEntries)
        histogram.SetName(self.name)
        histogram.GetXaxis().SetTimeDisplay(True)
        histogram.SetTitle(self.desc)
        histogram.SetMarkerStyle(ROOT.kFullCircle)

        for i in range(len(self.trendedValues)):
            histogram.SetPoint(i, i, self.trendedValues[i, 0])
            histogram.SetPointError(i, i, self.trendedValues[i, 1])

        return histogram

    def addNewHistogram(self, hist):
        if self.currentEntry > self.maxEntries:
            self.trendedValues = np.delete(self.trendedValues, 0, axis=0)
        else:
            self.currentEntry += 1

        newValue = hist.hist.GetStdDev(), hist.hist.GetStdDevError()
        self.trendedValues = np.append(self.trendedValues, [newValue], axis=0)
