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

    // Ensure that we only show on run pages
    showOrHideProperties();

    // Handle toggle value
    handleToggle("jsRootToggle");
    handleToggle("ajaxToggle");

    // Remove flask flashes after a short period to ensure that it doens't clutter the screen
    removeFlashes();
    testAjax();

    // Ensure that all links are routed properly (either through ajax or a normal link)
    interceptLinks();
});

function removeFlashes() {
    /* Removes flash after 5 seconds to avoid confusion */
    /* From: https://www.sitepoint.com/community/t/hide-div-after-10-seconds/5910 */
    console.log("running removeFlashes()");
    setTimeout(function() {
        var flashes = document.getElementById("flashes")
        if (flashes != null)
        {
            flashes.style.display="none"
        }
    }, 5000)
}

function handleToggle(selectedToggle) {
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
    }
    else {
        console.log("ERROR: Local storage not supported!");
    }
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

/* inputValue is needed for the template, where we can't set anchors */
function scrollIfHashExists(inputValue) {
    /* Not using default values in the function call because of https://stackoverflow.com/a/14657153 */
    /* If value is set test from: https://stackoverflow.com/a/6486357 */
    console.log(typeof(inputValue) !== "undefined");
    console.log(window.location.hash === "");
    console.log(window.location.href.search("timeSlices") !== -1);

    /* Only want to set if the hash is not set. If it is set, then we should ignore the value */
    /* since the hash was requested explicitly */
    if (typeof(inputValue) !== "undefined" && window.location.hash === "" && window.location.href.search("timeSlices") !== -1)
    {
        console.log("setting hash");
        window.location.hash = "scrollTo" + inputValue;
    }

    /* Scroll based on the value set in the hash value */
    var hashValue = window.location.hash;
    console.log(hashValue);
    if (hashValue.search("scrollTo") != -1)
    {
        /* + 8 since search returns the start of the first instance and "scrollTo" is length 8 */
        var scrollValue = hashValue.substring(hashValue.search("scrollTo") + 8);
        console.log("Scrolling to " + scrollValue);
        /* scrollTo(x, y) */
        window.scrollTo(0, scrollValue);

        /* Display the merge information if on mobile by showing the menu. */
        /* The menu icon will be floating right if we are on mobile. */
        /* NOTE: There should only be one menuIcon, so we should be okay directly accessing it. */
        var menuIcon = document.getElementsByClassName("menuIcon");
        if (menuIcon.length === 1 && menuIcon[0] !== null && window.getComputedStyle(menuIcon[0]).float === "right")
        {
            /* Show the menu by checking the checkmark so that the partial merge information is shown */
            console.log("Showing menu!");
            var menuToggle = document.getElementById("menuToggle");
            menuToggle.checked = true;
        }
    }
}

