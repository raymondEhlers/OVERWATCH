.. processRuns documentation master file, created by
   sphinx-quickstart on Fri Jan 22 14:38:46 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to OVERWATCH documentation!
=======================================

ALICE **OVERWATCH**: Online Visualization of Emerging tRends and Web Accessible deTector Conditions using the HLT.

This project provides real time detector monitoring, as well as basic QA, using histograms received from the HLT.
It is a very powerful tool for detecting issues (for example, noise in an EMCal Trigger Readout Unit) and checking
data quality in real time (for example, seeing the evolution of a noisy channel both over runs and within a run).

Please see the README_ for information about the project, and how to use it.

.. _README: README.html

Process Runs
============

The main processing function, taking ROOT files from the HLT viewer and organzing them into run
directory and subsystem structure, then writes out histograms to webpage  

.. toctree::
   :maxdepth: 2

   processRuns

Modules
-------

These powerful modules provide much of the processing functionality for Process Runs. They also
provide a number of helper functions for detectors specific processing.

.. toctree::
   :maxdepth: 2

   processRunsModules

Detector Modules
----------------

These modules provide detector specific functionality, allowing organization of histograms, as
well as functions to check QA, among many other possible features.

.. toctree::
   :maxdepth: 2

   processRunsModules.detectors

Web App
=======

The web app provides interactive access to the processing cabilities and output from Process Runs.
It can work both through WSGI, as well as a standalone server.

.. toctree::
   :maxdepth: 2

   webApp

Modules
-------

These modules provide support functions for the Web App, including authentication and validation
of inputs for safe operation.

.. toctree::
   :maxdepth: 2

   webAppModules

Configuration
=============

Provides convenient configuration for both Process Runs and the Web App.

.. toctree::
   :maxdepth: 2

   config

Testing Tools
=============

These tools allow convenient testing of the various components of this project, including providing
a full server stack to test the WSGI capbilities of the Web App. More tools will be added as they
are developed.

.. toctree::
   :maxdepth: 2

   fullStackServer

---------------------

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

