import ROOT

# General includes
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Used for sorting and generating html
from . import processingClasses


##################
# Trending Classes
##################
class TrendingObjectMean(processingClasses.trendingObject):
    def __init__(self, trendingHistName, trendingHistTitle, histNames, nEntries=50):
        super(TrendingObjectMean, self).__init__(trendingName=trendingHistName, prettyTrendingName=trendingHistTitle,
                                                 nEntries=nEntries, trendingHist=None, histNames=histNames)

    def retrieveHist(self):
        super(TrendingObjectMean, self).retrieveHist()

        # Set the histogrma to display a time axis
        self.hist.hist.GetXaxis().SetTimeDisplay(1)
        # self.trendingHist.GetXaxis().SetTimeFormat()

        # Make it more visible
        self.hist.hist.SetMarkerStyle(ROOT.kFullCircle)

        print("self.hist: {}, self.hist.hist: {}".format(self.hist, self.hist.hist))

    def fill(self, hist, _error=None):
        if len(self.histNames) > 1:
            print("Too many histograms passed to {0}!".format(self.histNames))
            return

        print("Filling hist {}, histNames: {}".format(self.hist, self.histNames))
        fillVal = 0
        fillValError = 0
        # for histName in self.histNames:
        #    hist = hists[histName]
        # Could do something more complicated here, but we really only want the one value
        fillVal += hist.hist.GetMean()
        fillValError += hist.hist.GetMeanError()

        print("Filling value: {}, error: {}".format(fillVal, fillValError))
        super(TrendingObjectMean, self).fill(fillVal, fillValError)


def createIfNotExist(trending, names):
    for name, title, histNames in names:
        # Create it if it doesn't exist
        if not name in trending.keys():
            # Define new trending histogram

            trending[name] = TrendingObjectMean(name, title, histNames)

    return trending
