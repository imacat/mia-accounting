# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/7

#  Copyright (c) 2023 imacat.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""The accounts with unapplied original line items.

"""
import datetime as dt
from decimal import Decimal

from flask import render_template, Response

from accounting.locale import gettext
from accounting.models import Currency, Account
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download
from accounting.report.utils.option_link import OptionLink
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.unapplied import get_accounts_with_unapplied
from accounting.report.utils.urls import unapplied_url


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, account: str, count: int | str):
        """Constructs a row in the CSV.

        :param account: The account.
        :param count: The number of unapplied original line items.
        """
        self.account: str = account
        """The currency."""
        self.count: int | str = count
        """The number of unapplied original line items."""

    @property
    def values(self) -> list[str | dt.date | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.account, self.count]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, currency: Currency, accounts: list[Account]):
        """Constructs the HTML page parameters.

        :param currency: The currency.
        :param accounts: The accounts.
        """
        self.currency: Currency = currency
        """The currency."""
        self.accounts: list[Account] = accounts
        """The accounts."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.accounts) > 0

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.UNAPPLIED, currency=self.currency,
                             account=None)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        return self._get_currency_options(lambda x: unapplied_url(x, None),
                                          self.currency)

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        options: list[OptionLink] \
            = [OptionLink(gettext("Accounts"),
                          unapplied_url(self.currency, None),
                          True)]
        options.extend(
            [OptionLink(str(x), unapplied_url(self.currency, x), False)
             for x in self.accounts])
        return options


def get_csv_rows(accounts: list[Account]) -> list[CSVRow]:
    """Composes and returns the CSV rows from the line items.

    :param accounts: The accounts.
    :return: The CSV rows.
    """
    rows: list[CSVRow] = [CSVRow(gettext("Account"), gettext("Count"))]
    rows.extend([CSVRow(str(x).title(), x.count)
                 for x in accounts])
    return rows


class AccountsWithUnappliedOriginalLineItems(BaseReport):
    """The accounts with unapplied original line items."""

    def __init__(self, currency: Currency):
        """Constructs the outstanding balances.

        :param currency: The currency.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__accounts: list[Account] = get_accounts_with_unapplied(currency)
        """The accounts."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "unapplied-accounts.csv"
        return csv_download(filename, get_csv_rows(self.__accounts))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        return render_template("accounting/report/unapplied-accounts.html",
                               report=PageParams(currency=self.__currency,
                                                 accounts=self.__accounts))
