# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/10

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
"""The reorder forms for the transaction management.

"""
from __future__ import annotations

from datetime import date

from flask import request

from accounting import db
from accounting.models import Transaction


def sort_transactions_in(txn_date: date, exclude: int) -> None:
    """Sorts the transactions under a date after changing the date or deleting
    a transaction.

    :param txn_date: The date of the transaction.
    :param exclude: The transaction ID to exclude.
    :return: None.
    """
    transactions: list[Transaction] = Transaction.query\
        .filter(Transaction.date == txn_date,
                Transaction.id != exclude)\
        .order_by(Transaction.no).all()
    for i in range(len(transactions)):
        if transactions[i].no != i + 1:
            transactions[i].no = i + 1


class TransactionReorderForm:
    """The form to reorder the transactions."""

    def __init__(self, txn_date: date):
        """Constructs the form to reorder the transactions in a day.

        :param txn_date: The date.
        """
        self.date: date = txn_date
        self.is_modified: bool = False

    def save_order(self) -> None:
        """Saves the order of the account.

        :return:
        """
        transactions: list[Transaction] = Transaction.query\
            .filter(Transaction.date == self.date).all()

        # Collects the specified order.
        orders: dict[Transaction, int] = {}
        for txn in transactions:
            if f"{txn.id}-no" in request.form:
                try:
                    orders[txn] = int(request.form[f"{txn.id}-no"])
                except ValueError:
                    pass

        # Missing and invalid orders are appended to the end.
        missing: list[Transaction] \
            = [x for x in transactions if x not in orders]
        if len(missing) > 0:
            next_no: int = 1 if len(orders) == 0 else max(orders.values()) + 1
            for txn in missing:
                orders[txn] = next_no

        # Sort by the specified order first, and their original order.
        transactions.sort(key=lambda x: (orders[x], x.no))

        # Update the orders.
        with db.session.no_autoflush:
            for i in range(len(transactions)):
                if transactions[i].no != i + 1:
                    transactions[i].no = i + 1
                    self.is_modified = True
