/** Handles JavaScript generally for Overwatch
  *
  * Contains general functionality for Overwatch, including supporting AJAX requests, jsRoot, as well
  * as presentation (such as collapsing containers, etc).
  *
  * NOTE: For our purposes, this code is sufficient for getting the job done. However, it really isn't
  *       very pretty or sophisticated and could most certainly benefit from a more experienced developer.
  *
  * Author: Raymond Ehlers <raymond.ehlers@yale.edu>, Yale University
  */

/**
  * This is the initial entry point where we setup all of the options, preferences, routing, etc.
  *
  * This performs initialization for both the app shell, as well as the individual page. If the
  * individual page changes with an AJAX request, we don't need to perform this function. We just
  * need to perform the more limited `initPage(...)`.
  *
  * NOTE: To ensure that elements are ready on polyfilled browsers, wait for `WebComponentsReady`.
 */
document.addEventListener('WebComponentsReady', function() {
    // Enable the link for the menu button to control the drawer.
    var menuButton = Polymer.dom(this.root).querySelector("#headerMenuButton");
    var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
    //console.log("panelButton: " + menuButton.outerHTML);
    // Create toggle for the drawer button.
    $(menuButton).click(function() {
        drawer.togglePanel();
    });

    // Create the link and dialog for the time slices dialog panel.
    setupDialog("propertiesButton", "propertiesDialog");
    // Create the link and dialog for the user settings dialog panel.
    setupDialog("userSettingsButton", "userSettings", true);

    // Ensure that we show or hide the menu button when the page loads.
    showOrHideMenuButton();
    // Add a listener for further changes.
    document.addEventListener("paper-responsive-change", showOrHideMenuButton);

    // Handle toggle value.
    var jsRootState = handleToggle("jsRootToggle");
    handleToggle("ajaxToggle");

    // Setup handling for the time slices form.
    handleFormSubmit("timeSlicesForm", "submitTimeSlices");

    // Remove flask flashes after a short period to ensure that it doesn't clutter the screen.
    removeFlashes();

    // Ensure that all links are routed properly (either through AJAX or a normal link).
    routeLinks();

    // Enables collapsing of containers with information.
    collapsibleContainers();

    // Perform the rest of the initialization which needs to be performed for every page.
    initPage(jsRootState);

    // Setup function to handle changing pages.
    window.addEventListener("popstate", handleChangeInHistory);
});

/**
  * Initialization functions which needs to be performed every time a page is loaded,
  * whether through a standard GET request, or via AJAX.
  */
function initPage(jsRootState) {
    // Get the value of `jsRootState` if it is undefined.
    // See: https://stackoverflow.com/a/894877
    jsRootState = typeof jsRootState !== 'undefined' ? jsRootState : ($(Polymer.dom(this.root).querySelector("#jsRootToggle")).prop("checked") === true);
    console.log("jsRootState: " + jsRootState);

    // Call jsRoot if necessary.
    if (jsRootState === true)
    {
        jsRootRequest();
    }

    // Update the title in the top bar based on the title defined in the main content.
    // The title was likely updated by the new content.
    var title = Polymer.dom(this.root).querySelector("#mainContentTitle");
    var titlesToSet = Polymer.dom(this.root).querySelectorAll(".title");
    if (title) {
        // Set the title in the toolbar and in the page.
        $(titlesToSet).text($(title).text());
        $('html head').find('title').text("ALICE OVERWATCH - " + $(title).text());
    }

    // Ensure that we only show on run pages.
    showOrHideProperties();

    // Sets the max limits of the form.
    setTimeSlicesFormValues();
}

/**
  * Removes flash after 5 seconds to avoid confusion.
  * From: https://www.sitepoint.com/community/t/hide-div-after-10-seconds/5910
  */
function removeFlashes() {
    console.log("Setting up the ability to remove flashes.");
    // We set the timeout on flashes to 5 seconds.
    setTimeout(function() {
        var flashes = document.getElementById("flashes");
        if (flashes != null)
        {
            flashes.style.display = "none";
        }
    }, 5000);
}

