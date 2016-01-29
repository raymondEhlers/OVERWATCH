/* TODO: Remove some debug messages! */

function removeFlashes() {
    /* Removes flash after 5 seconds to avoid confusion */
    /* From: https://www.sitepoint.com/community/t/hide-div-after-10-seconds/5910 */
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
