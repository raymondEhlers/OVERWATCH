/* TODO: Remove some debug messages! */

// Handle all of the polymer elements!
// To ensure that elements are ready on polyfilled browsers, wait for WebComponentsReady. 
document.addEventListener('WebComponentsReady', function() {
    // Enable the link for the menu button to control the drawer
    var menuButton = Polymer.dom(this.root).querySelector("#headerMenuButton");
    var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
    //console.log("panelButton: " + menuButton.outerHTML);
    // Create toggle for the drawer button
    $(menuButton).click(function() {
        drawer.togglePanel();
    });

    // Create the link and dialog for the time slices dialog panel
    setupDialog("propertiesButton", "propertiesDialog");
    // Create the link and dialog for the user settings dialog panel
    setupDialog("userSettingsButton", "userSettings", true);

    // Ensure that we show or hide the menu button when the page loads
    showOrHideMenuButton();
    // Add a listener for further changes
    document.addEventListener("paper-responsive-change", showOrHideMenuButton);

    // Handle toggle value
    var jsRootState = handleToggle("jsRootToggle");
    var ajaxState = handleToggle("ajaxToggle");

    // Handle forms
    handleFormSubmit("partialMergeForm", "submitPartialMerge");

    // Remove flask flashes after a short period to ensure that it doens't clutter the screen
    removeFlashes();

    // Ensure that all links are routed properly (either through ajax or a normal link)
    routeLinks();

    // Enables collapsing of containers with information
    collapsibleContainers();

    // Initialize the page
    initPage(jsRootState);

    // Setup function to handle changing pages
    window.addEventListener("popstate", handleChangeInHistory);
});

// These functions need to be run every time the page is laoded.
// Calling this function allows it to happen both on initial load and on ajax request
function initPage(jsRootState) {
    // Get the value of jsRootState if it is undefined
    // See: https://stackoverflow.com/a/894877
    jsRootState = typeof jsRootState !== 'undefined' ? jsRootState : ($(Polymer.dom(this.root).querySelector("#jsRootToggle")).prop("checked") === true);
    console.log("jsRootState: " + jsRootState);

    // Call jsroot if necessary
    if (jsRootState === true)
    {
        jsRootRequest();
    }

    // Update the title in the top bar based on the title defined in the main content
    // The title was likely updated by the new content
    var title = Polymer.dom(this.root).querySelector("#mainContentTitle");
    var titlesToSet = Polymer.dom(this.root).querySelectorAll(".title");
    if (title) {
        $(titlesToSet).text($(title).text());
    }

    // Ensure that we only show on run pages
    showOrHideProperties();

    // Fired click event on qa page if the elements exist
    initQADocStrings();
}

function removeFlashes() {
    /* Removes flash after 5 seconds to avoid confusion */
    /* From: https://www.sitepoint.com/community/t/hide-div-after-10-seconds/5910 */
    console.log("running removeFlashes()");
    setTimeout(function() {
        var flashes = document.getElementById("flashes")
        if (flashes != null)
        {
            flashes.style.display = "none";
        }
    }, 5000);
}

function handleFormSubmit(selectedForm, selectedButton) {
    var button = Polymer.dom(this.root).querySelector("#" + selectedButton);
    console.log("button: " + $(button).text());
    $(button).click(function() {
        //var form = Polymer.dom(this.root).querySelector("#" + selectedForm);
        var form = document.querySelector("#" + selectedForm);
        console.log("form: " + $(form).text());
        form.submit();
    });
}

function handleToggle(selectedToggle) {
    // NOTE: If no local storage, then both jsroot and ajax are enabled. However, it should be
    // fairly unlikely to encounter such a environment now
    var returnValue = true;
    if (storageAvailable("localStorage")) {
        var toggle = Polymer.dom(this.root).querySelector("#" + selectedToggle);
        // Check for value in local storage, and set it properly if it exists
        var storedToggleValue = localStorage.getItem(selectedToggle);
        if (storedToggleValue) {
            // See: https://stackoverflow.com/a/264037
            $(toggle).prop("checked", (storedToggleValue === "true"));

            console.log("Local storage checked for " + selectedToggle +": " + localStorage.getItem(selectedToggle));
        }

        // Storage the change value in local storage
        $(toggle).click(function() {
            // Store value in local storage
            localStorage.setItem(selectedToggle, $(this).prop("checked").toString());

            console.log("Local storage checked for " + selectedToggle +": " + localStorage.getItem(selectedToggle));
        });

        returnValue = $(toggle).prop("checked");
    }
    else {
        console.log("ERROR: Local storage not supported!");
    }

    return returnValue;
}