/**
  * Setup form submission so that it is properly submitted with AJAX.
  *
  * This involves setting up the actual form submission, adding `jsRoot` to the submission
  * showing a loading spinner while the response is being processed, and then setting up
  * the handling of the response.
  */
function handleFormSubmit(selectedForm, selectedButton) {
    var button = Polymer.dom(this.root).querySelector("#" + selectedButton);
    console.log("button: " + $(button).text());
    var form = document.querySelector("#" + selectedForm);

    // Show the spinner while the request is processing.
    $(button).click(function() {
        //var form = Polymer.dom(this.root).querySelector("#" + selectedForm);
        //var form = document.querySelector("#" + selectedForm);
        //console.log("form: " + $(form).text());

        // Show spinning wheel
        // For some reason, Polymer does not work here...
        //console.log("Showing spinner")
        var spinner = document.querySelectorAll("#loadingSpinnerContainer");
        //console.log("spinner: " + spinner);
        $(spinner).addClass("flexElement");
        
        form.submit();
    });

    // Append jsRoot to the form request
    form.addEventListener('iron-form-presubmit', function() {
        // Polymer DOM doesn't work here either...
        var jsRoot = $(document.querySelector("#jsRootToggle")).prop("checked") === true;
        // Append jsRoot to the request
        this.request.body.jsRoot = jsRoot;
        //console.log("this.request.body: " + JSON.stringify(this.request.body));
    });

    // Error handling.
    form.addEventListener("iron-form-error", function(event) {
        /*console.log("Error in iron-form!");
        console.log("event.detail.error:" + event.detail.error);*/

        // Create a fake data response so that we can propagate the error.
        var data = {};
        data.mainContent = event.detail.error;
        data.mainContent += ". Please contact the admin with information about what you were doing so that the error can be fixed! Thank you!";

        handleAjaxResponse()(data);
    });

    // Handle the actual form submission.
    form.addEventListener("iron-form-response", function(event) {
        // See: https://github.com/PolymerElements/iron-form/issues/112
        //console.log("event.detail.response: " + JSON.stringify(event.detail.response));
        var data = event.detail.response;

        /*console.log("status: " + event.detail.status);
        if (event.detail.status === 200) {
            console.log("Successful request!");
        }*/
        if (event.detail.status === 500) {
            console.log("Internal server error! ");
            // This should render in the main window
            data.mainContent = "500: Internal Server Error! Please contact the admin with information about what you were doing so that the error can be fixed! Thank you!";
        }

        handleAjaxResponse()(data);

        // Determine the GET parameters for display in the history.
        // NOTE: It could be null here in some cases if the request failed and we returned
        // an error message.
        if (data !== null) {
            var localParams = {};
            if (data.hasOwnProperty("timeSliceKey") && data.timeSliceKey !== "null") {
                localParams.timeSliceKey = data.timeSliceKey;
            }
            if (data.hasOwnProperty("histName") && data.histName !== "null") {
                localParams.histName = data.histName;
            }
            if (data.hasOwnProperty("histGroup") && data.histGroup !== "null") {
                localParams.histGroup = data.histGroup;
            }
            /*console.log("data: " + data);
            console.log("localParams: " + JSON.stringify(localParams));*/

            // Stay on the current page and update the history.
            // We need to set retrieve the current page and pass it to `updateHistory()`
            // to ensure that it doesn't navigate us away from our current page, where
            // we want to stay.
            var currentPage = window.location.pathname;
            console.log("currentPage: " + currentPage);
            updateHistory(localParams, currentPage);
        }
    });
}

/**
  * Set the values in the time slice form based on those provided in the main content.
  *
  * This enables the form to know which histograms or hist groups should be processed,
  * as well as setting the time limits to times for which we actually have data. 
  */
function setTimeSlicesFormValues() {
    var formValues = Polymer.dom(this.root).querySelector("#timeSlicesValues");
    var form = Polymer.dom(this.root).querySelector("#timeSlicesForm");

    if (form !== undefined && formValues !== undefined) {
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormMinTime", "runLength", "max");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormMinTime", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormMaxTime", "runLength", "max");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormMaxTime", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormHotChannelThreshold", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormHistGroupName", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormHistName", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormRunDir", "", "value");
        setTimeSlicesFormValue(form, formValues, "timeSlicesFormSubsystem", "", "value");
    }
}

