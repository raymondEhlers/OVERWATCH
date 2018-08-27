# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../overwatch'))


# -- Project information -----------------------------------------------------

project = 'ALICE Overwatch'
copyright = '2015-2018, Raymond Ehlers, James Mulligan'
author = 'Raymond Ehlers, James Mulligan'

# The short X.Y version
version = '1.0'
# The full version, including alpha/beta/rc tags
release = 'v1.0'


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_markdown_tables',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# Add markdown support
source_parsers = {
   '.md': 'recommonmark.parser.CommonMarkParser',
}

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of strings
source_suffix = ['.rst', ".md"]

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store',
        "CHEP",
        "planning",
        "logo",
        "README.md" # This is a README for the docs generation, so it shouldn't be included in the generated docs
    ]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
        "github_user": "raymondEhlers",
        "github_repo": "OVERWATCH",
        "github_type": "star",
        "github_banner": True,
        "logo" : "overwatchLogo.v1.svg",
        "show_powered_by": False
    }

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
html_sidebars = {
        # Two starts is extremely important! Otherwise, it won't apply the navigation bar
        # to pages further down in the docs, like in the api folder.
        "**" : [
            "about.html",
            "navigation.html",
            "relations.html",
            "searchbox.html"
        ]
    }


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'ALICEOverwatchdoc'


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'ALICEOverwatch.tex', 'ALICE Overwatch Documentation',
     'Raymond Ehlers, James Mulligan', 'manual'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'aliceoverwatch', 'ALICE Overwatch Documentation',
     [author], 1)
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'ALICEOverwatch', 'ALICE Overwatch Documentation',
     author, 'ALICEOverwatch', 'One line description of project.',
     'Miscellaneous'),
]


# -- Extension configuration -------------------------------------------------

# Mock modules which won't be available when reading the docs
# See: https://docs.readthedocs.io/en/latest/faq.html#i-get-import-errors-on-libraries-that-depend-on-c-modules
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

# root isn't available on RTD, and a flask-zodb that is python 3 compatiable isn't available on PyPI, so
# we can't install it as easily. This works fine for our purposes.
MOCK_MODULES = ["ROOT", "flask_zodb"]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

