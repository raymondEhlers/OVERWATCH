.. _documentation:

Documentation
=============

Documentation on the modules of the Overwatch package are available below. For any code contributions, please
be certain to document:

* New functions, arguments, and classes.
* New attributes of classes.
* New modules (for example, an additional subsystem).

All of the above can be documented in the source, with the exception of adding new modules to the docs. The
new modules must be added in the ``docs/api`` folder.

Module are list below by the order of their inheritance, with the bottom most module depending on every module
above it (the ``overwatch.receiver`` module is the exception - it only depends on ``overwatch.base``).

.. toctree::
   :maxdepth: 3

   api/overwatch.base
   api/overwatch.processing
   api/overwatch.processing.detectors
   api/overwatch.webApp
   api/overwatch.receiver

Some additional helpful links:

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