/**
  * Helper function to actually set the requested values to their corresponding variables in the form.
  *
  * This function retrieves the current and new values by extracting the requested values from the main
  * content. It then sets the current value to the new value (if the values were extracted successfully).
  */
function setTimeSlicesFormValue(form, formValues, formValueSelector, newValueDataName, valueType) {
    // Retrieve the objects
    var currentValue = $(form).children("#" + formValueSelector);
    // Format the string if necessary (it will work fine even if it's an empty string
    if (newValueDataName === "") {
        newValueDataName = formValueSelector;
    }
    newValueDataName = newValueDataName.replace("timeSlicesForm", "").toLowerCase();
    var newValue = $(formValues).data(newValueDataName);
    // Help handle 0. The form does not handle it well...
    // Instead, just take a small value to indicate that there is nothing more.
    if (newValue === 0 && valueType === "max") {
        console.log("Reassign a 0 to 0.5 for a max value!");
        newValue = 0.5;
    }
    /*console.log("currentValue: " + $(currentValue).prop(valueType));
    console.log("newValue: " + newValue);*/
    // Set the values
    // Need to check explicitly, because otherwise this fails on 0...
    if (currentValue !== undefined && currentValue !== null && newValue !== undefined && newValue !== null) {
        //console.log("Assigning!");
        $(currentValue).prop(valueType, newValue);
    }
}

/**
  * Setup a toggle value to store it's value in the browser's local storage.
  *
  * If the toggle value is in local storage, then we update the toggle value on the current page.
  * We also set it up to toggle back and forth based on the user clicking the button.
  *
  * NOTE: If no local storage, then both jsRoot and AJAX are enabled (because the default `returnValue` is `true`).
  *       However, it should be fairly unlikely to encounter such a environment.
  */
function handleToggle(selectedToggle) {
    var returnValue = true;
    if (storageAvailable("localStorage")) {
        var toggle = Polymer.dom(this.root).querySelector("#" + selectedToggle);
        // Check for value in local storage, and set it properly if it exists.
        // This gets the page in sync with the stored value.
        var storedToggleValue = localStorage.getItem(selectedToggle);
        if (storedToggleValue) {
            // See: https://stackoverflow.com/a/264037
            $(toggle).prop("checked", (storedToggleValue === "true"));

            console.log("Local storage checked for " + selectedToggle +": " + localStorage.getItem(selectedToggle));
        }

        // Setup the toggle to store the value in the local storage when it is changed.
        $(toggle).click(function() {
            // Store value in local storage.
            localStorage.setItem(selectedToggle, $(this).prop("checked").toString());

            console.log("Local storage checked for " + selectedToggle +": " + localStorage.getItem(selectedToggle));
        });

        // Finally, retrieve the current value to return to the caller.
        returnValue = $(toggle).prop("checked");
    }
    else {
        console.log("ERROR: Local storage not supported!");
    }

    return returnValue;
}

/**
  * Setup a button to open a dialog box.
  *
  * In particular, this is used to setup the time slice and user settings buttons.
  */
function setupDialog(buttonSelector, dialogSelector, relativePosition) {
    // Retrieve objects
    //var propertiesButton = document.getElementById("buttonSelector");
    var button = Polymer.dom(this.root).querySelector("#" + buttonSelector);
    //var propertiesDialog = document.getElementById("dialogSelector");
    var dialog = Polymer.dom(this.root).querySelector("#" + dialogSelector);
    
    //console.log("button: " + button + " dialog: " + dialog);

    // Add a click listener to perform the actual opening of the dialog.
    $(button).click(function() {
    //button.addEventListener("click", function() {
        dialog.open();
    });

    // Assign the position target of the dialog.
    if (relativePosition === true) {
        $(dialog).prop("positionTarget", button);
    }
}

/**
  * Show or hide time slices link based on the whether we are on a run page.
  * If we are on a run page, it should be shown.
  */
