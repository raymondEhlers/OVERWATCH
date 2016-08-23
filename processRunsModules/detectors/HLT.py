""" HLT subsystem specific functions.

This currently serves as a catch all for unsorted histograms. No additional QA functions are applied.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
.. codeauthor:: James Mulligan <james.mulligan@yale.edu>, Yale University

"""

######################################################################################################
######################################################################################################
# QA Functions
######################################################################################################
######################################################################################################

###################################################
def setHLTDrawOptions(hist, qaContainer):
    # Show HLT titles (by request from Mikolaj)
    if "EMC" not in hist.GetName():
        gStyle.SetOptTitle(1)
