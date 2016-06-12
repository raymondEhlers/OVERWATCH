/* TODO: Remove some debug messages! */

// Handle all of the polymer elements!
// To ensure that elements are ready on polyfilled browsers, wait for WebComponentsReady. 
document.addEventListener('WebComponentsReady', function() {
    // Enable the link for the menu button to control the drawer
    var menuButton = document.getElementById("headerMenuButton");
    var drawer = document.getElementById("drawerPanelId");
    //console.log("panelButton: " + menuButton.outerHTML);
    // Create toggle for the drawer button
    menuButton.addEventListener("click", function() {
        drawer.togglePanel();
    });

    // Create the link for opening the time slices dialog panel
    var propertiesButton = document.getElementById("propertiesButton");
    var propertiesDialog = document.getElementById("propertiesDialog");
    //console.log("button: " + propertiesButton + " dialog: " + propertiesDialog.outerHTML);
    propertiesButton.addEventListener("click", function() {
        propertiesDialog.open();
    });

    // Create the link for opening the user settings dialog panel
    var userSettingsButton = document.getElementById("userSettingsButton");
    var userSettings = document.getElementById("userSettings")
    userSettingsButton.addEventListener("click", function() {
        userSettings.open();
    })
    // Assign the position target of the settings
    // Don't currently need it because it is positioned correctly
    userSettings.positionTarget = userSettingsButton;

    // Ensure that we show or hide the menu button on load
    showOrHideMenuButton();
    // Add a listener for further changes
    document.addEventListener("paper-responsive-change", showOrHideMenuButton);

    // Handle jsRoot value
    if (storageAvailable("localStorage")) {
        var jsRootToggle = document.getElementById("jsRootToggle");
        // Check for value in local storage, and set it properly if it exists
        var storedToggleValue = localStorage.getItem("jsRootToggle");
        if (storedToggleValue) {
            // See: https://stackoverflow.com/a/264037
            jsRootToggle.checked = (storedToggleValue === "true");

            console.log("Local storage checked: " + localStorage.getItem("jsRootToggle"));
        }

        // Storage the change value in local storage
        jsRootToggle.addEventListener("change", function(e) {
            // Store value in local storage
            //console.log("checked: " + e.target.checked);
            localStorage.setItem("jsRootToggle", e.target.checked.toString());
            //console.log("Local storage checked: " + localStorage.getItem("jsRootToggle"));
        });
    }

    removeFlashes();
    testAjax();
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

// Hide the menu button if in the wide display!
function showOrHideMenuButton() {
    //console.log("narrow: " + e.target.narrow);
    var menuButton = document.getElementById("headerMenuButton");
    var drawer = document.getElementById("drawerPanelId");
    //console.log("drawer: " + drawer);
    //if (e.target.narrow === true) {
    if (drawer.narrow === true) {
        /*menuButton.style.visibility = "visible";*/
        menuButton.style.display = "inline-block";
    }
    else {
        /*menuButton.style.visibility = "hidden";*/
        menuButton.style.display = "none";
    }
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

