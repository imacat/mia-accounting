# The Mia! Accounting Project.
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
"""The reorder forms for the journal entry management.

"""
from datetime import date

import sqlalchemy as sa
from flask import request

from accounting import db
from accounting.models import JournalEntry


def sort_journal_entries_in(journal_entry_date: date,
                            exclude: int | None = None) -> None:
    """Sorts the journal entries under a date after changing the date or
    deleting a journal entry.

    :param journal_entry_date: The date of the journal entry.
    :param exclude: The journal entry ID to exclude.
    :return: None.
    """
    conditions: list[sa.BinaryExpression] \
        = [JournalEntry.date == journal_entry_date]
    if exclude is not None:
        conditions.append(JournalEntry.id != exclude)
    journal_entries: list[JournalEntry] = JournalEntry.query\
        .filter(*conditions)\
        .order_by(JournalEntry.no).all()
    for i in range(len(journal_entries)):
        if journal_entries[i].no != i + 1:
            journal_entries[i].no = i + 1


class JournalEntryReorderForm:
    """The form to reorder the journal entries."""

    def __init__(self, journal_entry_date: date):
        """Constructs the form to reorder the journal entries in a day.

        :param journal_entry_date: The date.
        """
        self.date: date = journal_entry_date
        self.is_modified: bool = False

    def save_order(self) -> None:
        """Saves the order of the account.

        :return:
        """
        journal_entries: list[JournalEntry] = JournalEntry.query\
            .filter(JournalEntry.date == self.date).all()

        # Collects the specified order.
        orders: dict[JournalEntry, int] = {}
        for journal_entry in journal_entries:
            if f"{journal_entry.id}-no" in request.form:
                try:
                    orders[journal_entry] \
                        = int(request.form[f"{journal_entry.id}-no"])
                except ValueError:
                    pass

        # Missing and invalid orders are appended to the end.
        missing: list[JournalEntry] \
            = [x for x in journal_entries if x not in orders]
        if len(missing) > 0:
            next_no: int = 1 if len(orders) == 0 else max(orders.values()) + 1
            for journal_entry in missing:
                orders[journal_entry] = next_no

        # Sort by the specified order first, and their original order.
        journal_entries.sort(key=lambda x: (orders[x], x.no))

        # Update the orders.
        with db.session.no_autoflush:
            for i in range(len(journal_entries)):
                if journal_entries[i].no != i + 1:
                    journal_entries[i].no = i + 1
                    self.is_modified = True