function showOrHideProperties() {
    var properties = Polymer.dom(this.root).querySelector("#propertiesButton");
    var currentPage = window.location.pathname;
    console.log("currentPage: " + currentPage);
    // Check for if we are on a run page by looking at the current URL.
    // If we are on a run page, it will contain "runPage".
    if (currentPage.search("runPage") !== -1) {
        console.log("Showing properties button");
        $(properties).removeClass("hideElement");
    }
    else {
        console.log("Hiding properties button");
        $(properties).addClass("hideElement");
    }
}

/**
  * Hide the drawer menu button if in the wide display mode (based on the value of the `narrow`
  * property).
  */
function showOrHideMenuButton() {
    var menuButton = Polymer.dom(this.root).querySelector("#headerMenuButton");
    var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
    //console.log("menuButton: " + menuButton.outerHTML);
    console.log("drawer narrow: " + $(drawer).prop("narrow"));
    // Decide whether to hide the button based on the `narrow` property.
    // We do the actual hiding or showing by adding CSS elements.
    if ($(drawer).prop("narrow") === true) {
        $(menuButton).removeClass("hideElement");
        console.log("Removing hideElement");
    }
    else {
        $(menuButton).addClass("hideElement");
        console.log("Adding hideElement");
    }
}

/**
  * Handles routing all links (`<a>`) to their proper destination.
  *
  * If they are to download files (like the test files), anchors (staying on the same page),
  * or to open in a new window (via `target` === "_blank"), we want to route them as normal.
  * Otherwise, it is a route within the web app, so we will pass it on to be inspected more
  * closely.
  */
function routeLinks() {
    // For links to be intercepted, they must be children of an object which
    // includes the `linksToIntercept` class. By avoiding general selection on "a",
    // we don't need to handle as many special cases where we want the normal behavior.
    // Basically, we want to intercept the minimum possible links (which is still quite a
    // large slice of the links).
    var linksToIntercept = Polymer.dom(this.root).querySelectorAll(".linksToIntercept");
    //var allLinks = Polymer.dom(this.root).querySelectorAll("a");
    //console.log("allLinks: " + allLinks);
    //console.log("linksToIntercept: " + linksToIntercept);
    //console.log("linksToIntercept[0]: " + linksToIntercept[0].outerHTML);
    //$(allLinks).click(function(event) {

    // Uses event delegation to intercept the links.
    // We use `on` instead of `click` here because it can better handle dynamic elements.
    // For more on this choice, see here: https://stackoverflow.com/a/11878976
    $(linksToIntercept).on("click", "a", function(event) {
        // Handle download links properly.
        // If the "download" attribute exists, then instead of handling with AJAX, we just let it link as normal.
        if ($(this).attr("download") !== undefined) {
            return;
        }

        // Handle anchor links properly.
        // Since it is just a normal anchor, we should allow it to link as normal.
        // NOTE: If it is just the hash with nothing more, then we just needed a link to click on. Thus,
        //       we should keep going with our routing function.
        if ($(this).attr("href").indexOf("#") >= 0 && $(this).attr("href").length > 1) {
            return;
        }

        // Skip links which are supposed to open externally (ie where target = "_blank").
        if ($(this).attr("target") === "_blank") {
            return;
        }

        // Now that we've handled our exceptions, we want to prevent the link from being
        // evaluated directly so we can inspect it ourselves.
        event.preventDefault();

        var currentTarget = event.currentTarget;
        console.log("current target: " + $(currentTarget).text());

        // Debug information on what sort of link information is available.
        console.log("this: " + $(this).text());

        // Get the current page.
        var currentPage = window.location.pathname;
        console.log("currentPage: " + currentPage);

        // Determine where the request should be routed.
        var pageToRequest = $(this).attr("href");
        console.log("pageToRequest: " + pageToRequest);
        if (pageToRequest === "#") {
            // Request the current page again with the proper GET request instead of with a #
            console.log("Routing the requesting to the address of the current page.");
            pageToRequest = currentPage;
        }

        // Determine parameters for the request.
        // Get hist group name
        var histGroupName = $(this).data("histgroup");
        // Get histogram name
        var histName = $(this).data("histname");
        /*console.log("histGroupName: " + histGroupName);
        console.log("histName: " + histName);*/

        // jsRoot and AJAX will be added when handling the general request.
        var params = {
            histGroup: histGroupName,
            histName: histName
        };

        // Handle the general request.
        handleGeneralRequest(params, pageToRequest);

        // Update the browser history based on the request information.
        updateHistory(params, pageToRequest);

        // Prevent further action
        return false;
    });
}

