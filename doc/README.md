# Notes on the documentation

Documentation is built via `sphinx`, taking advantage of the auto documentation capabilities. However, this
also requires that the in code documentation is mostly written `ReST`. Note that full markdown documents can
still be included successfully. For example, the main `README.md` is included this way.

## Linking `about.md` to the main `README.md`

It is imperative that this is a file named `about.md` to ensure that the sidebar logo and navigation shows up
properly. This is required by the alabaster theme (although it is not super well documented). For more, see
[this issue](https://github.com/bitprophet/alabaster/issues/86).

## Symlinks

A number of other READMEs and image files are symlinked to other locations in the repository. This is done to
simplify the building of the docs by ensuring that all files that are included in the docs are within the docs
directory.
