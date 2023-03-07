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
"""The income and expenses log.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import url_for, render_template, Response

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account, Transaction, JournalEntry
from accounting.report.period import Period
from accounting.utils.pagination import Pagination
from .utils.csv_export import BaseCSVRow, csv_download
from .utils.option_link import OptionLink
from .utils.page_params import PageParams
from .utils.period_choosers import IncomeExpensesPeriodChooser
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class Entry:
    """An entry in the income and expenses log."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the entry in the income and expenses log.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry | None = None
        """The journal entry."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.is_brought_forward: bool = False
        """Whether this is the brought-forward entry."""
        self.is_total: bool = False
        """Whether this is the total entry."""
        self.date: date | None = None
        """The date."""
        self.account: Account | None = None
        """The account."""
        self.summary: str | None = None
        """The summary."""
        self.income: Decimal | None = None
        """The income amount."""
        self.expense: Decimal | None = None
        """The expense amount."""
        self.balance: Decimal | None = None
        """The balance."""
        self.note: str | None = None
        """The note."""
        if entry is not None:
            self.entry = entry
            self.summary = entry.summary
            self.income = None if entry.is_debit else entry.amount
            self.expense = entry.amount if entry.is_debit else None


class EntryCollector:
    """The income and expenses log entry collector."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs the income and expenses log entry collector.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        self.__period: Period = period
        """The period"""
        self.brought_forward: Entry | None
        """The brought-forward entry."""
        self.entries: list[Entry]
        """The log entries."""
        self.total: Entry
        """The total entry."""
        self.brought_forward = self.__get_brought_forward_entry()
        self.entries = self.__query_entries()
        self.total = self.__get_total_entry()
        self.__populate_balance()

    def __get_brought_forward_entry(self) -> Entry | None:
        """Queries, composes and returns the brought-forward entry.

        :return: The brought-forward entry, or None if the period starts from
            the beginning.
        """
        if self.__period.start is None:
            return None
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount))
        select: sa.Select = sa.Select(balance_func).join(Transaction)\
            .filter(JournalEntry.currency_code == self.__currency.code,
                    JournalEntry.account_id == self.__account.id,
                    Transaction.date < self.__period.start)
        balance: int | None = db.session.scalar(select)
        if balance is None:
            return None
        entry: Entry = Entry()
        entry.is_brought_forward = True
        entry.date = self.__period.start
        entry.account = Account.find_by_code("3351-001")
        entry.summary = gettext("Brought forward")
        if balance > 0:
            entry.income = balance
        elif balance < 0:
            entry.expense = -balance
        entry.balance = balance
        return entry

    def __query_entries(self) -> list[Entry]:
        """Queries and returns the log entries.

        :return: The log entries.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code,
               JournalEntry.account_id == self.__account.id]
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        txn_with_account: sa.Select = sa.Select(Transaction.id).\
            join(JournalEntry).filter(*conditions)

        return [Entry(x)
                for x in JournalEntry.query.join(Transaction)
                .filter(JournalEntry.transaction_id.in_(txn_with_account),
                        JournalEntry.currency_code == self.__currency.code,
                        JournalEntry.account_id != self.__account.id)
                .order_by(Transaction.date,
                          JournalEntry.is_debit,
                          JournalEntry.no)]

    def __get_total_entry(self) -> Entry:
        """Composes the total entry.

        :return: None.
        """
        entry: Entry = Entry()
        entry.is_total = True
        entry.summary = gettext("Total")
        entry.income = sum([x.income for x in self.entries
                            if x.income is not None])
        entry.expense = sum([x.expense for x in self.entries
                             if x.expense is not None])
        entry.balance = entry.income - entry.expense
        if self.brought_forward is not None:
            entry.balance = self.brought_forward.balance + entry.balance
        return entry

    def __populate_balance(self) -> None:
        """Populates the balance of the entries.

        :return: None.
        """
        balance: Decimal = 0 if self.brought_forward is None \
            else self.brought_forward.balance
        for entry in self.entries:
            if entry.income is not None:
                balance = balance + entry.income
            if entry.expense is not None:
                balance = balance - entry.expense
            entry.balance = balance


class CSVRow(BaseCSVRow):
    """A row in the CSV income and expenses log."""

    def __init__(self, txn_date: date | str | None,
                 account: str | None,
                 summary: str | None,
                 income: str | Decimal | None,
                 expense: str | Decimal | None,
                 balance: str | Decimal | None,
                 note: str | None):
        """Constructs a row in the CSV income and expenses log.

        :param txn_date: The transaction date.
        :param account: The account.
        :param summary: The summary.
        :param income: The income.
        :param expense: The expense.
        :param balance: The balance.
        :param note: The note.
        """
        self.date: date | str | None = txn_date
        """The date."""
        self.account: str | None = account
        """The account."""
        self.summary: str | None = summary
        """The summary."""
        self.income: str | Decimal | None = income
        """The income."""
        self.expense: str | Decimal | None = expense
        """The expense."""
        self.balance: str | Decimal | None = balance
        """The balance."""
        self.note: str | None = note
        """The note."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.account, self.summary,
                self.income, self.expense, self.balance, self.note]