/**
  * Update the history using the HTML5 history API.
  *
  * We have to do this carefully because we don't want to update the history when going backwards and forwards.
  * We ignore jsRoot here it will be picked up from the toggle at the time of the request.
  * Consequently, if it is the only defined parameter, then we just want to ignore it.
  */
function updateHistory(params, pageToRequest) {
    // Make a copy in case the user wants to use `params` afterwards!
    var localParams = typeof params !== 'undefined' ? JSON.parse(JSON.stringify(params)) : {};

    // Strip `ajaxRequest` if it is included!
    // Otherwise, the URL will include this and a full load of the page will only load the AJAX..
    if (localParams.hasOwnProperty("ajaxRequest")) {
        delete localParams.ajaxRequest;
    }

    // Remove jsRoot so that it does not disrupt routing. For instance, if it is true, but our setting is false,
    // then it won't send the image, but we also never make the jsRoot request.
    if (localParams.hasOwnProperty("jsRoot")) {
        delete localParams.jsRoot;
    }

    // As long as there are parameters other than `ajaxRequest`, then we should add them to the URL.
    if (!(jQuery.isEmptyObject(localParams))) {
        // Include just the GET parameters.
        window.history.pushState(localParams, "Title", pageToRequest + "?" + jQuery.param(localParams));
    }
    else {
        // Change the overall page (and does not include the GET parameters, since they are null!).
        window.history.pushState(localParams, "Title", pageToRequest);
    }
}

/**
  * Perform the actual AJAX call and pass the result on for further processing.
  *
  * In the case of success or of error, we pass the result to `handleAjaxResponse()`
  * with the AJAX response data.
  */
function ajaxRequest(pageToRequest, params) {
    console.log("Sending ajax request to " + pageToRequest);

    // Show spinning wheel while the request is being processed by the web app.
    //console.log("Showing spinner")
    var spinner = Polymer.dom(this.root).querySelectorAll("#loadingSpinnerContainer");
    $(spinner).addClass("flexElement");

    // `params` is copied by reference, so we need to copy the object explicitly to avoid modifying the
    // other copy. The approach used here to actually copy the object requires a bit of care, since it
    // will mangle many objects. However, for our purposes here, it is fine.
    // For more, see: https://stackoverflow.com/a/5344074
    var localParams = JSON.parse(JSON.stringify(params));
    // Set that we are sending an AJAX request.
    localParams.ajaxRequest = true;

    // Make the actual request and handle the return.
    // We handle simple error handling with an anonymous function defined right here.
    $.get($SCRIPT_ROOT + pageToRequest, localParams, handleAjaxResponse(localParams)).fail(function(jqXHR, textStatus, errorThrown) {
        var data = {};
        data.mainContent = textStatus + ": " + errorThrown;
        data.mainContent += ". Please contact the admin with information about what you were doing so that the error can be fixed! Thank you!";

        handleAjaxResponse()(data);
    });

    return localParams;
}

/**
  * Handle the response from an AJAX call.
  *
  * Here, we use the response information to replace the main and drawer content
  * in the app shell (assuming that they exist in the response). Note that this
  * response could generate further AJAX requests for jsRoot (which will be handled
  * through their dedicated AJAX functions instead of ours).
  */
