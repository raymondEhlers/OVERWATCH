import logging
from flask_login import login_required
from flask import request, render_template, jsonify
import jinja2
import os

import overwatch.processing.trending.constants as CON
from overwatch.processing.trending.manager import TrendingManager
from overwatch.webApp.webApp import app, db, serverParameters
from overwatch.webApp import validation

logger = logging.getLogger(__name__)


def determineSubsystemName(subsystemName, trendingManager):  # type: (str, TrendingManager) -> str
    if subsystemName:
        return subsystemName

    for subsystemName, subsystem in trendingManager.trendingDB.items():
        if len(subsystem):
            return subsystemName


@app.route("/" + CON.TRENDING, methods=["GET", "POST"])
@login_required
def trending():
    """ Trending visualization"""
    logger.debug("request: {0}".format(request.args))
    (error, subsystemName, requestedHist, jsRoot, ajaxRequest) = validation.validateTrending()

    # Create trending container from stored trending information
    trendingManager = TrendingManager(db, serverParameters)
    subsystemName = determineSubsystemName(subsystemName, trendingManager)
    assert subsystemName

    # Template paths to the individual files
    filenameTemplate = os.path.join(CON.TRENDING, subsystemName, '{}', '{}.{}')
    imgFilenameTemplate = filenameTemplate.format(CON.IMAGE, '{}', serverParameters[CON.EXTENSION])
    jsonFilenameTemplate = filenameTemplate.format(CON.JSON, '{}', 'json')

    templateKwargs = {
        'trendingManager': trendingManager,
        'selectedHistGroup': subsystemName,
        'selectedHist': requestedHist,
        'jsonFilenameTemplate': jsonFilenameTemplate,
        'imgFilenameTemplate': imgFilenameTemplate,
        'jsRoot': jsRoot,
    }

    if ajaxRequest:
        drawerContent = safeRenderTemplate(error, "trendingDrawer.html", **templateKwargs)
        mainContent = safeRenderTemplate(error, "trendingMainContent.html", **templateKwargs)
        mainContent = reRenderIfError(error, "errorMainContent.html", mainContent)

        # Includes hist group and hist name for time slices since it is easier
        # to pass it here than parse the get requests. Otherwise, they are ignored.
        return jsonify(drawerContent=drawerContent, mainContent=mainContent,
                       histName=requestedHist, histGroup=subsystemName)

    returnValue = safeRenderTemplate(error, "trending.html", **templateKwargs)
    returnValue = reRenderIfError(error, "error.html", returnValue)
    return returnValue


def safeRenderTemplate(error, *args, **kwargs):
    if error != {}:
        return ''
    try:
        return render_template(*args, **kwargs)
    except jinja2.exceptions.TemplateNotFound as e:
        error.setdefault("Template Error", []).append(
            'Request template: "{0}", but it was not found!'.format(e.name))
        return ''


def reRenderIfError(error, template, rendered):
    if error != {}:
        return render_template(template, error=error)
    else:
        return rendered
