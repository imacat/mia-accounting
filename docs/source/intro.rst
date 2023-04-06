Introduction
============

*Mia! Accounting* is an accounting module for Flask_ applications.
It implements `double-entry bookkeeping`_, and generates the following
accounting reports:

* Trial balance
* Income statement
* Balance sheet

In addition, *Mia! Accounting* tracks offsets for unpaid payables and
receivables.

You may try the `live demonstration`_.


Installation
------------

Install *Mia! Accounting* with ``pip``:

::

    pip install mia-accounting

You may also download the from the `PyPI project page`_ or the
`release page`_ on the `Git repository`_.


Prerequisites
-------------

You need a running Flask application with database user login.
The primary key of the user data model must be integer.

The following front-end JavaScript libraries must be loaded.  You may
download it locally or use CDN_.

* Bootstrap_ 5.2.3 or above
* FontAwesome_ 6.2.1 or above
* `Decimal.js`_ 6.4.3 or above
* `Tempus-Dominus`_ 6.4.3 or above


Configuration
-------------

You need to pass the Flask *app* and an implementation of
:py:class:`accounting.utils.user.UserUtilityInterface` to the
:py:func:`accounting.init_app` function.  ``UserUtilityInterface``
contains everything *Mia! Accounting* needs.

See an example in :ref:`example-userutils`.


Database Initialization
-----------------------

After the configuration, you need to run
`flask_sqlalchemy.SQLAlchemy.create_all`_ to create the
database tables that *Mia! Accounting* uses.

*Mia! Accounting* adds three console commands:

* ``accounting-init-base``
* ``accounting-init-accounts``
* ``accounting-init-currencies``

After database tables are created, run
``accounting-init-base`` first, and then the other two commands.

::

    % flask --app myapp accounting-init-base
    % flask --app myapp accounting-init-accounts
    % flask --app myapp accounting-init-currencies


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


Test Site and Live Demonstration
--------------------------------

You may find a working example in the `test site`_ in the
`source distribution`_.  It is the simplest website that works with
*Mia! Accounting*.  It is used in the automatic tests.  It is the same
code run for `live demonstration`_.

If you do not have a running Flask application, you may start with the
test site.


Documentation
-------------

Refer to the `documentation on Read the Docs`_.


.. _Flask: https://flask.palletsprojects.com
.. _double-entry bookkeeping: https://en.wikipedia.org/wiki/Double-entry_bookkeeping
.. _live demonstration: https://accounting.imacat.idv.tw
.. _PyPI project page: https://pypi.org/project/mia-accounting
.. _release page: https://github.com/imacat/mia-accounting/releases
.. _Git repository: https://github.com/imacat/mia-accounting
.. _CDN: https://en.wikipedia.org/wiki/Content_delivery_network
.. _Bootstrap: https://getbootstrap.com
.. _FontAwesome: https://fontawesome.com
.. _Decimal.js: https://mikemcl.github.io/decimal.js
.. _Tempus-Dominus: https://getdatepicker.com
.. _flask_sqlalchemy.SQLAlchemy.create_all: https://flask-sqlalchemy.palletsprojects.com/en/3.0.x/api/#flask_sqlalchemy.SQLAlchemy.create_all
.. _Bootstrap navigation bar: https://getbootstrap.com/docs/5.3/components/navbar/
.. _test site: https://github.com/imacat/mia-accounting/tree/main/tests/test_site
.. _source distribution: https://pypi.org/project/mia-accounting/#files
.. _documentation on Read the Docs: https://mia-accounting.readthedocs.io
