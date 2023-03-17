# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/19

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
"""The path converters for the transaction management.

"""
from datetime import date

from flask import abort
from sqlalchemy.orm import selectinload
from werkzeug.routing import BaseConverter

from accounting.models import Transaction, JournalEntry
from accounting.utils.txn_types import TransactionType


class TransactionConverter(BaseConverter):
    """The transaction converter to convert the transaction ID from and to the
    corresponding transaction in the routes."""

    def to_python(self, value: str) -> Transaction:
        """Converts a transaction ID to a transaction.

        :param value: The transaction ID.
        :return: The corresponding transaction.
        """
        transaction: Transaction | None = Transaction.query\
            .join(JournalEntry)\
            .filter(Transaction.id == value)\
            .options(selectinload(Transaction.entries)
                     .selectinload(JournalEntry.offsets)
                     .selectinload(JournalEntry.transaction))\
            .first()
        if transaction is None:
            abort(404)
        return transaction

    def to_url(self, value: Transaction) -> str:
        """Converts a transaction to its ID.

        :param value: The transaction.
        :return: The ID.
        """
        return str(value.id)


class TransactionTypeConverter(BaseConverter):
    """The transaction converter to convert the transaction type ID from and to
    the corresponding transaction type in the routes."""

    def to_python(self, value: str) -> TransactionType:
        """Converts a transaction ID to a transaction.

        :param value: The transaction ID.
        :return: The corresponding transaction.
        """
        type_dict: dict[str, TransactionType] \
            = {x.value: x for x in TransactionType}
        txn_type: TransactionType | None = type_dict.get(value)
        if txn_type is None:
            abort(404)
        return txn_type

    def to_url(self, value: TransactionType) -> str:
        """Converts a transaction type to its ID.

        :param value: The transaction type.
        :return: The ID.
        """
        return str(value.value)


class DateConverter(BaseConverter):
    """The date converter to convert the ISO date from and to the
    corresponding date in the routes."""

    def to_python(self, value: str) -> date:
        """Converts an ISO date to a date.

        :param value: The ISO date.
        :return: The corresponding date.
        """
        try:
            return date.fromisoformat(value)
        except ValueError:
            abort(404)

    def to_url(self, value: date) -> str:
        """Converts a date to its ISO date.

        :param value: The date.
        :return: The ISO date.
        """
        return value.isoformat()
