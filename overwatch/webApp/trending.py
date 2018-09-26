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
    trendingManager = TrendingManager(db[CON.TRENDING], serverParameters)
    subsystemName = determineSubsystemName(subsystemName, trendingManager)
    assert subsystemName

    # Template paths to the individual files
    filenameTemplate = os.path.join(CON.TRENDING, subsystemName, '{}', '{}.{}')
    imgFilenameTemplate = filenameTemplate.format(CON.IMAGE, '{}', serverParameters[CON.EXTENSION])
    jsonFilenameTemplate = filenameTemplate.format(CON.JSON, '{}', 'json')

    if ajaxRequest != True:
        if error == {}:
            try:
                returnValue = render_template("trending.html", trendingManager=trendingManager,
                                              selectedHistGroup=subsystemName, selectedHist=requestedHist,
                                              jsonFilenameTemplate=jsonFilenameTemplate,
                                              imgFilenameTemplate=imgFilenameTemplate,
                                              jsRoot=jsRoot)
            except jinja2.exceptions.TemplateNotFound as e:
                error.setdefault("Template Error", []).append(
                    "Request template: \"{0}\", but it was not found!".format(e.name))

        if error != {}:
            logger.warning("error: {0}".format(error))
            returnValue = render_template("error.html", errors=error)
        return returnValue

    else:
        drawerContent = ''
        mainContent = ''
        if error == {}:

            try:
                drawerContent = render_template("trendingDrawer.html", trendingManager=trendingManager,
                                                selectedHistGroup=subsystemName, selectedHist=requestedHist,
                                                jsonFilenameTemplate=jsonFilenameTemplate,
                                                imgFilenameTemplate=imgFilenameTemplate,
                                                jsRoot=jsRoot)
                mainContent = render_template("trendingMainContent.html", trendingManager=trendingManager,
                                              selectedHistGroup=subsystemName, selectedHist=requestedHist,
                                              jsonFilenameTemplate=jsonFilenameTemplate,
                                              imgFilenameTemplate=imgFilenameTemplate,
                                              jsRoot=jsRoot)
            except jinja2.exceptions.TemplateNotFound as e:
                error.setdefault("Template Error", []).append(
                    "Request template: \"{0}\", but it was not found!".format(e.name))

        if error != {}:
            logger.warning("error: {0}".format(error))
            drawerContent = ""
            mainContent = render_template("errorMainContent.html", errors=error)

        # Includes hist group and hist name for time slices since it is easier to pass it here than parse the get requests. Otherwise, they are ignored.
        return jsonify(drawerContent=drawerContent,
                       mainContent=mainContent,
                       histName=requestedHist,
                       histGroup=subsystemName)
