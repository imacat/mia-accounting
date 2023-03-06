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
import typing as t
from abc import ABC, abstractmethod
from decimal import Decimal
from io import StringIO

import sqlalchemy as sa
from flask import Response, render_template, url_for

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account, Transaction, JournalEntry
from accounting.report.period import Period
from accounting.report.report_params import JournalParams, LedgerParams, \
    IncomeExpensesParams, TrialBalanceParams
from accounting.report.report_rows import JournalRow, LedgerRow, \
    IncomeExpensesRow, TrialBalanceRow

T = t.TypeVar("T")


class Report(t.Generic[T], ABC):
    """A report."""

    def __init__(self):
        """Constructs a report."""
        self.data_rows: list[T]
        """The data rows."""
        self.brought_forward: T | None
        """The brought-forward row."""
        self.total: T | None
        """The total row."""
        self.data_rows, self.brought_forward, self.total = self.get_rows()

    @abstractmethod
    def get_rows(self) -> tuple[list[T], T | None, T | None]:
        """Returns the data rows, the brought-forward row, and the total row.

        :return: The data rows, the brought-forward row, and the total row.
        """

    @staticmethod
    @abstractmethod
    def populate_rows(rows: list[JournalRow]) -> None:
        """Fills in the related data to the data rows.

        :param rows: The data rows.
        :return: None.
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
        """Returns the CSV download file name.

        :return: The CSV download file name.
        """

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        rows: list[T] = []
        if self.brought_forward is not None:
            rows.append(self.brought_forward)
        rows.extend(self.data_rows)
        if self.total is not None:
            rows.append(self.total)
        self.populate_rows(rows)
        with StringIO() as fp:
            writer: csv.DictWriter = csv.DictWriter(
                fp, fieldnames=self.csv_field_names)
            writer.writeheader()
            writer.writerows([x.as_dict() for x in rows])
            fp.seek(0)
            response: Response = Response(fp.read(), mimetype="text/csv")
            response.headers["Content-Disposition"] \
                = f"attachment; filename={self.csv_filename}"
            return response

    @abstractmethod
    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """


class Journal(Report[JournalRow]):
    """The journal."""

    def __init__(self, period: Period):
        """Constructs a journal.

        :param period: The period.
        """
        self.period: Period = period
        """The period."""
        super().__init__()

    def get_rows(self) -> tuple[list[T], T | None, T | None]:
        conditions: list[sa.BinaryExpression] = []
        if self.period.start is not None:
            conditions.append(Transaction.date >= self.period.start)
        if self.period.end is not None:
            conditions.append(Transaction.date <= self.period.end)
        rows: list[JournalRow] = [JournalRow(x) for x in db.session
                                  .query(JournalEntry)
                                  .join(Transaction)
                                  .filter(*conditions)
                                  .order_by(Transaction.date,
                                            JournalEntry.is_debit.desc(),
                                            JournalEntry.no).all()]
        return rows, None, None

    @staticmethod
    def populate_rows(rows: list[JournalRow]) -> None:
        transactions: dict[int, Transaction] \
            = {x.id: x for x in Transaction.query.filter(
               Transaction.id.in_({x.entry.transaction_id for x in rows}))}
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query.filter(
               Account.id.in_({x.entry.account_id for x in rows}))}
        currencies: dict[int, Currency] \
            = {x.code: x for x in Currency.query.filter(
               Currency.code.in_({x.entry.currency_code for x in rows}))}
        for row in rows:
            row.transaction = transactions[row.entry.transaction_id]
            row.account = accounts[row.entry.account_id]
            row.currency = currencies[row.entry.currency_code]

    @property
    def csv_field_names(self) -> list[str]:
        return ["Date", "Currency", "Account", "Summary", "Debit", "Credit",
                "Note"]

    @property
    def csv_filename(self) -> str:
        return f"journal-{self.period.spec}.csv"

    def html(self) -> str:
        params: JournalParams = JournalParams(
            period=self.period,
            data_rows=self.data_rows,
            filler=self.populate_rows)
        return render_template("accounting/report/journal.html",
                               report=params)


