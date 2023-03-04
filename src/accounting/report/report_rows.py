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
from decimal import Decimal
from abc import ABC, abstractmethod

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

    def __init__(self, entry: JournalEntry, transaction: Transaction,
                 account: Account, currency: Currency):
        """Constructs the row in the journal report.

        :param entry: The journal entry.
        :param transaction: The transaction.
        :param account: The account.
        :param currency: The currency.
        """
        self.is_debit: bool = entry.is_debit
        self.summary: str | None = entry.summary
        self.amount: Decimal = entry.amount
        self.transaction: Account = transaction
        self.account: Account = account
        self.currency: Currency = currency

    def as_dict(self) -> dict[str, t.Any]:
        return {"date": self.transaction.date.isoformat(),
                "currency": self.currency.name,
                "account": str(self.account),
                "summary": self.summary,
                "debit": self.amount if self.is_debit else None,
                "credit": None if self.is_debit else self.amount,
                "note": self.transaction.note}
