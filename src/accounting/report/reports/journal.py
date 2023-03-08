# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/7

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
"""The journal.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import render_template, Response

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account, Transaction, JournalEntry
from accounting.report.period import Period
from accounting.utils.pagination import Pagination
from .utils.base_report import BaseReport
from .utils.csv_export import BaseCSVRow, csv_download, period_spec
from .utils.base_page_params import BasePageParams
from .utils.period_choosers import JournalPeriodChooser
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class ReportEntry:
    """An entry in the report."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the entry in the report.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry | None = None
        """The journal entry."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.is_total: bool = False
        """Whether this is the total entry."""
        self.currency: Currency | None = None
        """The account."""
        self.account: Account | None = None
        """The account."""
        self.summary: str | None = None
        """The summary."""
        self.debit: Decimal | None = None
        """The debit amount."""
        self.credit: Decimal | None = None
        """The credit amount."""
        self.amount: Decimal | None = None
        """The amount."""
        if entry is not None:
            self.entry = entry
            self.summary = entry.summary
            self.debit = entry.amount if entry.is_debit else None
            self.credit = None if entry.is_debit else entry.amount
            self.amount = entry.amount


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, txn_date: str | date,
                 currency: str,
                 account: str,
                 summary: str | None,
                 debit: str | Decimal | None,
                 credit: str | Decimal | None,
                 note: str | None):
        """Constructs a row in the CSV.

        :param txn_date: The transaction date.
        :param summary: The summary.
        :param debit: The debit amount.
        :param credit: The credit amount.
        :param note: The note.
        """
        self.date: str | date = txn_date
        """The date."""
        self.currency: str = currency
        """The currency."""
        self.account: str = account
        """The account."""
        self.summary: str | None = summary
        """The summary."""
        self.debit: str | Decimal | None = debit
        """The debit amount."""
        self.credit: str | Decimal | None = credit
        """The credit amount."""
        self.note: str | None = note
        """The note."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.currency, self.account, self.summary,
                self.debit, self.credit, self.note]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, period: Period,
                 pagination: Pagination[ReportEntry],
                 entries: list[ReportEntry]):
        """Constructs the HTML page parameters.

        :param period: The period.
        :param entries: The journal entries.
        """
        self.period: Period = period
        """The period."""
        self.pagination: Pagination[ReportEntry] = pagination
        """The pagination."""
        self.entries: list[ReportEntry] = entries
        """The entries."""
        self.period_chooser: JournalPeriodChooser \
            = JournalPeriodChooser()
        """The period chooser."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.entries) > 0

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.JOURNAL,
                             period=self.period)


def populate_entries(entries: list[ReportEntry]) -> None:
    """Populates the report entries with relative data.

    :param entries: The report entries.
    :return: None.
    """
    transactions: dict[int, Transaction] \
        = {x.id: x for x in Transaction.query.filter(
           Transaction.id.in_({x.entry.transaction_id for x in entries}))}
    accounts: dict[int, Account] \
        = {x.id: x for x in Account.query.filter(
           Account.id.in_({x.entry.account_id for x in entries}))}
    currencies: dict[int, Currency] \
        = {x.code: x for x in Currency.query.filter(
           Currency.code.in_({x.entry.currency_code for x in entries}))}
    for entry in entries:
        entry.transaction = transactions[entry.entry.transaction_id]
        entry.account = accounts[entry.entry.account_id]
        entry.currency = currencies[entry.entry.currency_code]


class Journal(BaseReport):
    """The journal."""

    def __init__(self, period: Period):
        """Constructs a journal.

        :param period: The period.
        """
        self.__period: Period = period
        """The period."""
        self.__entries: list[ReportEntry] = self.__query_entries()
        """The journal entries."""

    def __query_entries(self) -> list[ReportEntry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        conditions: list[sa.BinaryExpression] = []
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        return [ReportEntry(x) for x in db.session
                .query(JournalEntry).join(Transaction).filter(*conditions)
                .order_by(Transaction.date,
                          JournalEntry.is_debit.desc(),
                          JournalEntry.no).all()]

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = f"journal-{period_spec(self.__period)}.csv"
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        populate_entries(self.__entries)
        rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Currency"),
                                     gettext("Account"), gettext("Summary"),
                                     gettext("Debit"), gettext("Credit"),
                                     gettext("Note"))]
        rows.extend([CSVRow(x.transaction.date, x.currency.code,
                            str(x.account).title(), x.summary,
                            x.debit, x.credit, x.transaction.note)
                     for x in self.__entries])
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[ReportEntry] \
            = Pagination[ReportEntry](self.__entries)
        page_entries: list[ReportEntry] = pagination.list
        populate_entries(page_entries)
        params: PageParams = PageParams(period=self.__period,
                                        pagination=pagination,
                                        entries=page_entries)
        return render_template("accounting/report/journal.html",
                               report=params)