function setupDialog(buttonSelector, dialogSelector, relativePosition) {
    // Retrieve objects
    //var propertiesButton = document.getElementById("buttonSelector");
    var button = Polymer.dom(this.root).querySelector("#" + buttonSelector);
    //var propertiesDialog = document.getElementById("dialogSelector");
    var dialog = Polymer.dom(this.root).querySelector("#" + dialogSelector);
    
    //console.log("button: " + button + " dialog: " + dialog);

    // Add click listener
    $(button).click(function() {
    //button.addEventListener("click", function() {
        dialog.open();
    });

    // Assign the position target of the dialog
    if (relativePosition === true)
    {
        $(dialog).prop("positionTarget", button);
    }
}

function showOrHideProperties() {
    var properties = Polymer.dom(this.root).querySelector("#propertiesButton");
    var currentPage = window.location.pathname;
    console.log("currentPage: " + currentPage);
    if (currentPage.search("runPage") !== -1) {
        console.log("Showing properties button");
        $(properties).removeClass("hideElement");
    }
    else {
        console.log("Hiding properties button");
        $(properties).addClass("hideElement");
    }
}

// Hide the menu button if in the wide display!
function showOrHideMenuButton() {
    var menuButton = Polymer.dom(this.root).querySelector("#headerMenuButton");
    var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
    //console.log("menuButton: " + menuButton.outerHTML);
    console.log("drawer narrow: " + $(drawer).prop("narrow"));
    if ($(drawer).prop("narrow") === true) {
        $(menuButton).removeClass("hideElement");
        console.log("Removing hideElement");
    }
    else {
        $(menuButton).addClass("hideElement");
        console.log("Adding hideElement");
    }
}

function routeLinks() {
    //var drawer = Polymer.dom(this.root).querySelector("#drawerContent");
    var linksToIntercept = Polymer.dom(this.root).querySelectorAll(".linksToIntercept");
    //var allLinks = Polymer.dom(drawer).querySelectorAll("a");
    //console.log("allLinks: " + allLinks);
    //console.log("linksToIntercept: " + linksToIntercept);
    //console.log("linksToIntercept[0]: " + linksToIntercept[0].outerHTML);
    //console.log("drawer: " + drawer);
    //$(allLinks).click(function(event) {
    // Uses event delegation
    //$(drawer).on("click", "a", function(event) {
    $(linksToIntercept).on("click", "a", function(event) {
        // Prevent the link from being evaluated directly
        event.preventDefault();

        var currentTarget = event.currentTarget;
        console.log("current target: " + $(currentTarget).text());

        // Handles qa function descriptions
        if ($(currentTarget).hasClass("qaFunctionSelector")) {
            handleQADocStrings(currentTarget);
        }
        else {
            // Handles general requests
            console.log("this: " + $(this).text());

            // Get the current page
            var currentPage = window.location.pathname;
            console.log("currentPage: " + currentPage);

            // Determine where the request should be routed
            var pageToRequest = $(this).attr("href");
            console.log("pageToRequest: " + pageToRequest);
            if (pageToRequest === "#") {
                // Request the current page again with the proper GET request instead of with a #
                console.log("Routing the requesting to the address of the current page.");
                pageToRequest = currentPage;
            }

            // Determine parameters for the request
            // Get hist group name
            var histGroupName = $(this).data("histgroup");
            // Get histogram name
            var histName = $(this).data("histname");
            /*console.log("histGroupName: " + histGroupName);
            console.log("histName: " + histName);*/

            // jsRoot and ajax will be added when handling the general request
            var params = {
                histGroup: histGroupName,
                histName: histName
            };

            // Handle the general request
            handleGeneralRequest(params, pageToRequest);

            // Update the history using the HTML5 history API
            // We only do this here because we don't want to update the history when going backwards and forwards.
            // The condition does not include jsRoot, because if it is the only defined parameter, then we just
            // want to hide it. The value will be picked up for the toggle by the time of the request.
            if (!(params.histGroup === undefined && params.histName === undefined)) {
                // Uses a relative path
                window.history.pushState(params, "Title", "?" + jQuery.param(params));
            }
            else {
                // Uses a absolute path
                window.history.pushState(params, "Title", pageToRequest);
            }

            // Prevent further action
            return false;
        }
    });
}

