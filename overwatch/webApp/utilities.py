#!/usr/bin/env python

""" Web app specific utilities.

In particular, it handles tasks related to deployment and minimization which are not relevant
to other Overwatch packages.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import os
import subprocess
import logging

import pendulum

logger = logging.getLogger(__name__)
# Webassets
import webassets.filter

# Configuration
from ..base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

class PolymerBundler(webassets.filter.ExternalTool):
    """ Filter to bundle Polymer html imports into a single file for deployment.

    Best practices dictate that the Polymer html imports should be combined into a single file
    to reduce the number of individual http requests. Polymer provides a tool to do so, called
    ``polymer-bundler``. By taking advantage of ``webassets``, we can automatically combine and
    minimize these files when starting a web app deployment.

    To successfully define the filter, the following details must be addressed:

    - polymer-bundler must only be executed with relative paths, so we cannot use
      ``ExternalTool.subprocess``, since that gives absolute paths.
    - To ensure that the polymer components also work when not bundled, the filter must be
      executed in a directory above the static dir.

    These issues causes quite some complications! See the ``input(...)`` function for how to deal
    with these issues.

    When ``webassets`` is run in debug mode, this filter will not be run! Instead, the standard
    (un-minified) version will be included. For information on forcing this filter to be run,
    see the :doc:`web app README </webAppReadme>`.
    """
    # Define the name of the bundle so it can be referenced.
    name = "PolymerBundler"

    def input(self, _in, out, **kwargs):
        """ Plugin function for adding an external filter to ``webassets``.

        As of August 2018, the ``kwargs`` options available include:

        .. code-block:: python

           kwargs = {'output': 'gen/polymerBundle.html',
                     'output_path': '/pathToOverwatch/overwatch/webApp/static/gen/polymerBundle.html',
                     'source_path': '/pathToOverwatch/overwatch/webApp/static/polymerComponents.html',
                     'source': 'polymerComponents.html'}

        Note:
            ``polymer-bundler`` parses arguments a bit strangely - values such as paths still need
            to be in a separate argument. Thus, the arguments looks more split than would usually
            be expected.

        Args:
            _in (StringIO): Input for the filter. Not used here.
            out (StringIO): Output for the filter. The output for ``polymer-bundler`` is written here.
                This will eventually be written out to a file.
            **kwargs (dict): Additional options required to run the filter properly. See the function
                description for the available options.
        Returns:
            None
        """
        # Printed because otherwise we won't be able to see the output.
        logger.debug("polymer-bundler filter arguments. _in: {}, out: {}, kwargs: {}".format(_in, out, kwargs))

        # Cannot just use the naive current path since this could be executed from anywhere. Instead,
        # look for the static folder - it must be included somewhere.
        output_path = "{output_path}".format(**kwargs)
        executionPath = output_path[:output_path.find(serverParameters["staticFolder"])]
        # Stream the result to stdout since writing the file seems to cause trouble with
        # the "out" string, which will overwrite the desired output
        args = [
            "polymer-bundler",
            "--inline-scripts",
            "--strip-comments",
            #"--out-html",
            #os.path.join(serverParameters["staticFolder"], "{output}.tmp".format(**kwargs)),
            # NOTE: It appears that ``--in-html`` is not a valid option anyonre. The input file should just be the last argument.
            os.path.join(serverParameters["staticFolder"], "{source}".format(**kwargs))
        ]

        logger.debug("Executing polymer filter with execution path \"{executionPath}\" and args {args}".format(executionPath = executionPath, args = args))
        output = subprocess.check_output(args, cwd = executionPath)
        if len(output) > 0:
            logger.debug("Received non-zero output string! This means the polymer-bundler filter likely worked!")
        # Write the output to the out string, which will then eventually automatically be written to file
        # Without explicit decoding here, it will fail
        out.write(output.decode('utf-8'))

# Register filter so it can be run in the web app
webassets.filter.register_filter(PolymerBundler)


def prettyPrintUnixTime(unixTime):
    """ Converts the given time stamp into an appropriate manner ("pretty") for display.

    The time is returned in the format: "Tuesday, 6 Nov 2018 20:55:10". This function is
    mainly needed in Jinja templates were arbitrary functions are not allowed.

    Note:
        We display this in the CERN time zone, so we convert it here to that timezone.

    Args:
        unixTime (int): Unix time to be converted.
    Returns:
        str: The time stamp converted into an appropriate manner for display.
    """
    d = pendulum.from_timestamp(unixTime, tz="Europe/Zurich")
    return d.format("dddd, D MMM YYYY HH:mm:ss")
