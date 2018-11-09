import logging
from flask_login import login_required
from flask import request, render_template, jsonify
from flask import Blueprint
import jinja2
import os

import overwatch.processing.trending.constants as CON
from overwatch.processing.trending.manager import TrendingManager
from overwatch.webApp.webApp import db, serverParameters
from overwatch.webApp import validation

logger = logging.getLogger(__name__)
trendingPage = Blueprint('trendingPage', __name__)


def determineSubsystemName(subsystemName, trendingManager):  # type: (str, TrendingManager) -> str
    """If subsystem argument is not valid, trying to return any subsystem from TrendingManager database"""
    if subsystemName:
        return subsystemName

    for subsystemName, subsystem in trendingManager.trendingDB.items():
        if len(subsystem):
            return subsystemName


@trendingPage.route("/" + CON.TRENDING, methods=["GET", "POST"])
@login_required
def trending():
    """ Route to provide visualization of trending information.

    This method provides functionality similar to that of a run page, but focused instead on displaying
    trending information. In particular, it displays trended objects from all subsystems, including
    those generated through the trending subsystem.

    Note:
        Function args are provided through the flask request object.

    Args:
        jsRoot (bool): True if the response should use jsRoot instead of images.
        ajaxRequest (bool): True if the response should be via AJAX.
        subsystemName (str): Name of the requested subsystem. It is fine for it to be an empty string.
        histName (str): Name of the requested histogram. It is fine for it to be an empty string.
    Returns:
        Response: Trending information template populated with trended objects.
    """

    logger.debug("request: {0}".format(request.args))
    (error, subsystemName, requestedHist, jsRoot, ajaxRequest) = validation.validateTrending(request)

    # Create trending container from stored trending information
    trendingManager = TrendingManager(db, serverParameters)
    subsystemName = determineSubsystemName(subsystemName, trendingManager)

    if not subsystemName:
        error.setdefault("Subsystem", []).append("Cannot find any trended subsystem")
        return render_template("error.html", error=error)

    # Template paths to the individual files
    filenameTemplate = os.path.join(CON.TRENDING, subsystemName, "{type}", "{{}}.{extension}")
    imgFilenameTemplate = filenameTemplate.format(type=CON.IMAGE, extension=serverParameters[CON.EXTENSION])
    jsonFilenameTemplate = filenameTemplate.format(type=CON.JSON, extension="json")

    templateKwargs = {
        "trendingManager": trendingManager,
        "selectedHistGroup": subsystemName,
        "selectedHist": requestedHist,
        "jsonFilenameTemplate": jsonFilenameTemplate,
        "imgFilenameTemplate": imgFilenameTemplate,
        "jsRoot": jsRoot,
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
    """If error is empty, return rendered template from *args and **kwargs.
    Otherwise return empty string, if exception appear return empty string."""
    if error != {}:
        return ''
    try:
        return render_template(*args, **kwargs)
    except jinja2.exceptions.TemplateNotFound as e:
        error.setdefault("Template Error", []).append(
            'Request template: "{0}", but it was not found!'.format(e.name))
        return ''


def reRenderIfError(error, template, rendered):
    """If errors exist, render new template with errors.
     Otherwise return unchanged previously rendered object."""
    if error != {}:
        return render_template(template, error=error)
    else:
        return rendered
