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
from sqlalchemy.orm import selectinload

from accounting.locale import gettext
from accounting.models import Currency, Account, Transaction, JournalEntry
from accounting.report.period import Period, PeriodChooser
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download, \
    period_spec
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.urls import journal_url
from accounting.utils.pagination import Pagination


class ReportEntry:
    """An entry in the report."""

    def __init__(self, entry: JournalEntry):
        """Constructs the entry in the report.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry = entry
        """The journal entry."""
        self.transaction: Transaction = entry.transaction
        """The transaction."""
        self.currency: Currency = entry.currency
        """The account."""
        self.account: Account = entry.account
        """The account."""
        self.summary: str | None = entry.summary
        """The summary."""
        self.debit: Decimal | None = entry.debit
        """The debit amount."""
        self.credit: Decimal | None = entry.credit
        """The credit amount."""
        self.amount: Decimal = entry.amount
        """The amount."""


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
                 pagination: Pagination[JournalEntry],
                 entries: list[JournalEntry]):
        """Constructs the HTML page parameters.

        :param period: The period.
        :param entries: The journal entries.
        """
        self.period: Period = period
        """The period."""
        self.pagination: Pagination[JournalEntry] = pagination
        """The pagination."""
        self.entries: list[JournalEntry] = entries
        """The entries."""
        self.period_chooser: PeriodChooser = PeriodChooser(
            lambda x: journal_url(x))
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


def get_csv_rows(entries: list[JournalEntry]) -> list[CSVRow]:
    """Composes and returns the CSV rows from the report entries.

    :param entries: The report entries.
    :return: The CSV rows.
    """
    rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Currency"),
                                 gettext("Account"), gettext("Summary"),
                                 gettext("Debit"), gettext("Credit"),
                                 gettext("Note"))]
    rows.extend([CSVRow(x.transaction.date, x.currency.code,
                        str(x.account).title(), x.summary,
                        x.debit, x.credit, x.transaction.note)
                 for x in entries])
    return rows


class Journal(BaseReport):
    """The journal."""

    def __init__(self, period: Period):
        """Constructs a journal.

        :param period: The period.
        """
        self.__period: Period = period
        """The period."""
        self.__entries: list[JournalEntry] = self.__query_entries()
        """The journal entries."""

    def __query_entries(self) -> list[JournalEntry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        conditions: list[sa.BinaryExpression] = []
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        return JournalEntry.query.join(Transaction)\
            .filter(*conditions)\
            .order_by(Transaction.date,
                      Transaction.no,
                      JournalEntry.is_debit.desc(),
                      JournalEntry.no)\
            .options(selectinload(JournalEntry.account),
                     selectinload(JournalEntry.currency),
                     selectinload(JournalEntry.transaction)).all()

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = f"journal-{period_spec(self.__period)}.csv"
        return csv_download(filename, get_csv_rows(self.__entries))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[JournalEntry] \
            = Pagination[JournalEntry](self.__entries)
        params: PageParams = PageParams(period=self.__period,
                                        pagination=pagination,
                                        entries=pagination.list)
        return render_template("accounting/report/journal.html",
                               report=params)
