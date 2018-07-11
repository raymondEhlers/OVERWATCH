<img src="https://cdn.rawgit.com/raymondEhlers/overwatch/37bc6f47/doc/logo/overwatchLogo.v1.png" width="75%" />

# ALICE Overwatch

[![DOI](https://zenodo.org/badge/50686415.svg)](https://zenodo.org/badge/latestdoi/50686415)

Welcome to ALICE Overwatch[\*](#name-meaning), a project to provide real-time online data monitoring and
quality assurance using timestamped data from the ALICE High Level Trigger (HLT) and Data Quality Monitoring (DQM).

# Quick Start

## Setup Overwatch

Along with a variety of dependencies which can be handled by pip, ROOT is required. ROOT 6 is recommended.

### Local development

To setup for local development is fairly straightforward.

```bash
$ git clone https://github.com/raymondEhlers/OVERWATCH.git overwatch
$ cd overwatch
# Probably best to do this in a virtualenv
$ pip install -r requirements.txt
# Install webApp static data (Google Polymer and jsRoot)
$ cd overwatch/webApp/static && bower install && git clone https://github.com/root-project/jsroot.git jsRoot && cd -
# Install for local development
$ pip install -e .
```

### Docker Image

As an alternative for advanced users or deployments, a docker image is available on Docker Hub under the name
`rehlers/overwatch`. Be certain to mount a directory containing data into the image so it can be used! Note
that you will likely want to use this image interactively (-it) and may want to remove the container when you
are done (--rm). If the data is in a folder called `data`, it should look something like:

```bash
$ docker run -it --rm -v data:/overwatch/data rehlers/overwatch /bin/bash
```

### Installation only for running Overwatch

For just running Overwatch (ie. performing no development at all), it is also available on
[PyPI](https://pypi.org/project/aliceOverwatch/) to install via pip.

```bash
# Required as a prerequisite since it is not available on PyPI.
$ pip install git+https://github.com/SpotlightKid/flask-zodb.git
# Install the final package
$ pip install aliceOverwatch
```

Note that the Overwatch package on PyPI includes all of `JSRoot` and Polymer components so that it can run out
of the box! While this is useful, it is important to remember that these dependencies must also be kept up to
date.

## Using Overwatch

### Retrieving test data

To use most parts of the Overwatch project, you need some data provided by the HLT. The latest five runs of data
received by Overwatch can be accessed
[here](https://aliceoverwatch.physics.yale.edu/testingDataArchive). The login credentials are available on
the [ALICE TWiki](https://twiki.cern.ch/twiki/bin/view/ALICE/L1TriggerMonitoring).

### Process the data with `overwatchProcessing`

Create a basic configuration file named `config.yaml` containing something like:

```yaml
# Main options
# Enable debug settings, messages at the debug level
debug: true
loggingLevel: "DEBUG"
# Reprocess the data each time, even if it is not detected as needed. It can be useful
# to test modifications to the processing
forceReprocessing: true

# The directory defaults to "data", which is the recommended name
dataFolder: &dataFolder "path/to/data"
```

Then, start processing the data with:

```bash
$ overwatchProcessing
```

### Visualizing the data with `overwatchWebApp`

For the webApp, add something similar to the following to your `config.yaml`:

```yaml
# Define users for local usage
_users: !bcrypt
    bcryptLogRounds: *bcryptLogRounds
    # You can change these values as desired
    # The key, (below is "username") is the the name of your user, while the value, (below is "password") is your password
    username: "password"
# Continue to keep debug: true . It often helps with ZODB difficulties.
```

Then, to start the webApp for data visualization, run:

```bash
$ overwatchWebApp
```

By default, the webApp will be available at [http://127.0.0.1:8850](http://127.0.0.1:8850) using the flask
development server (**not for production**). Login with the credentials that were specified in your
configuration file.

# Table of Contents

1. [Overwatch Overview and Architecture](#overwatch-overview-and-architecture)
    - [Processing](#overwatch-processing)
    - [Web App](@overwatch-webapp)
    - [Data Receivers](#overwatch-receivers)
2. [Overwatch Configuration](#overwatch-configuration)
3. [Overwatch Deployment](#overwatch-deployment)
4. [Citation](#citation)

# Overwatch Architecture

![](https://cdn.rawgit.com/raymondEhlers/overwatch/37bc6f47/doc/images/overwatchArch.png)

The Overwatch architecture is as shown above. Incoming data is handled by the receivers, which then make that data
available to be processed by the processing module. The output of the processing is then visualized via the WebApp.
In terms of code, the dependencies are as follows:

```
python modules
---
base <- processing <- webApp
     <- dqmReceiver

c++
---
zmqReceiver
```

Further information on each component is available in the sections below.

## Overwatch Processing

The main processing component of Overwatch is responsible for transforming the received data into a viewable
form, while also extracting derived quantities and performing checks for alarms. The main processing module is
written in python and depends heavily on PyRoot, with some functionality implemented through numpy. The module
is located in `overwatch/processing`, with the file `processRuns.py` driving the processing.

At a high level, the processing pipeline looks like:

- Extract run metadata (run number, HLT mode, detector subsystem being processed, available histograms in the particular run, etc).
- Determine which runs need processing.
    - For example, if a new file has arrived for a particular run, then that run should be processed.
- If the run is new, determine which objects (histograms) are included and to which groups they belong, which processing functions need to be run, etc.
    - The processing functions are implemented by each detector and called when requested by the particular detector.
- Apply those processing functions for each object (histogram), and store the outputs.

Each detector (also known as a subsystem) is given the opportunity to plug into the processing pipeline at nearly every stage. Each one is identified by the three letter detector name. The detector specific code is located in `overwatch/processing/detectors/` and can be enable through the processing configuration.

## Overwatch WebApp

![An Overwatch run page](https://cdn.rawgit.com/raymondEhlers/overwatch/37bc6f47/doc/images/overwatch.upgrade.runPage.png)

The web app visualizes the information provided by the processing. The WebApp is based on flask and serves
the various forms of visualization, as well as providing an interface to request on-demand processing of the
data with customized parameters. Note that this causes a direct dependence on the processing module. The main
mode of visualization is via json files displayed using `JSRoot`, which provides interactivity with the data.

## Overwatch Data Receivers

The receivers are responsible for receiving data from the various input sources and writing them out.
Receivers write out ROOT files with the same filename information, thereby allowing for them to be processed
the same regardless of their source.

_Note that these receivers need to be deployed in the production environment, but would rarely, if ever,
need to be used by standard Overwatch users!_

### HLT Receivers

Data from the HLT consists of ROOT TObject-derived objects sent via ZeroMQ (ZMQ). The receiver is built in C++,
with dependencies on HLT files automatically downloaded, compiled, and linked with the receiver code when the
receiver is compiled.

Installation follows the typical CMake pattern for an out of source build. When configuring, remember to specifying
the location of ZMQ and ROOT as necessary. Once built, the receiver executable is named `zmqReceive`. A variety of
options are available - for the precise options, see the help (`-h` or `--help`).

Note that if there is a ROOT version mismatch (for example, ROOT 5 on the HLT but ROOT 6 for Overwatch), it is
imperative to request the relevant ROOT streamers with the '--requestStreamers' option. Note that this option can
potentially trigger an internal ROOT bug, and therefore should not be used too frequently. Thus, the request is only
sent once when the receiver is started, and it should not be frequently restarted.

### DQM Receiver

Data from DQM consists of ROOT files sent via a rest API. The DQM receiver code is written as a flask app.
The web app is installed as part of the Overwatch package and can be run using the flask development server
via `overwatchDQMReceiver`. It is configured using the same system as the rest of the Overwatch package, as
described [here](overwatch-configuration).

For the APIs that are made available, please see the main server code in `overwatch/receiver/dqmReceiver.py`.

# Overwatch Configuration

Overwatch is configured via options defined in YAML configuration files. There is one configuration file each for
the Overwatch module (DQM receiver, processing, and webApp). Given the dependency of the various module on each
other, the configuration files are also interconnected. For example, if the webApp is loaded, it will also load
the processing configuration, along with the other configurations on which the processing depends. In particular,
below is the ordered precedence for configuration files.

```
./config.yaml
~/overwatch{Module}.yaml
overwatch/webApp/config.yaml
overwatch/processing/config.yaml
overwatch/receiver/config.yaml
overwatch/base/config.yaml
```

The ordering of the configuration files means that values can be overridden in configurations that defined
with a higher precedence. For example, to enable debugging, simply set `debug: true` in your `./config.yaml`
(stored in your current working directory) - it will override the definition of `debug` as false in the base
configuration.

For a list of the available configuration options, see the `config.yaml` file in the desired module.

# Overwatch Deployment

All of the components of Overwatch can be configured and launched by the `overwatchDeploy` executable.
Overwatch is intended to be deployed with a docker image. Within this image, configurations are
managed by `supervisord`. All web apps are deployed behind nginx.

The Dockerfiles and additional information is available in the `deploy/docker` directory.

## Configuring Deployment

For a configuration file containing all available options, see `overwatch/base/deployConfig.yaml`. Note that
this particular file is _not_ considered when configuring a deployment - it only considers the file that is passed
to it.

## Deployment with the docker image

The role of the image is determined by the configuration passed into the environment variable config.
Available configuration options are described in the section
on [configuring Overwatch for deployment](#configuring-deployment).

The image can then be run with something like (using an external configuration file call config.yaml):

```bash
$ docker run -d -v data:/overwatch/data -e config="$(config.yaml)" rehlers/overwatch
```

# Citation

Please cite Overwatch as:

```
@misc{raymond_ehlers_2018_1309376,
  author       = {Raymond Ehlers and
                  James Mulligan},
  title        = {raymondEhlers/OVERWATCH: Initial full release},
  month        = jul,
  year         = 2018,
  doi          = {10.5281/zenodo.1309376},
  url          = {https://doi.org/10.5281/zenodo.1309376}
}
```

## Name Meaning

**OVERWATCH**: **O**nline **V**isualization of **E**merging t**R**ends and **W**eb **A**ccessible de**T**ector **C**onditions using the **H**LT.

