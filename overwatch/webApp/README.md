# Web App details

## Notes on `webassets` and `webassets` filters

Overwatch depends on `webassets` to deploy compiled and minimized files. In particular, the `js` is minimized,
and `polymer-bundler` is employed to compile all of the polymer components into one minimized file to reduce
the number of HTTP requests. 

A few number of important notes on usage are below:

- Most filters, including the `polymer-bundler` and `rjsmin` filters, won't build in debug mode!
- Disable caching with the below lines. Put these lines in `overwatch.webApp.webApp` or `overewatch.webApp.run`.
  It is useful for debugging: 

    ``` 
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
  the `flaskAssetsDebug` field in the yaml configuration. This allows debug information to flow while still
  causing the filters to run.
- Each Asset won't be built until first access of the particular file. Access the associated `urls` of the
  asset to force it to built immediately (will still only be built if needed or forced by following the 
  debug procedure above).

    ```
    >>> logger.debug(assets["polymerBundle"].urls())
    ```