var handleAjaxResponse = function (localParams) {
    localParams = typeof localParams !== 'undefined' ? localParams : {};
    return function(data) {
        // data is already json, so we don't need to perform any conversions.
        console.log("Handling AJAX response");
        //console.log(data)

        // Replace the drawer content if we received a meaningful response
        var drawerContent = $(data).prop("drawerContent");
        // console.log("drawerContent " + drawerContent);
        if (drawerContent !== undefined)
        {
            //console.log("Replacing drawer content!");
            var drawerContainer = Polymer.dom(this.root).querySelector("#drawerContent");
            $(drawerContainer).html(drawerContent);
        }

        // Replace the main content if we received a meaningful response
        var mainContent = $(data).prop("mainContent");
        //console.log("mainContent: " + mainContent);
        if (mainContent !== undefined)
        {
            //console.log("Replacing main content!");
            var mainContainer = Polymer.dom(this.root).querySelector("#mainContent");
            $(mainContainer).html(mainContent);
        }

        // Handle page initialization
        // Note that this could create some additional AJAX requests via jsRoot
        if (!(localParams.hasOwnProperty("jsRoot"))) {
            console.log("jsRoot is not in localParams, so adding jsRoot value!");
            localParams.jsRoot = $(Polymer.dom(this.root).querySelector("#jsRootToggle")).prop("checked") === true;
        }
        initPage(localParams.jsRoot);

        // Update the drawer width
        // Code works, but the drawer does not handle this very gracefully.
        // Better to leave this disabled.
        /*var drawerWidthObject = Polymer.dom(this.root).querySelector("#drawerWidth");
        var drawerWidth = $(drawerWidth).data("width");
        var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
        $(drawer).prop("drawerWidth", drawerWidth);*/

        // Hide spinner now that we are done.
        var spinner = Polymer.dom(this.root).querySelectorAll("#loadingSpinnerContainer");
        //console.log("hiding spinner");
        $(spinner).removeClass("flexElement");
    };
};

/**
  * Handle jsRoot AJAX requests.
  *
  * Here, we find all histograms that are included in the main content and make requests
  * for the histogram representation in json. On a successful request, we use this information
  * to draw a histogram vis jsRoot.
  */
function jsRootRequest() {
    console.log("Handling js root request!");
    // Find all histograms that should be requested
    var requestedHists = Polymer.dom(this.root).querySelectorAll(".histogramContainer");
    $(requestedHists).addClass("histogramContainerStyle");

    // Request each jsRoot object
    $(requestedHists).each(function() {
        // Determine the request address.
        // Set the base request URL.
        var requestAddress = "/monitoring/protected/";
        // Add the filename from the histogram container corresponding to the request.
        requestAddress += $(this).data("filename");
        console.log("requestAddress: " + requestAddress);

        // Sets the object where the hist will be drawn.
        var objectToDrawIn = this;
        // Define the request and the handling of the returned object.
        var req = JSROOT.NewHttpRequest(requestAddress, 'object', function(jsRootObj) {
            // Plot the jsRootObj.
            // `jsRootObj` is the object returned by jsRoot.
            // For a grid, one would have to set one the required `div`s beforehand.
            // Then select the corresponding one to draw in after each request.

            // (re)draw `jsRootObj` at specified frame "objectToDrawIn"
            // `redraw()` was the previous API, while the newer API requires `draw()`.
            //JSROOT.redraw(objectToDrawIn, jsRootObj, "colz");
            JSROOT.draw(objectToDrawIn, jsRootObj, "colz");
        });

        // Actually send the request
        req.send();
    });
}

/**
  *  Handle changes in the history when navigating within the site.
  */
function handleChangeInHistory(eventState) {
    // Check for hashes first to avoid calling a `popstate` when it is a simple anchor.
    // NOTE: If it is just the hash with nothing more, then we just needed a link to click on. Thus,
    //       we should keep going with our function.
    var hash = window.location.hash;
    if (hash.indexOf("#") >= 0 && hash.length > 1) {
        return;
    }

    // Otherwise, continue with the pop state.
    var state = eventState.state;
    console.log("eventState: " + JSON.stringify(state));

    // Now that we've establish the state of the new page, we handle the request.
    handleGeneralRequest(state);
}

/**
  * Handle any request with a given set of parameters to a given page.
  *
  * The request will be made through a GET or an AJAX request depending on the user preferences
  * for `ajaxRequest`.
  */
