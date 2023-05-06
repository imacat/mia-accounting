Introduction
============

*Mia! Accounting* is an accounting module for Flask_ applications.
It is designed both for mobile and desktop environments.  It
implements `double-entry bookkeeping`_.  It generates the following
accounting reports:

* Trial balance
* Income statement
* Balance sheet

In addition, *Mia! Accounting* tracks offsets for unpaid payables and
receivables.


Live Demonstration and Test Site
--------------------------------

There is a `live demonstration`_ for *Mia! Accounting*.  It runs the
same code as the `test site`_ in the `source distribution`_.  It is
the simplest website that works with *Mia! Accounting*.  It is also
used in the automatic tests.

If you do not have a running Flask application or do not know how to
start one, you may start with the test site.


Installation
------------

Install *Mia! Accounting* with ``pip``:

::

    pip install mia-accounting

You may also download from the `PyPI project page`_ or the
`release page`_ on the `Git repository`_.


Prerequisites
-------------

You need a running Flask application with database user login.
The primary key of the user data model must be integer.  You also
need at least one user.

The following front-end JavaScript libraries must be loaded.  You may
download it locally or use CDN_.

* Bootstrap_ 5.2.3 or above
* FontAwesome_ 6.4.0 or above
* `decimal.js`_ 10.4.3 or above, or `decimal.js-light`_ 2.5.1 or above.
* `Tempus-Dominus`_ 6.7.7 or above


Configuration
-------------

You need to pass the Flask *app* and an implementation of
:py:class:`accounting.utils.user.UserUtilityInterface` to the
:py:func:`accounting.init_app` function.  ``UserUtilityInterface``
contains everything *Mia! Accounting* needs.

See an example in :ref:`example-userutils`.


Database Initialization
-----------------------

After the configuration, run the ``accounting-init-db`` console
command to initialize the accounting database.  You need to specify
the username of a user as the data creator.

::

    % flask --app myapp accounting-init-db -u username


Navigation Menu
---------------

Include the navigation menu in the `Bootstrap navigation bar`_ in your
base template:

::

    <nav class="navbar navbar-expand-lg bg-body-tertiary bg-dark navbar-dark">
      <div class="container-fluid">
        ...
        <div id="collapsible-navbar" class="collapse navbar-collapse">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
            ...
            {% include "accounting/include/nav.html" %}
            ...
          </ul>
          ...
        </div>
      </div>
    </nav>

Check your Flask application and see how it works.


.. _Flask: https://flask.palletsprojects.com
.. _double-entry bookkeeping: https://en.wikipedia.org/wiki/Double-entry_bookkeeping
.. _live demonstration: https://accounting.imacat.idv.tw
.. _test site: https://github.com/imacat/mia-accounting/tree/main/tests/test_site
.. _source distribution: https://pypi.org/project/mia-accounting/#files
.. _PyPI project page: https://pypi.org/project/mia-accounting
.. _release page: https://github.com/imacat/mia-accounting/releases
.. _Git repository: https://github.com/imacat/mia-accounting
.. _CDN: https://en.wikipedia.org/wiki/Content_delivery_network
.. _Bootstrap: https://getbootstrap.com
.. _FontAwesome: https://fontawesome.com
.. _decimal.js: https://mikemcl.github.io/decimal.js
.. _decimal.js-light: https://mikemcl.github.io/decimal.js-light
.. _Tempus-Dominus: https://getdatepicker.com
.. _Bootstrap navigation bar: https://getbootstrap.com/docs/5.3/components/navbar/
