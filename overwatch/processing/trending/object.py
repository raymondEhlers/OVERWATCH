import abc
import logging
import os
import sys

import ROOT
import numpy as np

import overwatch.processing.trending.constants as CON

# https://stackoverflow.com/questions/35673474/using-abc-abcmeta-in-a-way-it-is-compatible-both-with-python-2-7-and-python-3-5/41622155#41622155
from overwatch.processing.processingClasses import histogramContainer

if sys.version_info >= (3, 4):
    ABC = abc.ABC
else:
    ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

try:
    from typing import *
except ImportError:
    pass

logger = logging.getLogger(__name__)


# class TrendingObject(ABC):
class TrendingObject:

    def __init__(self, name, description, histogramNames, subsystemName, parameters):
        # type: (str, str, list, str, dict) -> None
        self.name = name
        self.desc = description
        self.histogramNames = histogramNames
        self.subsystemName = subsystemName
        self.parameters = parameters

        self.currentEntry = 0
        self.maxEntries = self.parameters.get(CON.ENTRIES, 50)
        self.trendedValues = self.initStartValues()

        self._histogram = None
        self.drawOptions = 'AP'  # Ensure that the axis and points are drawn on the TGraph

    def __str__(self):
        return self.name

    # @abc.abstractmethod
    def initStartValues(self):  # type: () -> Any
        return np.zeros((self.maxEntries, 2), dtype=np.float)

    @property
    def histogram(self):
        return self._histogram or self.retrieveHist()

    # @abc.abstractmethod
    def retrieveHist(self):
        # Define TGraph
        # TH1's need to be defined more carefully, as they seem to possible cause memory corruption
        # Multiply by 60.0 because it expects the times in seconds
        #  TODO multiply what? OK: in old TrendingObject was option SetTimeDisplay
        self._histogram = ROOT.TGraphErrors(self.maxEntries)
        self._histogram.SetName(self.name)
        self._histogram.GetXaxis().SetTimeDisplay(True)
        self._histogram.SetTitle(self.desc)

        for i in range(len(self.trendedValues)):
            self._histogram.SetPoint(i, i, self.trendedValues[i, 0])
            self._histogram.SetPointError(i, i, self.trendedValues[i, 1])

        return self._histogram

    def processHist(self, canvas):
        self.resetCanvas(canvas)
        canvas.cd()  # Ensure we plot onto the right canvas

        ROOT.gStyle.SetOptTitle(False)  # turn off title #TODO false vs 0?
        hist = self.histogram
        hist.SetMarkerStyle(ROOT.kFullCircle)
        hist.Draw(self.drawOptions)

        # Replace any slashes with underscores to ensure that it can be used safely as a filename
        outputNameWithoutExt = self.name.replace("/", "_") + '.{}'
        outputPath = os.path.join(self.parameters[CON.DIR_PREFIX], CON.TRENDING,
                                  self.subsystemName, '{}', outputNameWithoutExt)
        imgFile = outputPath.format(CON.IMAGE, self.parameters[CON.EXTENSION])
        jsonFile = outputPath.format(CON.JSON, 'json')

        logger.debug("Saving hist to {}".format(imgFile))
        canvas.SaveAs(imgFile)

        with open(jsonFile, "wb") as f:
            f.write(ROOT.TBufferJSON.ConvertToJSON(canvas).Data().encode())

    @staticmethod
    def resetCanvas(canvas):
        canvas.Clear()
        # Reset log status, since clear does not do this
        canvas.SetLogx(False)
        canvas.SetLogy(False)
        canvas.SetLogz(False)

    def addNewHistogram(self, hist):  # type: (histogramContainer) -> None
        if self.currentEntry > self.maxEntries:
            self.trendedValues = np.delete(self.trendedValues, 0, axis=0)
        else:
            self.currentEntry += 1

        newValue = self.getMeasurement(hist)
        self.trendedValues = np.append(self.trendedValues, [newValue], axis=0)

    @staticmethod
    def getMeasurement(hist):  # type: (histogramContainer) -> Any
        value = hist.hist.GetMean(), hist.hist.GetMeanError()
        return value