function handleGeneralRequest(params, pageToRequest) {
    // We allow `pageToRequest` to be optional. If it isn't passed, we take `window.location.pathname`.
    // See: https://stackoverflow.com/a/894877
    pageToRequest = typeof pageToRequest !== 'undefined' ? pageToRequest : window.location.pathname;

    //console.log("params passed for general request: " + JSON.stringify(params));

    // If the `params` are empty, we need to do a general request. In that case, we want an empty object.
    if (params === null) {
        params = {};
    }

    // AJAX toggle status and convert it to bool
    var ajaxToggle = Polymer.dom(this.root).querySelector("#ajaxToggle");
    var ajaxState = ($(ajaxToggle).prop("checked") === true);
    // jsRoot toggle status and convert it to bool
    var jsRootToggle = Polymer.dom(this.root).querySelector("#jsRootToggle");
    var jsRootState = ($(jsRootToggle).prop("checked") === true);
    /*console.log("ajaxState: " + ajaxState);
    console.log("jsRootState: " + jsRootState);*/

    // This will ignore whatever was sent in the request parameters and use whatever value the user
    // has stored. This is potentially counterintuitive, but it seems to be the preferable solution 
    // because different users may have different desired settings, and it would be nice if the links
    // adapted to these settings dynamically.
    params.jsRoot = jsRootState;

    console.log("params for general request: " + JSON.stringify(params));

    // We need to handle `logout` carefully to avoid getting into a invalid state. The easiest
    // approach is just to require a full request on logout.
    if (ajaxState === false || pageToRequest.search("logout") !== -1) {
        console.log("ajax disabled link");

        // Make a copy in case the user wants to use `params` afterwards!
        var localParams = JSON.parse(JSON.stringify(params));

        // Strip `ajaxRequest` if it is included!
        // Otherwise, the URL will include this and a full load of the page will only load the AJAX.
        if (localParams.hasOwnProperty("ajaxRequest")) {
            delete localParams.ajaxRequest;
        }

        // This should never fall through since jsRoot should always be defined, but the check it is
        // left to be extra careful.
        if (!(jQuery.isEmptyObject(localParams))) {
            console.log("Assigning parameters to href");
            pageToRequest += "?" + jQuery.param(localParams);
        }
        else {
            console.log("ERROR: No parameters to assign");
        }

        // Assign the page, which will cause a request to load the specified link.
        console.log("Requesting page: " + pageToRequest);
        window.location.href = pageToRequest;
    }
    else {
        console.log("ajax enabled link");
        // We don't want to take the returned `params` variable, because adding the `ajaxRequest` setting to
        // the URL will often break loading the page from a link (ie it will only return the drawer and main
        // content, which we don't want in that situation).
        ajaxRequest(pageToRequest, params);
    }
}

/**
  * Enables the collapsing of containers which contain information to display.
  *
  * For example, this may be a list of hot channels. By default, the button should be shown,
  * but the container should be collapsed. For this opening and closing functionality to be
  * enabled, the button just needs to have the class `collapsibleContainerButton`.
  * The name of the button will have "Button" removed to find the name of the corresponding
  * collapsible container.
  */
function collapsibleContainers() {
    var containers = Polymer.dom(this.root).querySelectorAll("#mainContent");

    // Uses event delegation to intercept the links.
    $(containers).on("click", ".collapsibleContainerButton", function(event) {
        // Prevent the link while we change where it is going.
        event.preventDefault();

        // Determine our new target.
        var currentTarget = event.currentTarget;
        console.log("current target: " + $(currentTarget).text());

        // Find the collapsible container name by removing "Button".
        var containerName = $(currentTarget).attr("id").replace("Button", "");
        console.log("containerName: " + containerName);

        // Toggle container.
        // Polymer.dom() does not work for some reason.
        //var container = Polymer.dom(this.root).querySelector("#" + containerName);
        var container = $(currentTarget).siblings("#" + containerName);
        container.toggle();

        // Toggle the icon associated with the button and container.
        var iconObject = $(currentTarget).children(".collapsibleContainerIcon");
        var icon = $(iconObject).attr("icon");
        if (icon === "icons:arrow-drop-down") {
            icon = icon.replace("down", "up");
        }
        else {
            icon = icon.replace("up", "down");
        }
        $(iconObject).attr("icon", icon);
    });
}

/**
  * Check whether local storage is available.
  *
  * From: https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API
  */
function storageAvailable(type) {
    try {
        var storage = window[type],
        x = '__storage_test__';
        storage.setItem(x, x);
        storage.removeItem(x);
        return true;
    }
    catch(e) {
        return false;
    }
}

