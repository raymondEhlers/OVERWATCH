#!/usr/bin/env python

""" Web app specific utilities.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

import os
import subprocess
import logging
# Setup logger
logger = logging.getLogger(__name__)
# Webassets
import webassets.filter

# Configuration
from ..base import config
(serverParameters, filesRead) = config.readConfig(config.configurationType.webApp)

class PolymerBundler(webassets.filter.ExternalTool):
    # TODO: Document
    """

    """
    name = "PolymerBundler"

    def input(self, _in, out, **kwargs):
        print("input. _in: {0}, out: {1}, kwargs: {2}".format(_in, out, kwargs))
        """ polymer-bundler must only be executed with relative paths, so we cannot use
        ExternalTool.subprocess, since that gives absolute paths. Further, to ensure that the polymer
        components also work when not bundled, it must be executed a directory above the static dir. This
        causes quite some complications.

        In addition, polymer-bundler parses arguments a bit strangely - values such as paths still need
        to be in a separate argument. Thus, the arguments looks more split than would usually be expected.

        For future reference, the kwargs available in input() include:
            kwargs: {'output': 'gen/polymerBundle.html',
                     'output_path': '/pathToOverwatch/overwatch/webApp/static/gen/polymerBundle.html',
                     'source_path': '/pathToOverwatch/overwatch/webApp/static/polymerComponents.html',
                     'source': 'polymerComponents.html'}
        """
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
                "--in-html",
                os.path.join(serverParameters["staticFolder"], "{source}".format(**kwargs))
                ]

        logger.debug("Executing polymer filter with execution path \"{0}\" and args {1}".format(executionPath, args))
        output = subprocess.check_output(args, cwd = executionPath)
        if len(output) > 0:
            logger.debug("Received non-zero output string! This means it likely worked!")
        # Write the output to the out string, which will then eventually automatically be written to file
        # With explicit decoding, it will fail
        out.write(output.decode('utf-8'))

# Register filter
webassets.filter.register_filter(PolymerBundler)
