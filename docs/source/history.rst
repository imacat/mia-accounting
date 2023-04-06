History
=======

I created my own private accounting application in Perl_/mod_perl_ in
2007, as part of my personal website.  The first revision was made
using Perl/Mojolicious_ in 2019, with the aim of making it
mobile-friendly using Bootstrap_, and with modern back-end and
front-end technologies such as jQuery.

The second revision was done in Python_/Django_ in 2020, as I was
looking to change my career from PHP_/Laravel_ to Python, but lacked
experience with large Python projects.  I needed something in my
portfolio and decided to work on the somewhat outdated Mojolicious
project.

Despite having no prior experience with Django, I spent two months
working late nights to create the `Mia! Accounting Django`_
application.  It took me another 1.5 months to make it an independent
module, which I later released as an open source project on PyPI.

The application worked nicely for my household bookkeeping for two
years.  However, new demands arose over time, especially with tracking
payables and receivables.  This was critical `during the pandemic`_ as
more payments were made online with credit cards.

The biggest issue I encountered was with
`Django's MTV architectural pattern`_.  Django takes over the control
flow.  I had to override several parts of the `class-based views`_ for
different but yet simple control flow logic.  In the end, it became
very difficult to track whether things went wrong because I overrode
something or because it just wouldn't work with the basic assumption
of the class-based views.  By the time I realized it, it was too late
for me to drop Django's MTV and rewrite everything from class-based
views to function-based views.

Therefore, I decided to turn to microframeworks_ like Flask_.   After
working with modularized Flask and FastAPI_ applications for two
years, I returned to the project and wrote its third revision using
Flask in 2023.


.. _Perl: https://www.perl.org
.. _mod_perl: https://perl.apache.org
.. _Mojolicious: https://mojolicious.org
.. _Bootstrap: https://getbootstrap.com
.. _jQuery: https://jquery.com
.. _Python: https://www.python.org
.. _Django: https://www.djangoproject.com
.. _PHP: https://www.php.net
.. _Laravel: https://laravel.com
.. _Mia! Accounting Django: https://github.com/imacat/mia-accounting-django
.. _during the pandemic: https://en.wikipedia.org/wiki/COVID-19_pandemic
.. _FastAPI: https://fastapi.tiangolo.com
.. _Django's MTV architectural pattern: https://docs.djangoproject.com/en/dev/faq/general/#django-appears-to-be-a-mvc-framework-but-you-call-the-controller-the-view-and-the-view-the-template-how-come-you-don-t-use-the-standard-names
.. _class-based views: https://docs.djangoproject.com/en/4.2/topics/class-based-views/
.. _microframeworks: https://en.wikipedia.org/wiki/Microframework
.. _Flask: https://flask.palletsprojects.com