class Ledger(Report[LedgerRow]):
    """The ledger."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs a ledger.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""
        super().__init__()

    def get_rows(self) -> tuple[list[T], T | None, T | None]:
        brought_forward: LedgerRow | None = self.__get_brought_forward_row()
        rows: list[LedgerRow] = [LedgerRow(x) for x in self.__query_entries()]
        total: LedgerRow = self.__get_total_row(brought_forward, rows)
        self.__populate_balance(brought_forward, rows)
        return rows, brought_forward, total

    def __get_brought_forward_row(self) -> LedgerRow | None:
        """Queries, composes and returns the brought-forward row.

        :return: The brought-forward row, or None if the ledger starts from the
            beginning.
        """
        if self.period.start is None:
            return None
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount))
        select: sa.Select = sa.Select(balance_func).join(Transaction)\
            .filter(JournalEntry.currency_code == self.currency.code,
                    JournalEntry.account_id == self.account.id,
                    Transaction.date < self.period.start)
        balance: int | None = db.session.scalar(select)
        if balance is None:
            return None
        row: LedgerRow = LedgerRow()
        row.date = self.period.start
        row.summary = gettext("Brought forward")
        if balance > 0:
            row.debit = balance
        elif balance < 0:
            row.credit = -balance
        row.balance = balance
        return row

    def __query_entries(self) -> list[JournalEntry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.currency.code,
               JournalEntry.account_id == self.account.id]
        if self.period.start is not None:
            conditions.append(Transaction.date >= self.period.start)
        if self.period.end is not None:
            conditions.append(Transaction.date <= self.period.end)
        return db.session.query(JournalEntry).join(Transaction)\
            .filter(*conditions)\
            .order_by(Transaction.date,
                      JournalEntry.is_debit.desc(),
                      JournalEntry.no).all()

    @staticmethod
    def __get_total_row(brought_forward: LedgerRow | None,
                        rows: list[LedgerRow]) -> LedgerRow:
        """Composes the total row.

        :param brought_forward: The brought-forward row.
        :param rows: The rows.
        :return: None.
        """
        row: LedgerRow = LedgerRow()
        row.is_total = True
        row.summary = gettext("Total")
        row.debit = sum([x.debit for x in rows if x.debit is not None])
        row.credit = sum([x.credit for x in rows if x.credit is not None])
        row.balance = row.debit - row.credit
        if brought_forward is not None:
            row.balance = brought_forward.balance + row.balance
        return row

    @staticmethod
    def __populate_balance(brought_forward: LedgerRow | None,
                           rows: list[LedgerRow]) -> None:
        """Populates the balance of the rows.

        :param brought_forward: The brought-forward row.
        :param rows: The rows.
        :return: None.
        """
        balance: Decimal = 0 if brought_forward is None \
            else brought_forward.balance
        for row in rows:
            if row.debit is not None:
                balance = balance + row.debit
            if row.credit is not None:
                balance = balance - row.credit
            row.balance = balance

    @staticmethod
    def populate_rows(rows: list[LedgerRow]) -> None:
        transactions: dict[int, Transaction] \
            = {x.id: x for x in Transaction.query.filter(
               Transaction.id.in_({x.entry.transaction_id for x in rows
                                   if x.entry is not None}))}
        for row in rows:
            if row.entry is not None:
                row.transaction = transactions[row.entry.transaction_id]
                row.date = row.transaction.date
                row.note = row.transaction.note

    @property
    def csv_field_names(self) -> list[str]:
        return ["Date", "Summary", "Debit", "Credit", "Balance", "Note"]

    @property
    def csv_filename(self) -> str:
        return "ledger-{currency}-{account}-{period}.csv".format(
            currency=self.currency.code, account=self.account.code,
            period=self.period.spec)

    def html(self) -> str:
        params: LedgerParams = LedgerParams(
            currency=self.currency,
            account=self.account,
            period=self.period,
            data_rows=self.data_rows,
            filler=self.populate_rows,
            brought_forward=self.brought_forward,
            total=self.total)
        return render_template("accounting/report/ledger.html",
                               report=params)


class IncomeExpenses(Report[IncomeExpensesRow]):
    """The income and expenses."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs an income and expenses.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""
        super().__init__()

    def get_rows(self) -> tuple[list[T], T | None, T | None]:
        brought_forward: IncomeExpensesRow | None \
            = self.__get_brought_forward_row()
        rows: list[IncomeExpensesRow] \
            = [IncomeExpensesRow(x) for x in self.__query_entries()]
        total: IncomeExpensesRow = self.__get_total_row(brought_forward, rows)
        self.__populate_balance(brought_forward, rows)
        return rows, brought_forward, total

    def __get_brought_forward_row(self) -> IncomeExpensesRow | None:
        """Queries, composes and returns the brought-forward row.

        :return: The brought-forward row, or None if the income-expenses starts
            from the beginning.
        """
        if self.period.start is None:
            return None
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount))
        select: sa.Select = sa.Select(balance_func).join(Transaction)\
            .filter(JournalEntry.currency_code == self.currency.code,
                    JournalEntry.account_id == self.account.id,
                    Transaction.date < self.period.start)
        balance: int | None = db.session.scalar(select)
        if balance is None:
            return None
        row: IncomeExpensesRow = IncomeExpensesRow()
        row.date = self.period.start
        row.account = Account.find_by_code("3351-001")
        row.summary = gettext("Brought forward")
        if balance > 0:
            row.income = balance
        elif balance < 0:
            row.expense = -balance
        row.balance = balance
        return row

    def __query_entries(self) -> list[JournalEntry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.currency.code,
               JournalEntry.account_id == self.account.id]
        if self.period.start is not None:
            conditions.append(Transaction.date >= self.period.start)
        if self.period.end is not None:
            conditions.append(Transaction.date <= self.period.end)
        txn_with_account: sa.Select = sa.Select(Transaction.id).\
            join(JournalEntry).filter(*conditions)

        return JournalEntry.query.join(Transaction)\
            .filter(JournalEntry.transaction_id.in_(txn_with_account),
                    JournalEntry.currency_code == self.currency.code,
                    JournalEntry.account_id != self.account.id)\
            .order_by(Transaction.date,
                      sa.desc(JournalEntry.is_debit),
                      JournalEntry.no)

    @staticmethod
    def __get_total_row(brought_forward: IncomeExpensesRow | None,
                        rows: list[IncomeExpensesRow]) -> IncomeExpensesRow:
        """Composes the total row.

        :param brought_forward: The brought-forward row.
        :param rows: The rows.
        :return: None.
        """
        row: IncomeExpensesRow = IncomeExpensesRow()
        row.is_total = True
        row.summary = gettext("Total")
        row.income = sum([x.income for x in rows if x.income is not None])
        row.expense = sum([x.expense for x in rows if x.expense is not None])
        row.balance = row.income - row.expense
        if brought_forward is not None:
            row.balance = brought_forward.balance + row.balance
        return row

    @staticmethod
    def __populate_balance(brought_forward: IncomeExpensesRow | None,
                           rows: list[IncomeExpensesRow]) -> None:
        """Populates the balance of the rows.

        :param brought_forward: The brought-forward row.
        :param rows: The rows.
        :return: None.
        """
        balance: Decimal = 0 if brought_forward is None \
            else brought_forward.balance
        for row in rows:
            if row.income is not None:
                balance = balance + row.income
            if row.expense is not None:
                balance = balance - row.expense
            row.balance = balance

    @staticmethod
    def populate_rows(rows: list[IncomeExpensesRow]) -> None:
        transactions: dict[int, Transaction] \
            = {x.id: x for x in Transaction.query.filter(
               Transaction.id.in_({x.entry.transaction_id for x in rows
                                   if x.entry is not None}))}
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query.filter(
               Account.id.in_({x.entry.account_id for x in rows
                               if x.entry is not None}))}
        for row in rows:
            if row.entry is not None:
                row.transaction = transactions[row.entry.transaction_id]
                row.date = row.transaction.date
                row.note = row.transaction.note
                row.account = accounts[row.entry.account_id]

    @property
    def csv_field_names(self) -> list[str]:
        return ["Date", "Account", "Summary", "Income", "Expense", "Balance",
                "Note"]

    @property
    def csv_filename(self) -> str:
        return "income-expenses-{currency}-{account}-{period}.csv".format(
            currency=self.currency.code, account=self.account.code,
            period=self.period.spec)

    def html(self) -> str:
        params: IncomeExpensesParams = IncomeExpensesParams(
            currency=self.currency,
            account=self.account,
            period=self.period,
            data_rows=self.data_rows,
            filler=self.populate_rows,
            brought_forward=self.brought_forward,
            total=self.total)
        return render_template("accounting/report/income-expenses.html",
                               report=params)


