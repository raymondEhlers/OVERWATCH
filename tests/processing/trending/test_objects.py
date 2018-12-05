#!/usr/bin/env python
""" Tests for example implementations of TrendingObject.

.. code-author: Pawel Ostrowski <ostr000@interia.pl>, AGH University of Science and Technology
"""
import pytest
import ROOT

import overwatch.processing.trending.objects as to


@pytest.mark.parametrize(
    "trendingClass",
    [to.MeanTrending, to.MaximumTrending, to.StdDevTrending],
    ids=['mean', 'maximum', 'stdDev']
)
def testExampleTrendingObjects(tf_trendingArgs, tf_histogram, trendingClass):
    t = trendingClass(*tf_trendingArgs)
    t.initializeTrendingArray()
    for i in range(50):
        t.extractTrendValue(tf_histogram)
    h = t.retrieveHist()
    assert isinstance(h, ROOT.TObject)
