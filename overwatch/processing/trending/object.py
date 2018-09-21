import abc
import logging
import os
import sys

import ROOT
import numpy as np

import overwatch.processing.trending.constants as CON

# https://stackoverflow.com/questions/35673474/using-abc-abcmeta-in-a-way-it-is-compatible-both-with-python-2-7-and-python-3-5/41622155#41622155
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
        self.values = self.initStartValues()

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
        # Multiply by 60.0 because it expects the times in seconds # TODO multiply what?
        self._histogram = ROOT.TGraphErrors(self.maxEntries)
        self._histogram.SetName(self.name)
        self._histogram.SetTitle(self.desc)

        for i in range(len(self.values)):
            self._histogram.SetPoint(i, i, self.values[i, 0])
            self._histogram.SetPointError(i, i, self.values[i, 1])

        return self._histogram

    def processHist(self, canvas):
        self.resetCanvas(canvas)
        canvas.cd()  # Ensure we plot onto the right canvas

        ROOT.gStyle.SetOptTitle(False)  # turn off title #TODO false vs 0?
        hist = self.histogram
        hist.Draw(self.drawOptions)

        # Replace any slashes with underscores to ensure that it can be used safely as a filename
        outputName = self.name.replace("/", "_")
        outputName = "{}.{}".format(outputName, self.parameters[CON.EXTENSION])
        outputPath = os.path.join(self.parameters[CON.DIR_PREFIX], CON.TRENDING,
                                  self.subsystemName, '{}', outputName)
        imgFile = outputPath.format(CON.IMAGE)
        jsonFile = outputPath.format(CON.JSON)

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

    def fill(self, val):
        pass  # TODO implement
