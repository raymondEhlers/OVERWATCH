#!/usr/bin/env python

""" Fixtures for testing the trending subsystem.

"""

import ROOT
import pytest
import uuid

from overwatch.processing.trending.constants import EXTENSION, ENTRIES
from overwatch.processing.trending.objects.mean import MeanTrending

"""
All fixtures for trending have 'tf_' prefix
"""


@pytest.fixture
def tf_trendingArgs():
    parameters = {
        'test': True, ENTRIES: 20, EXTENSION: 'png',
    }
    yield ["name", "desc", ["h1", "h2"], 'TST', parameters]


@pytest.fixture
def tf_infoArgs():
    yield ["name", "desc", ["hist1", "hist2"], MeanTrending]


class Histogram(object):
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
def tf_histogram():
    yield Histogram()


@pytest.fixture
def tf_canvas():
    # Needs a random string so that ROOT doesn't complain about replacing the canvas.
    canvasName = 'testCanvas_{random}'.format(random = uuid.uuid4())
    return ROOT.TCanvas(canvasName, canvasName)