class IncomeExpensesPageParams(PageParams):
    """The HTML parameters of the income and expenses log."""

    def __init__(self, currency: Currency,
                 account: Account,
                 period: Period,
                 has_data: bool,
                 pagination: Pagination[Entry],
                 brought_forward: Entry | None,
                 entries: list[Entry],
                 total: Entry | None):
        """Constructs the HTML parameters of the income and expenses log.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        :param has_data: True if there is any data, or False otherwise.
        :param brought_forward: The brought-forward entry.
        :param entries: The log entries.
        :param total: The total entry.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""
        self.__has_data: bool = has_data
        """True if there is any data, or False otherwise."""
        self.pagination: Pagination[Entry] = pagination
        """The pagination."""
        self.brought_forward: Entry | None = brought_forward
        """The brought-forward entry."""
        self.entries: list[Entry] = entries
        """The entries."""
        self.total: Entry | None = total
        """The total entry."""
        self.period_chooser: IncomeExpensesPeriodChooser \
            = IncomeExpensesPeriodChooser(currency, account)
        """The period chooser."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return self.__has_data

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.INCOME_EXPENSES,
                             currency=self.currency,
                             account=self.account,
                             period=self.period)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.income-expenses-default",
                               currency=currency, account=self.account)
            return url_for("accounting.report.income-expenses",
                           currency=currency, account=self.account,
                           period=self.period)

        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .group_by(JournalEntry.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        def get_url(account: Account):
            if self.period.is_default:
                return url_for("accounting.report.income-expenses-default",
                               currency=self.currency, account=account)
            return url_for("accounting.report.income-expenses",
                           currency=self.currency, account=account,
                           period=self.period)

        in_use: sa.Select = sa.Select(JournalEntry.account_id)\
            .join(Account)\
            .filter(JournalEntry.currency_code == self.currency.code,
                    sa.or_(Account.base_code.startswith("11"),
                           Account.base_code.startswith("12"),
                           Account.base_code.startswith("21"),
                           Account.base_code.startswith("22")))\
            .group_by(JournalEntry.account_id)
        return [OptionLink(str(x), get_url(x), x.id == self.account.id)
                for x in Account.query.filter(Account.id.in_(in_use))
                .order_by(Account.base_code, Account.no).all()]


def _populate_entries(entries: list[Entry]) -> None:
    """Populates the income and expenses entries with relative data.

    :param entries: The income and expenses entries.
    :return: None.
    """
    transactions: dict[int, Transaction] \
        = {x.id: x for x in Transaction.query.filter(
           Transaction.id.in_({x.entry.transaction_id for x in entries
                               if x.entry is not None}))}
    accounts: dict[int, Account] \
        = {x.id: x for x in Account.query.filter(
           Account.id.in_({x.entry.account_id for x in entries
                           if x.entry is not None}))}
    for entry in entries:
        if entry.entry is not None:
            entry.transaction = transactions[entry.entry.transaction_id]
            entry.date = entry.transaction.date
            entry.note = entry.transaction.note
            entry.account = accounts[entry.entry.account_id]


class IncomeExpenses:
    """The income and expenses log."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs an income and expenses log.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        self.__period: Period = period
        """The period."""
        collector: EntryCollector = EntryCollector(
            self.__currency, self.__account, self.__period)
        self.__brought_forward: Entry | None = collector.brought_forward
        """The brought-forward entry."""
        self.__entries: list[Entry] = collector.entries
        """The log entries."""
        self.__total: Entry = collector.total
        """The total entry."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "income-expenses-{currency}-{account}-{period}.csv"\
            .format(currency=self.__currency.code, account=self.__account.code,
                    period=self.__period.spec)
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        _populate_entries(self.__entries)
        rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Account"),
                                     gettext("Summary"), gettext("Income"),
                                     gettext("Expense"), gettext("Balance"),
                                     gettext("Note"))]
        if self.__brought_forward is not None:
            rows.append(CSVRow(self.__brought_forward.date,
                               str(self.__brought_forward.account).title(),
                               self.__brought_forward.summary,
                               self.__brought_forward.income,
                               self.__brought_forward.expense,
                               self.__brought_forward.balance,
                               None))
        rows.extend([CSVRow(x.date, str(x.account).title(), x.summary,
                            x.income, x.expense, x.balance, x.note)
                     for x in self.__entries])
        rows.append(CSVRow(gettext("Total"), None, None,
                           self.__total.income, self.__total.expense,
                           self.__total.balance, None))
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        all_entries: list[Entry] = []
        if self.__brought_forward is not None:
            all_entries.append(self.__brought_forward)
        all_entries.extend(self.__entries)
        all_entries.append(self.__total)
        pagination: Pagination[Entry] = Pagination[Entry](all_entries)
        page_entries: list[Entry] = pagination.list
        has_data: bool = len(page_entries) > 0
        _populate_entries(page_entries)
        brought_forward: Entry | None = None
        if page_entries[0].is_brought_forward:
            brought_forward = page_entries[0]
            page_entries = page_entries[1:]
        total: Entry | None = None
        if page_entries[-1].is_total:
            total = page_entries[-1]
            page_entries = page_entries[:-1]
        params: IncomeExpensesPageParams = IncomeExpensesPageParams(
            currency=self.__currency,
            account=self.__account,
            period=self.__period,
            has_data=has_data,
            pagination=pagination,
            brought_forward=brought_forward,
            entries=page_entries,
            total=total)
        return render_template("accounting/report/income-expenses.html",
                               report=params)
