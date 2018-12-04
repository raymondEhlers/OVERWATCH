# Web App package details

This package encompass the web app functionality provided by Overwatch. This package includes:

- The web app serving modules, including routing requests for time slices and user directed reprocessing.
- The `html` templates for serving the content. The templates use `jinja2`, while the pages themselves are
  built with Google Polymer.
- Overwatch `js` (`shared.js`), `css` (`style.css`), and other static dependencies (`jQuery`, `jsRoot`,
  Google Polymer).

## Page template layout

Web pages are defined via `jinja2` templates. This allows the dynamic determination of content. As an overall
design, `layout.html` is the main shell for all pages. It provides consistent visual presentation through the
entire web app.

Individual pages are designed around three primary templates. For a page named `example`, these three
templates are:

- The page itself, which will be known as `example.html`. This is mostly a thin wrapper around the other
  templates defined below, which can be imported directly via `jinja`. Most of these pages will be approximately
  the same, with the main different being the title for the particular page.
- `exampleMainContent.html`, which contains the main content of the example page. This could be histograms,
  information, etc.
- `exampleDrawer.html`, which contains supplemental information to be displayed in the drawer on the left side of the
  app shell. This could be organizational or navigational information, or information which would want to be
  available at a glance, such as if the run is ongoing.

While this division may be somewhat unconventional, it is beneficial because it allows us to support regular
and AJAX requests with the same underlying content. If a request is made of AJAX, we simply request and
replace the new main content and drawer content directly within the app shell. However, if a full page is
requested, we simply direct to the full template, which will contain the app shell as well as the main and
drawer content.

Note that the page itself could be refactored further to be totally general, but this would require additional
JavaScript development to request and set the page title via AJAX. For our purposes, the code duplication is
worth the savings in development time and complexity.

The pages themselves are designed using Google Polymer v1. Although they do not take advantage of the more
sophisticated features of Polymer, we still benefit heavily because we don't need to worry about the design -
it automatically creates a responsive app shell. We just have to make a few customizations. Ideally, we would
update to the most recent version of Polymer, but as of August 2018, it is not a top priority.

## AJAX and `JSRoot` options

As noted above, all content is built such that it can be requested either as full pages or AJAX. There is a
similar option for using either `JSRoot` or statically generated images. By default, pages are requested via
AJAX and `JSRoot` is used for display. These options can be modified via GET parameters `ajaxRequest` and
`jsRoot`, respectively, in the HTTP request. See the `webApp` and `validation` modules for further details.

## Flask

Flask is a very powerful framework for web apps. The docs are quite good, so they are an excellent place to
start. Since flask is not very opinionated, it is often up to the user to determine the best approach. In
Overwatch, we approach this by using many popular plugins such as `flask-login`, `flask-wtf`, etc, since these
packages probably have a better grasp of the issue than a home written solution.

Information on how we use flask is available below.

### Requests and URL routing

For each route, note that the flask.request object is available with information about the request. In
particular, the `request.args` dictionary is particularly useful, since it provides access to GET parameters
of the request. The `reuest.post` dictionary contains the POST parameters.

When making a request within the web app or a template, remember that the main argument to `url_for(...)` is
the _name_ of the function, not the _path_! Further, named arguments will be passed as GET parameters.

### Error Format

In an effort to improve the user experience around errors, there are a set of templates for displaying error
messages available in `error.html` and the corresponding drawer and main content.

To use these templates, the errors must be constructed according to the dictionary format below. Each type of
error is stored under a category (which is the key) and then the particular error messages are a list (which
is the value). By appending to that list, new error messages won't overwrite existing ones.

```python
>>> # General format:
>>> errors = {'hello2': ['world', 'world2', 'world3'], 'hello': ['world', 'world2']}
>>> # We add an error related to the subsystem. Note that by using `setdefault()`, we can created
>>> # the list if necessary, or if it already exists, simply use that.
>>> # See: https://stackoverflow.com/a/2052206
>>> errors.setdefault("subsystem", []).append("Subsystem name \"EMC\" is not available!")
>>> errors
{'hello2': ['world', 'world2', 'world3'], 'hello': ['world', 'world2'], 'subsystem': ['Subsystem name "EMC" is not available!']}
```

Error handling is built into most routes, so errors will usually be handled seamlessly.

### `flask-webassets`, `webassets` filters, and debugging

Overwatch depends on `webassets` to deploy compiled and minimized files. In particular, the `js` is minimized,
and `polymer-bundler` is employed to compile all of the polymer components into one minimized file to reduce
the number of HTTP requests.

A few number of important notes on usage are below:

- Most filters, including the `polymer-bundler` and `rjsmin` filters, won't build in debug mode!
- Disable caching with the below lines. Put these lines in `overwatch.webApp.webApp` or `overewatch.webApp.run`.
  It is useful for debugging:

    ```python
    >>> assets.cache = False
    >>> assets.manifest = False
    ```

- To debug, you still need to delete and touch the relevant files in between each change. Usually, that means:
    - Counterintuitively, ensure that `flask-assets` debug mode is **disabled**. Otherwise the filters will
      not be run!
    - Deleting the file in the `static/gen/` folder
    - Removing the `static/.webassets` folder if it exists
    - Update or otherwise touch the file of interest (for example, `static/polyerComponents.html`)
- To ease debugging, the debug mode of `flask-assets` can be separately from the overall debug mode via
  the `flaskAssetsDebug` field in the YAML configuration. This allows debug information to flow while still
  causing the filters to run.
- Each Asset won't be built until first access of the particular file. Access the associated `urls` of the
  asset to force it to built immediately (will still only be built if needed or forced by following the
  debug procedure above).

    ```python
    >>> logger.debug(assets["polymerBundle"].urls())
    ```

## Monitoring for errors

It is important to monitor Overwatch for errors and other issues. For the web app, this monitoring is provided
by `sentry`, which hooks into exceptions, logging, and other parts of the app to automatically provide alerts
and information when issues occur.

For successful monitoring, the environment must export the `DSN` as `export SENTRY_DSN_WEBAPP=<value>`. The
value will be some sort of unique URL. Note that this endpoint is just for Overwatch Web App errors (called
`overwatch-webapp` on `sentry`). If it is not available, it will look for the general environment variable
`SENTRY_DSN`.

