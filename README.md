# ALICE OVERWATCH

**OVERWATCH**: **O**nline **V**isualization of **E**merging t**R**ends and **W**eb **A**ccessible de**T**ector **C**onditions using the **H**LT.

Welcome to OVERWATCH, an online monitoring framework utilizing detector histograms provided by the HLT. The OVERWATCH framework processes these histograms and displays them minute-by-minute on this website; this allows for real-time monitoring of detector performance, effortlessly available to any ALICE member at any location. For example, a collaborator in the US can monitor the EMCal trigger patch ADC spectrum for noisy TRUs in the comfort of daylight hours, while the CERN-based detector expert sleeps.

The framework also features the ability to automate QA functions to identify detector performance problems, as well as the ability to examine detector behavior during user-specified time ranges within a run. Moreover, the framework provides long-term trending info, i.e. the ability to plot detector quantities as a function of run number. OVERWATCH complements the DQM framework, allowing remote monitoring and easily implementable user customization. We provide extensive documentation for any detector system to be easily added to OVERWATCH, and encourage more subsystems to take advantage of the framework. For more information, [see below](#adding-a-detector).

If you accessed this page via the _Web App_ and want to return back, either use the back button or <a href="javascript:history.back()">click here</a>.

## Introduction

This project utilizes data from the HLT. Histograms are received and should be saved out at a fixed time interval (outside of the scope of this project). _Process Runs_  will move, classify, and process the files. This includes printing the histograms, and transferring to the files to PDSF for wider access to the data. This data is then served by the _Web App_. It also handles calls to _Process Runs_ for dynamic features, including stepping through the data in time, both within a run and by run, as well as basic QA.

The rest of this README is intended for **technical users**, such as those adding detector functionality. Any general users will likely want to return back to the _Web App_.

#### Technical Description

This project utilizes data from the HLT (although it could be from any source of histograms if they were saved properly). Access to the HLT must be handled and is outside the scope of this package - our current setup uses a number of systems at CERN. The histograms are received from the HLT, and then saved to a file at a fixed time interval (this is currently performed every minute). A cron job is then setup to run _Process Runs_ at some short time interval. It is generally best to run _Process Runs_ less frequently than the interval between writes of the HLT files. _Process Runs_ will move, classify, and process the files. This includes printing the histograms, and transferring to the files to PDSF for wider access to the data. _Process Runs_ also contains functions to allow more dynamic processing of the data, including stepping through the data in time, both within a run and by run, as well as basic QA.

To handle viewing of the data, the server _Web App_ is used. It serves up the processed and printed data. This also handles stepping through time slices (both within runs as well as by run using the QA features) of the data by hooking into functions defined in _Process Runs_. It can also be configured to provide direct access to the underlying ROOT files. The _Web App_ can serve run pages based on Jinja2 templates (preferred) or fully static web pages, as both are written out. See [here](#directory-structure) for more information about the files that are written out. 

The _Web App_ is configured to work as both a full web server or a WSGI server. Since authentication is required for all of the data, Flask must serve all files. (/static could be served by a traditional server, since no authentication is needed for those files, but there are only a few small files, so it does not seem worthwhile to add the complicated when Flask seems to work fine, if not at the best performance). 

A full, high performance web server is available in _Full Stack Server_. It is extremely simple, but it can act as a front end to the Flask server, which is a task usually performed by a more traditional web server such as Apache or Nginx. When the _Full Stack Server_ is used, the _Web App_ is used as a WSGI server and it will automatically be loaded by the _Full Stack Server_.

This package has only had basic testing against python 3.

## Setup and Usage

This is a `python` based project, so pip (ie `pip install <packageName>`) is the recommended way to install dependencies.

 1. Install dependencies: `flask Flask-Login Flask-Bcrypt bcrypt numpy flup future`. This can be accomplished by running `pip install -r requirements.txt`. If using the _Web App_ as a WSGI server on PDSF, then `uwsgi` is also needed. It is not needed for a normal user.

 2. Optional, but recommended: Build the documentation. See [here](#documentation).

 3. Configure _Process Runs_ and the _Web App_ with files in the `config` directory. Copy `serverParams_stub` to `serverParams` so that it is usable. Begin configuring with the options in `sharedParams` file, and then configure `processingParams` and `serverParams` as necessary. Most defaults should be fine but at minimum, the `users` and `secretKey` must be configured in `serverParams`. Each option is extensively documented, which can be viewed in the source file or the documentation.

 4. Configure the directory structure. See [here](#directory-structure).

 5. Run _Process Runs_ to process the available data. `python processRuns.py`

 6. Run the _Web App_ to look at the data in a better organized way. `python webApp.py`. It can then be accessed at `http://localhost:portNumber`, where `portNumber` is the port defined in the `serverParams` file.

## Documentation

Based on `sphinx-autodoc` generation, the documentation is generated from the docstrings in the code. While they can be viewed in the source files or via python, sphinx compiles them into HTML, facilitating a cleaner view of the information. To build the documentation,

 1. Install the dependencies. The documentation requires the python packages `sphinx sphinxcontrib-napoleon recommonmark`. Pip is the recommended install method.
 
 2. Build the documentation using:

    ```bash
    cd doc
    make html
    open doc/build/html/index.html
    ```

The documentation will be created and available in the `doc/build/html/`. It is recommended to start with the `index.html` page.

## Adding a Detector

Adding a new detector to the project is well documented in the `processRunsModules.detectors` package. Please look at it in the documentation (or look at it via python or the source file, `processRunsModules/detectors/__init__.py`). After following this guide, create a pull request for this repository at [raymondEhlers/OVERWATCH](https://github.com/raymondEhlers/OVERWATCH).

## File Structure

### Files

 - `processRuns.py` - Moves, classifies, and processes files from the HLT. It will drive functions to produce html and images to display the data for arbitrary times and runs. This file and the associated modules contains functions that provide a large majority of the overall functionality.

 - `webApp.py` - A Flask application which handles serving either dynamic (template) or static (simple html pages) run pages to display the QA data. It handles authentication, as well as allowing dynamic features, such as viewing time slices of the data within and between runs.

 - `fullStackServer.py` - A higher performance front-end server for use with `webApp.py`. Not necessary at PDSF, but useful for testing, and it allows for deployment at other places without additional infrastructure setup. It requires the python modules `cherrypy` and `paste`.

Inside of the data folder, there are a few main HTML files. `(subsystem)output.html` displays images from the run. `(subsystem)ROOTFiles.html` links to the raw ROOT files that are saved out for each write of histograms from the HLT. In both cases, `(subsystem)` is the three letter name of a detector in all caps.

### Directory Structure

There are specific directories for data, docs, config, templates, modules, and additional static files.

**IMPORTANT NOTE**: _Process Runs_ saves many files, including templates, relative to the `data/` directory (it was done for historical reasons). Consequently, **if the data directory is not going to be stored in the root folder of this repository, then create a symlink to it and call it `data`**. For instance, if it the data is going to be stored at `/path/to/data`, then in the root folder of the repository, one should run `ln -s /path/to/data data`.

 - data/ - Contains all of the histogram data. Also contains static HTML pages that are an alternative to the dynamic templates normally used to render the site.

 - doc/ - Contains the files to build the documentation for the project. See [here](#documentation).

 - config/ - Contains all of the configuration files for _Process Runs_, the _Web App_, and running the _Web App_ as a WSGI server. See the documentation or the source files for more information about the individual options.

 - processRunsModules/ - Contains most of the functionality of _Process Runs_, as well as some generally useful utilities. See the documentation for more information.

 - templates/ - Contains all of the jinja2 templates needed to render the website. The main templates are stored in the root of the folder, while templates related to the data are stored in a "data" directory that mirrors the structure of the main "data" directory.

 - static/ - Contains the shared `css`, `javascript`, and background texture. 

 - webAppModules/ - Contains helper functions for the _Web App_. See the documentation for more information.

For reference, an example file structure is shown below.

```bash
.
├── fullStackServer.py
├── processRuns.py
├── README.html
├── README.md
├── startWSGIServer.sh
├── webApp.py
├── config
│   ├── __init__.py
│   ├── processingParams.py
│   ├── serverParams.py
│   ├── serverParams_stub.py
│   ├── sharedParams.py
│   └── wsgiConfig.ini
├── data
│   ├── Run123456
│   │   ├── EMC
│   │   │   ├── EMChists.*.root
│   │   │   ├── EMCoutput.html
│   │   │   ├── hists.combined.*.root
│   │   │   └── img [contains *.png]
│   ├── Run123457
│   │   ├── EMC
│   │   │   ├── EMChists.*.root
│   │   │   ├── EMCoutput.html
│   │   │   ├── hists.combined.*.root
│   │   │   ├── img [contains *.png]
│   │   │   └── timeSlices
│   │   │       ├── timeSlice.*
│   │   │       │   ├── EMCoutput.html
│   │   │       │   └── img [contains *.png]
│   │   │       └── timeSlice.*.root
│   │   └── HLT
│   │       ├── HLTROOTFiles.html
│   │       ├── HLThists.*.root
│   │       ├── HLToutput.html
│   │       ├── TPCoutput.html
│   │       ├── hists.combined.*.root
│   │       ├── img [ contains *.png ]
│   │       └── timeSlices
│   │           ├── timeSlice.*
│   │           │   ├── HLToutput.html
│   │           │   └── img [ contains *.png ]
│   │           └── timeSlice.*.root
│   ├── determineMedianSlope [ Could be another QA function ]
│   │   └── medianSlope.png
│   ├── runList.html
│   └── testingDataArchive.zip
├── doc
│   ├── Makefile
│   └── source
│       ├── _static
│       ├── _templates
│       ├── conf.py
│       ├── config.rst
│       ├── fullStackServer.rst
│       ├── index.rst
│       ├── processRuns.rst
│       ├── processRunsModules.detectors.rst
│       ├── processRunsModules.rst
│       ├── webApp.rst
│       └── webAppModules.rst
├── processRunsModules
│   ├── __init__.py
│   ├── detectors
│   │   ├── EMC.py
│   │   ├── HLT.py
│   │   ├── __init__.py
│   ├── generateHtml.py
│   ├── generateWebPages.py
│   ├── mergeFiles.py
│   ├── qa.py
│   ├── utilities.py
├── static
│   ├── cream-pixels.png
│   ├── shared.js
│   └── style.css
├── templates
|   ├── data
|   │   ├── Run123456
|   │   │   └── EMC
|   │   │       └── EMCoutput.html
|   │   ├── Run123457
|   │   │   ├── EMC
|   │   │   │   ├── EMCoutput.html
|   │   │   │   └── timeSlices
|   │   │   │       └── timeSlice.*
|   │   │   │           └── EMCoutput.html
|   │   │   └── HLT
|   │   │       ├── HLTROOTFiles.html
|   │   │       ├── HLToutput.html
|   │   │       ├── TPCoutput.html
|   │   │       └── timeSlices
|   │   │           └── timeSlice.*
|   │   │               └── HLToutput.html
|   │   └── runList.html
|   ├── contact.html
|   ├── error.html
|   ├── layout.html
|   ├── login.html
|   ├── qa.html
|   └── qaResult.html
└── webAppModules
    ├── __init__.py
    ├── auth.py
    ├── routing.py
    └── validation.py
```

## Development Note

This project was originally developed in the [alice-yale-dev](https://gitlab.cern.ch/ALICEYale/alice-yale-dev) repository. All older development history is available there.

## To do

There are a number of possible improvements for this project

 - Allow additional user options for reprocessing via the time dependent merge. Additional options should include:
     - Option to disable scaling by nEvents.
     - Option to change the hot channel warning threshold. This should be done generally enough such that other values could be set in the future.

 - Implement better logging and error notification. It is all explained [here](http://flask.pocoo.org/docs/0.10/errorhandling/).

 - Split out the QA and partial merge functions to use worker pools using something such as `celery`. This would require asynchronus loading of the images once the process is completed. One solution for 

 - Processing relies heavily on metadata. These operations can be very slow, particularly on slows disks. To resolve this, a database should be created (likely built using MongoDB) which caches and manages such metadata, thereby reducing the load on the disk. A longer term approach could store the data directly there, creating ROOT histograms (or some other visualization tool) on the fly.
 
 - CERN Single Sign On (SSO) support. This would require a reworking of the authentication system. For more information, see [here](https://alexpearce.me/2014/10/setting-up-flask-with-apache-and-shibboleth/). This appears to be a very involved process. It may be simpler to implement using `SAML2`. See the CERN SSO page for more information.

## Authors

 - [Raymond Ehlers](mailto:raymond.ehlers@cern.ch), Yale University 

 - [James Mulligan](mailto:james.mulligan@yale.edu), Yale University 