function ajaxRequest(pageToRequest, params) {
    // Call ajax
    // See: https://stackoverflow.com/a/788501
    console.log("Sending ajax request to " + pageToRequest);

    // Params is copied by reference, so we need to copy the object explicitly
    // Careful with this approach! It will mangle many objects, but it is fine for these purposes.
    // See: https://stackoverflow.com/a/5344074
    var localParams = JSON.parse(JSON.stringify(params));
    // Set that we are sending an ajax request
    localParams.ajaxRequest = true;

    // Make the actual request and handle the return
    $.get($SCRIPT_ROOT + pageToRequest, localParams, function(data) {
        // data is already JSON!
        console.log(data)

        // Replace the drawer content if we received a meaingful response
        var drawerContent = $(data).prop("drawerContent");
        // console.log("drawerContent " + drawerContent);
        if (drawerContent !== undefined)
        {
            //console.log("Replacing drawer content!");
            var drawerContainer = Polymer.dom(this.root).querySelector("#drawerContent");
            $(drawerContainer).html(drawerContent);
        }

        // Replace the main content if we received a meaingful response
        var mainContent = $(data).prop("mainContent");
        //console.log("mainContent: " + mainContent);
        if (mainContent !== undefined)
        {
            //console.log("Replacing main content!");
            var mainContainer = Polymer.dom(this.root).querySelector("#mainContent");
            $(mainContainer).html(mainContent);
        }

        // Handle page initialization
        // Note that this could create some additional ajax requests via jsRoot
        initPage(localParams.jsRoot);

        // Update the drawer width
        // Code works, but the drawer does not handle this very gracefully.
        // Better to leave this disabled.
        /*var drawerWidthObject = Polymer.dom(this.root).querySelector("#drawerWidth");
        var drawerWidth = $(drawerWidth).data("width");
        var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
        $(drawer).prop("drawerWidth", drawerWidth);*/
    });

    return localParams;
}

function jsRootRequest() {
    console.log("Handling js root request!");
    var requestedHists = Polymer.dom(this.root).querySelectorAll(".histogramContainer");

    $(requestedHists).each(function() {
        // TODO: Improve the robustness here
        requestAddress = $(this).data("filename");
        requestAddress = "/monitoring/protected/" + requestAddress;
        console.log("requestAddress: " + requestAddress);
        //console.log("this: " + $(this).toString());
        var idToDrawIn = $(this).attr("id");
        console.log("idToDrawIn:" + idToDrawIn);
        // Reason that [0] is needed is currently unclear!
        var objectToDrawIn = $(this)[0];
        var req = JSROOT.NewHttpRequest(requestAddress, 'object', function(canvas) {
            // Plot the hist
            // Allow the div to resize properly
            // TODO: Improve registration with Polymer size changes!
            // It currently doesn't work and generates errors on some reloads, so disable for now
            //JSROOT.RegisterForResize(objectToDrawIn);
            // The 2 corresponds to the 2x2 grid above
            //if (layout != null) { console.log("2x2 this.cnt % 2: " + this.cnt); frame = layout.FindFrame("item" + this.cnt , true) }

            // redraw canvas at specified frame
            JSROOT.redraw(objectToDrawIn, canvas, "colz");
        });

        req.send(null);
    });
}

function initQADocStrings() {
    // Fire click event if the qa function docstrings exists so that it will show one on page load
    var qaFunctionSelector = Polymer.dom(this.root).querySelector(".qaFunctionSelector");
    if (qaFunctionSelector !== null)
    {
        // Fire event
        $(qaFunctionSelector).trigger("click");
    }
}

