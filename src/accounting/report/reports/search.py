# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/8

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
"""The search.

"""
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from flask import Response, render_template, request

from accounting.locale import gettext
from accounting.models import Currency, CurrencyL10n, Account, AccountL10n, \
    Transaction, JournalEntry
from accounting.utils.pagination import Pagination
from accounting.utils.query import parse_query_keywords
from .utils.base_report import BaseReport
from .utils.csv_export import BaseCSVRow, csv_download
from .utils.base_page_params import BasePageParams
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class Entry:
    """An entry in the search result."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the entry in the search result.

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

    def __init__(self, pagination: Pagination[Entry],
                 entries: list[Entry]):
        """Constructs the HTML page parameters.

        :param entries: The search result entries.
        """
        self.pagination: Pagination[Entry] = pagination
        """The pagination."""
        self.entries: list[Entry] = entries
        """The entries."""

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
        return ReportChooser(ReportType.SEARCH)


def _populate_entries(entries: list[Entry]) -> None:
    """Populates the search result entries with relative data.

    :param entries: The search result entries.
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


class Search(BaseReport):
    """The search."""

    def __init__(self):
        """Constructs a search."""
        """The account."""
        self.__entries: list[Entry] = self.__query_entries()
        """The journal entries."""

    def __query_entries(self) -> list[Entry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        keywords: list[str] = parse_query_keywords(request.args.get("q"))
        if len(keywords) == 0:
            return []
        conditions: list[sa.BinaryExpression] = []
        for k in keywords:
            sub_conditions: list[sa.BinaryExpression] \
                = [JournalEntry.summary.contains(k),
                   JournalEntry.account_id.in_(
                       self.__get_account_condition(k)),
                   JournalEntry.currency_code.in_(
                       self.__get_currency_condition(k)),
                   JournalEntry.transaction_id.in_(
                       self.__get_transaction_condition(k))]
            try:
                sub_conditions.append(JournalEntry.amount == Decimal(k))
            except ArithmeticError:
                pass
            conditions.append(sa.or_(*sub_conditions))
        return [Entry(x) for x in JournalEntry.query.filter(*conditions)]

    @staticmethod
    def __get_account_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the account.

        :param k: The keyword.
        :return: The condition to filter the account.
        """
        code: sa.BinaryExpression = Account.base_code + "-" \
            + sa.func.substr("000" + sa.cast(Account.no, sa.String),
                             sa.func.char_length(sa.cast(Account.no,
                                                         sa.String)) + 1)
        select_l10n: sa.Select = sa.select(AccountL10n.account_id)\
            .filter(AccountL10n.title.contains(k))
        conditions: list[sa.BinaryExpression] \
            = [Account.base_code.contains(k),
               Account.title_l10n.contains(k),
               code.contains(k),
               Account.id.in_(select_l10n)]
        if k in gettext("Pay-off needed"):
            conditions.append(Account.is_pay_off_needed)
        return sa.select(Account.id).filter(sa.or_(*conditions))

    @staticmethod
    def __get_currency_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the currency.

        :param k: The keyword.
        :return: The condition to filter the currency.
        """
        select_l10n: sa.Select = sa.select(CurrencyL10n.currency_code)\
            .filter(CurrencyL10n.name.contains(k))
        return sa.select(Currency.code).filter(
            sa.or_(Currency.code.contains(k),
                   Currency.name_l10n.contains(k),
                   Currency.code.in_(select_l10n)))

    @staticmethod
    def __get_transaction_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the transaction.

        :param k: The keyword.
        :return: The condition to filter the transaction.
        """
        conditions: list[sa.BinaryExpression] = [Transaction.note.contains(k)]
        txn_date: datetime
        try:
            txn_date = datetime.strptime(k, "%Y")
            conditions.append(
                sa.extract("year", Transaction.date) == txn_date.year)
        except ValueError:
            pass
        try:
            txn_date = datetime.strptime(k, "%Y/%m")
            conditions.append(sa.and_(
                sa.extract("year", Transaction.date) == txn_date.year,
                sa.extract("month", Transaction.date) == txn_date.month))
        except ValueError:
            pass
        try:
            txn_date = datetime.strptime(f"2000/{k}", "%Y/%m/%d")
            conditions.append(sa.and_(
                sa.extract("month", Transaction.date) == txn_date.month,
                sa.extract("day", Transaction.date) == txn_date.day))
        except ValueError:
            pass
        return sa.select(Transaction.id).filter(sa.or_(*conditions))

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "search-{q}.csv".format(q=request.args["q"])
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        _populate_entries(self.__entries)
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
        pagination: Pagination[Entry] = Pagination[Entry](self.__entries)
        page_entries: list[Entry] = pagination.list
        _populate_entries(page_entries)
        params: PageParams = PageParams(pagination=pagination,
                                        entries=page_entries)
        return render_template("accounting/report/search.html",
                               report=params)
