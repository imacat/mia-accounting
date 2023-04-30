Change Log
==========


Version 1.5.3
-------------

Released 2023/4/30

* Fixed the error of the net balance in the unmatched offset list.
* Revised the original line item editor not to override the existing
  amount when the existing amount is less or equal to the net
  balance.


Version 1.5.2
-------------

Released 2023/4/30

* Fixed the error of the net balance in the unmatched offset list.


Version 1.5.1
-------------

Released 2023/4/30

* Fixed the error calling the old ``setEnableDescriptionAccount``
  method in the ``saveOriginalLineItem`` method of the JavaScript
  ``JournalEntryLineItemEditor`` class.


Version 1.5.0
-------------

Released 2023/4/23

* Updated to require ``SQLAlchemy >= 2``.
* Added the change log.
* Added the ``VERSION`` constant to the ``accounting`` module for
  the package version, and revised ``pyproject.toml`` and ``conf.py``
  to read the version from it.


Version 1.4.1
-------------

Released 2023/4/22

* Updated to allow editing the description of the journal entry line
  item with offsets or are offsetting to original line items.
* Updated not to override the existing description of a journal entry
  line item after choosing the original line item to offset to.


Version 1.4.0
-------------

Released 2023/4/18

* Rewrote the unapplied original line items and unmatched offsets.

  * The unapplied original line items and unmatched offsets are both
    in the report submodule.  They can be filtered with currency and
    period now.
  * Show the unapplied original line items and unmatched offsets
    together, and added the accumulated balance in the unmatched
    offset list, for ease of reference.

* Removed the account code from the journal entry detail and journal
  entry form for mobile devices.
* Made the account options in the reports to be scrollable.


Version 1.3.3
-------------

Released 2023/4/13

Changed the sample data generation in the test site live demonstration
from pre-recorded data to real-time generation, to avoid the problem
with the start of months and weeks changed with the date of the
import.


Version 1.3.2
-------------

Released 2023/4/12

Added the sample data generation and database reset on the test site
for live demonstration.


Version 1.3.1
-------------

Released 2023/4/11

* Fixed the permission of the navigation menu of the unmatched offsets.
* Revised the test site to be more accessible as the live demonstration.


Version 1.3.0
-------------

Released 2023/4/11

Added the ``accounting-init-db`` console command to replace all the
other console commands to initialize the accounting database.  The
test site does not work with previous versions (<1.3.0).


Version 1.2.1
-------------

Released 2023/4/9

Fixed the search result to allow full ``year/month/day``
specification.


Version 1.2.0
-------------

Released 2023/4/9

* Simplified the URL of the default reports.
* Fixed the crash with malformed Chinese translation.
* Fixed the crash when downloading CSV data with non-US-ASCII
  filenames.


Version 1.1.0
-------------

Released 2023/4/9

* Added the unapplied original line item list, to track unpaid
  payables, unreceived receivables, assets, prepaids, refundable
  deposits, etc.
* Added the offset matcher to match unapplied original line items
  with unmatched offsets.


Version 1.0.1
-------------

Released 2023/4/6

Documentation fixes.


Version 1.0.0
-------------

Released 2023/4/6

The first formal release in Flask.

Added the documentation.


Version 0.11.1 (Pre-release)
----------------------------

Released 2023/4/5

Removed the zero balances from the trial balance, the income
statement, and the balance sheet.


Version 0.11.0 (Pre-release)
----------------------------

Released 2023/4/5

* Renamed the project from ``mia-accounting-flask`` to
  ``mia-accounting``.
* Updated the URL of the reports, as the default views of the
  accounting application.
* Updated ``README``.
* Various fixes.


Version 0.10.0 (Pre-release)
----------------------------

Released 2023/4/3

* Added the unauthorized method to the ``UserUtilityInterface``
  interface to allow fine control to how to handle the case when the
  user has not logged in.
* Revised the JavaScript description editor to respect the account
  that the user has confirmed or specifically selected.
* Various fixes.


Version 0.9.1 (Pre-release)
---------------------------

Released 2023/3/24

* A distinguishable look in the option detail than the option form.
* A better look in the new journal entry forms when there is no line
  item yet.
* Fixed the search in the original entry selector in the journal
  entry form to always do a partial match, to fix the problem that
  there is no match when typing is not finished yet.
* Fixed the search in the original entry selector to search the net
  balance correctly.
* Replaced the ``editor`` and ``editor2`` accounts with the ``admin``
  and ``editor`` accounts.
* Various fixes.


Version 0.9.0 (Pre-release)
---------------------------

Released 2023/3/23

Moved the settings from the ``.env`` file to the option table in the
database that can be set and updated on the web interface.  Added the
settings page to show and update the settings.


Version 0.8.0 (Pre-release)
---------------------------

Released 2023/3/22

* Added the recurring transactions to the description editor.
* Added prevention to delete database objects that are essential or
  referenced by others with foreign keys.
* Various fixes on the visual layout.


Version 0.7.0 (Pre-release)
---------------------------

Released 2023/3/21

* Renamed "transaction" to "journal entry", and "journal entry" to
  "journal entry line item".
* Renamed ``summary`` to ``description``.
* Updated tempus-dominus from version 6.2.10 to 6.4.3.
* Fixed titles and capitalization.
* Fixed to search case-insensitively.
* Added favicon to the test site.
* Fixed the navigation menu when there is no matching endpoint.
* Various fixes.


Version 0.6.0 (Pre-release)
---------------------------

Released 2023/3/18

* Added offset tracking to the journal entries in the payable and
  receivable accounts.
* Renamed the ``is_offset_needed`` column to ``is_need_offset`` in
  the ``Account`` data model.


Version 0.5.0 (Pre-release)
---------------------------

Released 2023/3/10

Added the accounting reports.


Version 0.4.0 (Pre-release)
---------------------------

Released 2023/3/1

Added the transaction summary helper.


Version 0.3.1 (Pre-release)
---------------------------

Released 2023/2/28

* Fixed the error that cannot select any account when adding new
  transactions.
* Fixed the database error when adding new transactions.
* Added the button to convert a cash income or cash expense
  transaction to a transfer transaction.


Version 0.3.0 (Pre-release)
---------------------------

Released 2023/2/27

Added the transaction management.


Version 0.2.0 (Pre-release)
---------------------------

Released 2023/2/7

* Added the currency management.
* Changed the ``can_edit`` permission to at least require the user to
  log in first.
* Changed the type hint of the ``current_user`` pseudo property of
  the ``AbstractUserUtils`` class to return ``None`` when the user
  has not logged in.


Version 0.1.1 (Pre-release)
---------------------------

Released 2023/2/3

Finalized the account management, with tests and reordering.


Version 0.1.0 (Pre-release)
---------------------------

Released 2023/2/3

Added the account management, and updated the API to initialize the
accounting application.


Version 0.0.0 (Pre-release)
---------------------------

Released 2023/2/3

Initial release with main account list, localization, pagination,
query, permission, Sphinx documentation, and a test case based on a
test demonstration site.