class TrialBalance(Report[TrialBalanceRow]):
    """The trial balance."""

    def __init__(self, currency: Currency, period: Period):
        """Constructs a trial balance.

        :param currency: The currency.
        :param period: The period.
        """
        self.currency: Currency = currency
        """The currency."""
        self.period: Period = period
        """The period."""
        super().__init__()

    def get_rows(self) -> tuple[list[T], T | None, T | None]:
        rows: list[TrialBalanceRow] = self.__query_balances()
        self.__populate_url(rows)
        total_row: TrialBalanceRow = self.__get_total_row(rows)
        return rows, None, total_row

    def __query_balances(self) -> list[TrialBalanceRow]:
        """Queries and returns the balances.

        :return: The balances.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.currency.code]
        if self.period.start is not None:
            conditions.append(Transaction.date >= self.period.start)
        if self.period.end is not None:
            conditions.append(Transaction.date <= self.period.end)
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)).label("balance")
        select_trial_balance: sa.Select \
            = sa.select(JournalEntry.account_id, balance_func)\
            .join(Transaction).join(Account)\
            .filter(*conditions)\
            .group_by(JournalEntry.account_id)\
            .order_by(Account.base_code, Account.no)
        balances: list[sa.Row] = db.session.execute(select_trial_balance).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_([x.account_id for x in balances])).all()}
        return [TrialBalanceRow(accounts[x.account_id], x.balance)
                for x in balances]

    def __populate_url(self, rows: list[TrialBalanceRow]) -> None:
        """Populates the URL of the trial balance rows.

        :param rows: The trial balance rows.
        :return: None.
        """
        def get_url(account: Account) -> str:
            """Returns the ledger URL of an account.

            :param account: The account.
            :return: The ledger URL of the account.
            """
            if self.period.is_default:
                return url_for("accounting.report.ledger-default",
                               currency=self.currency, account=account)
            return url_for("accounting.report.ledger",
                           currency=self.currency, account=account,
                           period=self.period)

        for row in rows:
            row.url = get_url(row.account)

    @staticmethod
    def __get_total_row(rows: list[TrialBalanceRow]) -> TrialBalanceRow:
        """Composes the total row.

        :param rows: The rows.
        :return: None.
        """
        row: TrialBalanceRow = TrialBalanceRow()
        row.is_total = True
        row.debit = sum([x.debit for x in rows if x.debit is not None])
        row.credit = sum([x.credit for x in rows if x.credit is not None])
        return row

    @staticmethod
    def populate_rows(rows: list[JournalRow]) -> None:
        pass

    @property
    def csv_field_names(self) -> list[str]:
        return ["Account", "Debit", "Credit"]

    @property
    def csv_filename(self) -> str:
        return f"trial-balance-{self.period.spec}.csv"

    def html(self) -> str:
        params: TrialBalanceParams = TrialBalanceParams(
            currency=self.currency,
            period=self.period,
            data_rows=self.data_rows,
            total=self.total)
        return render_template("accounting/report/trial-balance.html",
                               report=params)
