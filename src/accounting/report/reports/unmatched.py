# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/17

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
"""The unmatched offsets.

"""
import datetime as dt
from decimal import Decimal

from flask import render_template, Response
from flask_babel import LazyString

from accounting.locale import gettext
from accounting.models import Currency, Account, JournalEntryLineItem
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download
from accounting.report.utils.offset_matcher import OffsetMatcher, OffsetPair
from accounting.report.utils.option_link import OptionLink
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.unmatched import get_accounts_with_unmatched
from accounting.report.utils.urls import unmatched_url
from accounting.utils.pagination import Pagination


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, journal_entry_date: str | dt.date, currency: str,
                 description: str | None, debit: str | Decimal,
                 credit: str | Decimal, balance: str | Decimal):
        """Constructs a row in the CSV.

        :param journal_entry_date: The journal entry date.
        :param currency: The currency.
        :param description: The description.
        :param debit: The debit amount.
        :param credit: The credit amount.
        :param balance: The balance.
        """
        self.date: str | dt.date = journal_entry_date
        """The date."""
        self.currency: str = currency
        """The currency."""
        self.description: str | None = description
        """The description."""
        self.debit: str | Decimal | None = debit
        """The debit amount."""
        self.credit: str | Decimal | None = credit
        """The credit amount."""
        self.balance: str | Decimal = balance
        """The balance."""

    @property
    def values(self) -> list[str | dt.date | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.currency, self.description, self.debit,
                self.credit, self.balance]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, currency: Currency,
                 account: Account,
                 match_status: str | LazyString,
                 matched_pairs: list[OffsetPair],
                 pagination: Pagination[JournalEntryLineItem],
                 line_items: list[JournalEntryLineItem]):
        """Constructs the HTML page parameters.

        :param currency: The currency.
        :param account: The account.
        :param match_status: The match status message.
        :param matched_pairs: A list of matched pairs.
        :param pagination: The pagination.
        :param line_items: The line items.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.match_status: str | LazyString = match_status
        """The match status message."""
        self.matched_pairs: list[OffsetPair] = matched_pairs
        """A list of matched pairs."""
        self.pagination: Pagination[JournalEntryLineItem] = pagination
        """The pagination."""
        self.line_items: list[JournalEntryLineItem] = line_items
        """The line items."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.line_items) > 0

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.UNMATCHED, currency=self.currency,
                             account=self.account)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        return self._get_currency_options(
            lambda x: unmatched_url(x, self.account), self.currency)

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        options: list[OptionLink] \
            = [OptionLink(gettext("Accounts"),
                          unmatched_url(self.currency, None),
                          False)]
        options.extend(
            [OptionLink(str(x), unmatched_url(self.currency, x),
                        x.id == self.account.id)
             for x in get_accounts_with_unmatched(self.currency)])
        return options


def get_csv_rows(line_items: list[JournalEntryLineItem]) -> list[CSVRow]:
    """Composes and returns the CSV rows from the line items.

    :param line_items: The line items.
    :return: The CSV rows.
    """
    rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Currency"),
                                 gettext("Description"), gettext("Debit"),
                                 gettext("Credit"), gettext("Balance"))]
    rows.extend([CSVRow(x.journal_entry.date, x.currency.code,
                        x.description, x.debit, x.credit, x.balance)
                 for x in line_items])
    return rows


class UnmatchedOffsets(BaseReport):
    """The unmatched offsets."""

    def __init__(self, currency: Currency, account: Account):
        """Constructs the unmatched offsets.

        :param currency: The currency.
        :param account: The account.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        offset_matcher: OffsetMatcher \
            = OffsetMatcher(self.__currency, self.__account)
        self.__line_items: list[JournalEntryLineItem] \
            = offset_matcher.line_items
        """The line items."""
        self.__match_status: str | LazyString = offset_matcher.status
        """The match status message."""
        self.__matched_pairs: list[OffsetPair] = offset_matcher.matched_pairs
        """A list of matched pairs."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "unmatched-{currency}-{account}.csv"\
            .format(currency=self.__currency.code, account=self.__account.code)
        return csv_download(filename, get_csv_rows(self.__line_items))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[JournalEntryLineItem] \
            = Pagination[JournalEntryLineItem](self.__line_items,
                                               is_reversed=True)
        params: PageParams = PageParams(currency=self.__currency,
                                        account=self.__account,
                                        match_status=self.__match_status,
                                        matched_pairs=self.__matched_pairs,
                                        pagination=pagination,
                                        line_items=pagination.list)
        return render_template("accounting/report/unmatched.html",
                               report=params)
