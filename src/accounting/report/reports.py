# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/4

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
"""The reports.

"""
import csv
from abc import ABC, abstractmethod
from io import StringIO

import sqlalchemy as sa
from flask import Response, render_template
from flask_sqlalchemy.query import Query

from accounting import db
from accounting.models import JournalEntry, Transaction, Account, Currency
from accounting.transaction.dispatcher import TXN_TYPE_OBJ, TransactionTypes
from accounting.utils.pagination import Pagination
from .period import Period
from .period_choosers import PeriodChooser, \
    JournalPeriodChooser
from .report_chooser import ReportChooser, ReportType
from .report_rows import ReportRow, JournalRow


class JournalEntryReport(ABC):
    """A report based on a journal entry."""

    def __init__(self, period: Period):
        """Constructs a journal.

        :param period: The period.
        """
        self.period: Period = period
        """The period."""
        self._entries: list[JournalEntry] = self.get_entries()
        """The journal entries."""

    @abstractmethod
    def get_entries(self) -> list[JournalEntry]:
        """Returns the journal entries.

        :return: The journal entries.
        """

    @abstractmethod
    def entries_to_rows(self, entries: list[JournalEntry]) -> list[ReportRow]:
        """Converts the journal entries into report rows.

        :param entries: The journal entries.
        :return: The report rows.
        """

    @property
    @abstractmethod
    def csv_field_names(self) -> list[str]:
        """Returns the CSV field names.

        :return: The CSV field names.
        """

    @property
    @abstractmethod
    def csv_filename(self) -> str:
        """Returns the CSV file name.

        :return: The CSV file name.
        """

    @property
    @abstractmethod
    def period_chooser(self) -> PeriodChooser:
        """Returns the period chooser.

        :return: The period chooser.
        """

    @property
    @abstractmethod
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """

    @abstractmethod
    def as_html_page(self) -> str:
        """Returns the report as an HTML page.

        :return: The report as an HTML page.
        """

    @property
    def txn_types(self) -> TransactionTypes:
        """Returns the transaction types.

        :return: The transaction types.
        """
        return TXN_TYPE_OBJ

    def as_csv_download(self) -> Response:
        """Returns the journal entries as CSV download.

        :return: The CSV download response.
        """
        with StringIO() as fp:
            writer: csv.DictWriter = csv.DictWriter(
                fp, fieldnames=self.csv_field_names)
            writer.writeheader()
            writer.writerows([x.as_dict()
                              for x in self.entries_to_rows(self._entries)])
            fp.seek(0)
            response: Response = Response(fp.read(), mimetype="text/csv")
            response.headers["Content-Disposition"] \
                = f"attachment; filename={self.csv_filename}"
            return response


class Journal(JournalEntryReport):
    """A journal."""

    def get_entries(self) -> list[JournalEntry]:
        conditions: list[sa.BinaryExpression] = []
        if self.period.start is not None:
            conditions.append(Transaction.date >= self.period.start)
        if self.period.end is not None:
            conditions.append(Transaction.date <= self.period.end)
        query: Query = db.session.query(JournalEntry).join(Transaction)
        if len(conditions) > 0:
            query = query.filter(*conditions)
        return query.order_by(Transaction.date,
                              JournalEntry.is_debit.desc(),
                              JournalEntry.no).all()

    def entries_to_rows(self, entries: list[JournalEntry]) -> list[ReportRow]:
        transactions: dict[int, Transaction] \
            = {x.id: x for x in Transaction.query.filter(
               Transaction.id.in_({x.transaction_id for x in entries}))}
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query.filter(
               Account.id.in_({x.account_id for x in entries}))}
        currencies: dict[int, Currency] \
            = {x.code: x for x in Currency.query.filter(
               Currency.code.in_({x.currency_code for x in entries}))}
        return [JournalRow(x, transactions[x.transaction_id],
                           accounts[x.account_id], currencies[x.currency_code])
                for x in entries]

    @property
    def csv_field_names(self) -> list[str]:
        return ["date", "currency", "account", "summary", "debit", "credit",
                "note"]

    @property
    def csv_filename(self) -> str:
        return f"journal-{self.period.spec}.csv"

    @property
    def period_chooser(self) -> PeriodChooser:
        return JournalPeriodChooser()

    @property
    def report_chooser(self) -> ReportChooser:
        return ReportChooser(ReportType.JOURNAL, self.period)

    def as_html_page(self) -> str:
        pagination: Pagination = Pagination[JournalEntry](self._entries)
        return render_template("accounting/report/journal.html",
                               list=self.entries_to_rows(pagination.list),
                               pagination=pagination, report=self)
