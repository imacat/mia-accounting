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

You may try the `Mia! Accounting live demonstration`_.


History
-------

I created my own private accounting application in Perl_/mod_perl_ in
2007, as part of my personal website.  The first revision was made
using Perl/Mojolicious_ in 2019, with the aim of making it
mobile-friendly using Bootstrap_, and with modern back-end and
front-end technologies such as jQuery.

The second revision was done in Python_/Django_ in 2020, as I was
looking to change my career from PHP_/Laravel_ to Python, but lacked
experience with large Python projects.  I wanted to add something new
to my portfolio and decided to work on the somewhat outdated
Mojolicious project.

Despite having no prior experience with Django, I spent two months
working late nights to create the `Mia! Account Django application`_.
It took me another 1.5 months to make it an independent module, which
I later released as an open source project.

The application worked nicely for my household bookkeeping for two
years.  However, new demands arose over time, especially with tracking
payables and receivables, which became difficult with credit card
payments.  This was critical `during the pandemic`_ as more payments
were made online with credit cards.

The biggest issue I encountered was with Django's MVT framework.  Due
to my lack of experience with Django during development, I ended up
with mixed function-based view controllers and class-based views.  It
became very difficult to track whether problems originated from my
overridden methods or not-overridden methods, or from the Django base
views themselves.  I did not fully understand how everything worked.

Therefore, I decided to turn to microframeworks like Flask.   After
working with modularized Flask and FastAPI_ applications for two
years, I returned to the project and wrote its third revision using
Flask in 2023.


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
:py:meth:`flask_sqlalchemy.SQLAlchemy.create_all` to create the
database tables that *Mia! Accounting* uses.

*Mia! Accounting* adds three console commands:

* ``accounting-init-base``
* ``accounting-init-accounts``
* ``accounting-init-currencies``

You need to run ``accounting-init-base`` first, and then the other
two commands.

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
.. _Mia! Accounting live demonstration: https://accounting.imacat.idv.tw/
.. _Perl: https://www.perl.org
.. _mod_perl: https://perl.apache.org
.. _Mojolicious: https://mojolicious.org
.. _Bootstrap: https://getbootstrap.com
.. _jQuery: https://jquery.com
.. _Python: https://www.python.org
.. _Django: https://www.djangoproject.com
.. _PHP: https://www.php.net
.. _Laravel: https://laravel.com
.. _Mia! Account Django application: https://github.com/imacat/mia-accounting-django
.. _during the pandemic: https://en.wikipedia.org/wiki/COVID-19_pandemic
.. _FastAPI: https://fastapi.tiangolo.com
.. _FontAwesome: https://fontawesome.com
.. _Decimal.js: https://mikemcl.github.io/decimal.js
.. _Tempus-Dominus: https://getdatepicker.com
.. _CDN: https://en.wikipedia.org/wiki/Content_delivery_network
.. _PyPI project page: https://pypi.org/project/mia-accounting
.. _release page: https://github.com/imacat/mia-accounting/releases
.. _Git repository: https://github.com/imacat/mia-accounting
.. _Bootstrap navigation bar: https://getbootstrap.com/docs/5.3/components/navbar/
.. _test site: https://github.com/imacat/mia-accounting/tree/main/tests/test_site
.. _source distribution: https://pypi.org/project/mia-accounting/#files
.. _live demonstration: https://accounting.imacat.idv.tw
.. _documentation on Read the Docs: https://mia-accounting.readthedocs.io
