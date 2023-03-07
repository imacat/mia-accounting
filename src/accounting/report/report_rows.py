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
"""The rows of the reports.

"""
import typing as t
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from accounting.locale import gettext
from accounting.models import JournalEntry, Transaction, Account, Currency


class ReportRow(ABC):
    """A row in the report."""

    @abstractmethod
    def as_dict(self) -> dict[str, t.Any]:
        """Returns the row as a dictionary.

        :return: None.
        """


class JournalRow(ReportRow):
    """A row in the journal."""

    def __init__(self, entry: JournalEntry):
        """Constructs the row in the journal.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry = entry
        """The journal entry."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.currency: Currency | None = None
        """The currency."""
        self.account: Account | None = None
        """The account."""
        self.summary: str | None = entry.summary
        """The summary."""
        self.debit: Decimal | None = entry.amount if entry.is_debit else None
        """The debit amount."""
        self.credit: Decimal | None = None if entry.is_debit else entry.amount
        """The credit amount."""
        self.amount: Decimal = entry.amount
        """The amount."""

    def as_dict(self) -> dict[str, t.Any]:
        return {"Date": self.transaction.date,
                "Currency": self.currency.code,
                "Account": str(self.account).title(),
                "Summary": self.summary,
                "Debit": self.debit,
                "Credit": self.credit,
                "Note": self.transaction.note}


class LedgerRow(ReportRow):
    """A row in the ledger."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the row in the ledger.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry | None = None
        """The journal entry."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.is_total: bool = False
        """Whether this is the total row."""
        self.date: date | None = None
        """The date."""
        self.summary: str | None = None
        """The summary."""
        self.debit: Decimal | None = None
        """The debit amount."""
        self.credit: Decimal | None = None
        """The credit amount."""
        self.balance: Decimal | None = None
        """The balance."""
        self.note: str | None = None
        """The note."""
        if entry is not None:
            self.entry = entry
            self.summary = entry.summary
            self.debit = entry.amount if entry.is_debit else None
            self.credit = None if entry.is_debit else entry.amount

    def as_dict(self) -> dict[str, t.Any]:
        if self.is_total:
            return {"Date": "Total",
                    "Summary": None,
                    "Debit": self.debit,
                    "Credit": self.credit,
                    "Balance": self.balance,
                    "Note": None}
        return {"Date": self.date,
                "Summary": self.summary,
                "Debit": self.debit,
                "Credit": self.credit,
                "Balance": self.balance,
                "Note": self.note}


class IncomeExpensesRow(ReportRow):
    """A row in the income and expenses."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the row in the income and expenses.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry | None = None
        """The journal entry."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.is_total: bool = False
        """Whether this is the total row."""
        self.date: date | None = None
        """The date."""
        self.account: Account | None = None
        """The date."""
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

    def as_dict(self) -> dict[str, t.Any]:
        if self.is_total:
            return {"Date": "Total",
                    "Account": None,
                    "Summary": None,
                    "Income": self.income,
                    "Expense": self.expense,
                    "Balance": self.balance,
                    "Note": None}
        return {"Date": self.date,
                "Account": str(self.account).title(),
                "Summary": self.summary,
                "Income": self.income,
                "Expense": self.expense,
                "Balance": self.balance,
                "Note": self.note}


class TrialBalanceRow(ReportRow):
    """A row in the trial balance."""

    def __init__(self, account: Account | None = None,
                 balance: Decimal | None = None):
        """Constructs the row in the trial balance.

        :param account: The account.
        :param balance: The balance.
        """
        self.is_total: bool = False
        """Whether this is the total row."""
        self.account: Account | None = account
        """The account."""
        self.debit: Decimal | None = None
        """The debit amount."""
        self.credit: Decimal | None = None
        """The credit amount."""
        self.url: str | None = None
        """The URL."""
        if balance is not None:
            if balance > 0:
                self.debit = balance
            if balance < 0:
                self.credit = -balance

    def as_dict(self) -> dict[str, t.Any]:
        if self.is_total:
            return {"Account": gettext("Total"),
                    "Debit": self.debit,
                    "Credit": self.credit}
        return {"Account": str(self.account).title(),
                "Debit": self.debit,
                "Credit": self.credit}


class IncomeStatementRow(ReportRow):
    """A row in the income statement."""

    def __init__(self,
                 code: str | None = None,
                 title: str | None = None,
                 amount: Decimal | None = None,
                 is_category: bool = False,
                 is_total: bool = False,
                 is_subcategory: bool = False,
                 is_subtotal: bool = False,
                 url: str | None = None):
        """Constructs the row in the income statement.

        :param code: The account code.
        :param title: The account title.
        :param amount: The amount.
        :param is_category: True for a category, or False otherwise.
        :param is_total: True for a total, or False otherwise.
        :param is_subcategory: True for a subcategory, or False otherwise.
        :param is_subtotal: True for a subtotal, or False otherwise.
        :param url: The URL for the account.
        """
        self.is_total: bool = False
        """Whether this is the total row."""
        self.code: str | None = code
        """The account code."""
        self.title: str | None = title
        """The account code."""
        self.amount: Decimal | None = amount
        """The amount."""
        self.is_category: bool = is_category
        """True if this row is a category, or False otherwise."""
        self.is_total: bool = is_total
        """True if this row is a total, or False otherwise."""
        self.is_subcategory: bool = is_subcategory
        """True if this row is a subcategory, or False otherwise."""
        self.is_subtotal: bool = is_subtotal
        """True if this row is a subtotal, or False otherwise."""
        self.url: str | None = url
        """The URL."""

    def as_dict(self) -> dict[str, t.Any]:
        if self.is_subtotal:
            return {"": "Total",
                    "Amount": self.amount}
        if self.is_total:
            return {"": self.title,
                    "Amount": self.amount}
        return {"": f"{self.code} {self.title}",
                "Amount": self.amount}