/* Set value of how far the user has scrolled on submit of form */
/* From: https://stackoverflow.com/a/4517530 */
function setScrollValueInForm() {
    /* When this function is called, time dependent merge should always exist, but it is best to check */
    console.log("Checking if time dependent merge exists!");
    if (document.getElementById("timeDependentMergeControls") != null)
    {
        console.log("timeDependentMerge exists");
        /* Registers to change the value on submit, but before the POST is actually sent. */
        document.getElementById("timeDependentMergeControls").onsubmit = function() {
            /* From: https://stackoverflow.com/a/11373834 */
            /* Distance from top of page */
            var scrollTop = (window.pageYOffset !== undefined) ? window.pageYOffset : (document.documentElement || document.body.parentNode || document.body).scrollTop;
            console.log(scrollTop);
            /* Set the value in the form */
            var inputInForm = document.getElementById("scrollAmount");
            console.log(inputInForm);
            if (inputInForm != null)
            {
                inputInForm.value = scrollTop;
            }
            console.log("scroll value is: " + scrollTop);
            console.log(document.getElementById("scrollAmount").value);
        }
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

function interceptLinks() {
    var drawer = Polymer.dom(this.root).querySelector("#drawerContent");
    var linksToIntercept = Polymer.dom(this.root).querySelectorAll(".linksToIntercept");
    var allLinks = Polymer.dom(drawer).querySelectorAll("a");
    console.log("allLinks: " + allLinks);
    //console.log("linksToIntercept: " + linksToIntercept);
    //console.log("linksToIntercept[0]: " + linksToIntercept[0].outerHTML);
    console.log("drawer: " + drawer);
    //$(allLinks).click(function(event) {
    // Uses event delegation
    //$(drawer).on("click", "a", function(event) {
    $(linksToIntercept).on("click", "a", function(event) {
        var ajaxToggle = Polymer.dom(this.root).querySelector("#ajaxToggle");

        // Get hist group
        var histGroupName = $(this).data("histgroup");
        console.log("histGroupName: " + histGroupName);
        // Get histogram
        var histName = $(this).data("histname");
        console.log("histName: " + histName);

        // jsRoot toggle
        var jsRootToggle = Polymer.dom(this.root).querySelector("#jsRootToggle");
        var jsRoot = ($(jsRootToggle).prop("checked") === true);
        console.log("jsRoot: " + jsRoot);

        var params = jQuery.param({
            jsRoot: jsRoot,
            histGroup: histGroupName,
            histName: histName
        });

        console.log("params: " + params);
        if (ajaxToggle.checked === false) {
            console.log("ajax disabled link");

            // Prevent the link while we change where it is going
            event.preventDefault();

            // Get the current page
            var currentPage = window.location.pathname;
            console.log("currentPage: " + currentPage);

            var pageToRequest = $(this).attr("href");
            console.log("pageToRequest: " + pageToRequest);
            if (pageToRequest === "#") {
                // Request the current page again with the proper GET request
                pageToRequest = currentPage;
            }

            if (!(histGroupName === undefined && histName === undefined)) {
                console.log("Assigning parameters to href");
                pageToRequest += "?" + params;
                // TEST
                //pageToRequest += "#";
            }
            else {
                console.log("No parameters to assign");
            }

            // Assign the page (which will send it to the specified link)
            window.location.href = pageToRequest;

            // TODO: Update this more carefully to avoid adding unnecessary parameters
            // Normalize to the html5 history
            //var appendTohref = window.location.href;
            // Used since href contains the previous parameters
            // See: https://stackoverflow.com/a/6257480
            /*var appendTohref = window.location.protocol + "//" + window.location.host + window.location.pathname;
            console.log("appendTohref: " + appendTohref);
            appendTohref += "?";
            appendTohref += params;
            console.log("appendTohref: " + appendTohref);
            window.location.href = appendTohref;*/
            //window.location.hash = hash;
        }
        else {
            console.log("ajax enabled link");
            console.log("this: " + $(this).text());
            console.log("current target: " + $(event.currentTarget).text());
            // Prevent the link from going through
            event.preventDefault();

            // Get the current page
            var currentPage = window.location.pathname;
            console.log("currentPage: " + currentPage);

            var pageToRequest = $(this).attr("href");
            console.log("pageToRequest: " + pageToRequest);
            if (pageToRequest === "#") {
                // Request the current page again with the proper GET request
                pageToRequest = currentPage;
            }

            // Call ajax
            // See: https://stackoverflow.com/a/788501
            console.log("Sending ajax request to " + pageToRequest);
            $.get($SCRIPT_ROOT + pageToRequest, {
                ajaxRequest: true,
                jsRoot: jsRoot,
                histName: histName,
                histGroup: histGroupName
            }, function(data) {
                // Already JSON!
                console.log(data)
                var drawerContent = $(data).prop("drawerContent");
                //console.log("drawerContent " + drawerContent);
                if (drawerContent !== undefined)
                {
                    console.log("Replacing drawer content!");
                    var drawerContainer = Polymer.dom(this.root).querySelector("#drawerContent");
                    $(drawerContainer).html(drawerContent);
                }
                var mainContent = $(data).prop("mainContent");
                //console.log("mainContent: " + mainContent);
                if (mainContent !== undefined)
                {
                    console.log("Replacing main content!");
                    var mainContainer = Polymer.dom(this.root).querySelector("#mainContent");
                    $(mainContainer).html(mainContent);
                }
                //$("#mainCont").replaceWith(data);
                
                // Setup jsRoot and get images
                if (jsRoot === true)
                {
                    console.log("Handling js root request!");
                    var requestedHists = Polymer.dom(this.root).querySelectorAll(".histogramContainer");

                    $(requestedHists).each(function() {
                        // TODO: Improve the robustness here
                        requestAddress = $(this).data("filename");
                        requestAddress = "/monitoring/protected/" + requestAddress;
                        console.log("requestAddress: " + requestAddress);
                        console.log("this: " + $(this).toString());
                        var idToDrawIn = $(this).attr("id");
                        console.log("idToDrawIn:" + idToDrawIn);
                        var req = JSROOT.NewHttpRequest(requestAddress, 'object', function(canvas) {
                            // Plot the hist
                            var frame = idToDrawIn;
                            console.log("frame: " + frame);
                            // Allow the div to resize properly
                            JSROOT.RegisterForResize("test");
                            //JSROOT.RegisterForResize(frame);
                            // The 2 corresponds to the 2x2 grid above
                            //if (layout != null) { console.log("2x2 this.cnt % 2: " + this.cnt); frame = layout.FindFrame("item" + this.cnt , true) }

                            // redraw canvas at specified frame
                            JSROOT.redraw(frame, canvas, "colz");

                        });

                        req.send(null);
                    });
                }

                // Update the title
                var title = Polymer.dom(this.root).querySelector("#mainContentTitle");
                var titlesToSet = Polymer.dom(this.root).querySelectorAll(".title");
                $(titlesToSet).text($(title).text());

                // Remove the properties button if necessary
                showOrHideProperties();

                // Update the drawer width
                // Code works, but the drawer does not handle this very gracefully.
                // Better to leave this disabled.
                /*var drawerWidthObject = Polymer.dom(this.root).querySelector("#drawerWidth");
                var drawerWidth = $(drawerWidth).data("width");
                var drawer = Polymer.dom(this.root).querySelector("#drawerPanelId");
                $(drawer).prop("drawerWidth", drawerWidth);*/
            });

            // Update the hash
            //var href = $(this).attr("href");
            //console.log("href: " + href)
            //window.location.hash = href;

            // Update the current link
            //window.location.href += "?" + params;
            // See: https://stackoverflow.com/a/5607923
            console.log("histGroupName: " + histGroupName);
            if (!(histGroupName === undefined && histName === undefined)) {
                // Uses a relative path
                window.history.pushState("string", "Title", "?" + params);
            }
            else {
                // Uses a absolute path
                window.history.pushState("string", "Title", pageToRequest);
            }

            // Prevent further action
            return false;
        }
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

function testAjax() {
    $('a#testAjax').bind('click', function() {
        $.get($SCRIPT_ROOT + '/testAjax', {
            a: "testA",
            b: "testB"
        }, function(data) {
            console.log(data)
            $("#mainCont").replaceWith(data);
            //$("#mainCont").append(data);
        });
        return false;
    });
}

