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

from accounting.models import JournalEntry, Transaction, Account, Currency


class ReportRow(ABC):
    """A report row."""

    @abstractmethod
    def as_dict(self) -> dict[str, t.Any]:
        """Returns the row as a dictionary.

        :return: None.
        """


class JournalRow(ReportRow):
    """A row in the journal report."""

    def __init__(self, entry: JournalEntry):
        """Constructs the row in the journal report.

        :param entry: The journal entry.
        """
        self.entry: JournalEntry = entry
        """The journal entry."""
        self.summary: str | None = entry.summary
        """The summary."""
        self.currency_code: str = entry.currency_code
        """The currency code."""
        self.is_debit: bool = entry.is_debit
        """True for a debit journal entry, or False for a credit entry."""
        self.amount: Decimal = entry.amount
        """The amount."""
        self.transaction: Transaction | None = None
        """The transaction."""
        self.currency: Currency | None = None
        """The currency."""
        self.account: Account | None = None
        """The account."""

    def as_dict(self) -> dict[str, t.Any]:
        return {"date": self.transaction.date,
                "currency": str(self.currency),
                "account": str(self.account),
                "summary": self.summary,
                "debit": self.amount if self.is_debit else None,
                "credit": None if self.is_debit else self.amount,
                "note": self.transaction.note}


class LedgerRow(ReportRow):
    """A row in the ledger report."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the row in the journal report.

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
        if entry is not None:
            self.entry = entry
            self.summary = entry.summary
            self.debit = entry.amount if entry.is_debit else None
            self.credit = None if entry.is_debit else entry.amount

    def as_dict(self) -> dict[str, t.Any]:
        if self.is_total:
            return {"date": "Total",
                    "summary": None,
                    "debit": self.debit,
                    "credit": self.credit,
                    "balance": self.balance}
        return {"date": self.date,
                "summary": self.summary,
                "debit": self.debit,
                "credit": self.credit,
                "balance": self.balance}