function handleQADocStrings(currentTarget) {
    // Hide previous docstring
    var hideDocstring = Polymer.dom(this.root).querySelector(".showDocstring");
    if (hideDocstring !== null) {
        $(hideDocstring).removeClass("showDocstring");
        $(hideDocstring).addClass("hideElement");
    }

    // Show new docstring
    var funcName = $(currentTarget).data("funcname");
    var subsystem = $(currentTarget).data("subsystem");
    var targetDocstring = Polymer.dom(this.root).querySelector("#" + subsystem + funcName);
    if (targetDocstring !== null) {
        //console.log("targetDocstring: " + $(targetDocstring).text());
        $(targetDocstring).removeClass("hideElement");
        $(targetDocstring).addClass("showDocstring");
    }
    else {
        console.log("Target docstring #" + subsystem + funcName + "is null! Cannot set docstring!");
    }
}

// This function is only called when navigating within the site
function handleChangeInHistory(eventState) {
    var state = eventState.state;
    console.log("eventState: " + JSON.stringify(state));

    handleGeneralRequest(state);
}

function handleGeneralRequest(params, pageToRequest) {
    // Allow pageToRequest to be optional
    // See: https://stackoverflow.com/a/894877
    pageToRequest = typeof pageToRequest !== 'undefined' ? pageToRequest : window.location.pathname;

    console.log("params passed for general request: " + JSON.stringify(params));

    // Params are empty so we need to do a general request. In that case, we want an empty object
    if (params === null) {
        params = {};
    }

    // ajax toggle status and convert it to bool
    var ajaxToggle = Polymer.dom(this.root).querySelector("#ajaxToggle");
    var ajaxState = ($(ajaxToggle).prop("checked") === true);
    // jsRoot toggle status and convert it to bool
    var jsRootToggle = Polymer.dom(this.root).querySelector("#jsRootToggle");
    var jsRootState = ($(jsRootToggle).prop("checked") === true);
    /*console.log("ajaxState: " + ajaxState);
    console.log("jsRootState: " + jsRootState);*/

    // This will ignore whatever was sent in the parameters and use whatever value the user has set.
    // However, this seems preferable, because different users may have different desired settings,
    // and it would be nice if the links adapted.
    params.jsRoot = jsRootState;

    console.log("params for general request: " + JSON.stringify(params));

    if (ajaxState === false || pageToRequest.search("logout") !== -1) {
        console.log("ajax disabled link");

        // This should never fall through since jsRoot should always be defined, but it is left to be careful.
        if (!(params.histGroup === undefined && params.histName === undefined && params.jsRoot === undefined)) {
            console.log("Assigning parameters to href");
            pageToRequest += "?" + jQuery.param(params);
        }
        else {
            console.log("ERROR: No parameters to assign");
        }

        // Assign the page (which will send it to the specified link)
        console.log("Requesting page: " + pageToRequest);
        window.location.href = pageToRequest;

    }
    else {
        console.log("ajax enabled link");
        // We don't want to take the returned params variable, because adding the ajaxRequest setting to the url
        // will often break loading the page from a link (ie it will only return the drawer and main content,
        // which we don't want in that situation).
        ajaxRequest(pageToRequest, params);
    }
}

function collapsibleContainers() {
    //var containers = Polymer.dom(this.root).querySelectorAll(".collapsibleContainerButton");
    var containers = Polymer.dom(this.root).querySelectorAll("#mainContent");

    //$(containers).on("click", function(event) {
    $(containers).on("click", ".collapsibleContainerButton", function(event) {
        // Prevent the link while we change where it is going
        event.preventDefault();

        var currentTarget = event.currentTarget;
        console.log("current target: " + $(currentTarget).text());

        // Collapsible container
        var containerName = $(currentTarget).attr("id").replace("Button", "");
        console.log("containerName: " + containerName);

        // Toggle container
        // Polyer.dom() does not work for some reason...
        //var container = Polymer.dom(this.root).querySelector("#" + containerName);
        var container = $(currentTarget).siblings("#" + containerName);
        container.toggle();

        // Toggle icon
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

// Check for local storage being available
// From: https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API
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

