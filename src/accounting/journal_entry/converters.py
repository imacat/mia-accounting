# The Mia! Accounting Project.
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
"""The path converters for the journal entry management.

"""
from datetime import date

from flask import abort
from sqlalchemy.orm import selectinload
from werkzeug.routing import BaseConverter

from accounting.models import JournalEntry, JournalEntryLineItem
from accounting.utils.journal_entry_types import JournalEntryType


class JournalEntryConverter(BaseConverter):
    """The journal entry converter to convert the journal entry ID from and to
    the corresponding journal entry in the routes."""

    def to_python(self, value: str) -> JournalEntry:
        """Converts a journal entry ID to a journal entry.

        :param value: The journal entry ID.
        :return: The corresponding journal entry.
        """
        journal_entry: JournalEntry | None = JournalEntry.query\
            .join(JournalEntryLineItem)\
            .filter(JournalEntry.id == value)\
            .options(selectinload(JournalEntry.line_items)
                     .selectinload(JournalEntryLineItem.offsets)
                     .selectinload(JournalEntryLineItem.journal_entry))\
            .first()
        if journal_entry is None:
            abort(404)
        return journal_entry

    def to_url(self, value: JournalEntry) -> str:
        """Converts a journal entry to its ID.

        :param value: The journal entry.
        :return: The ID.
        """
        return str(value.id)


class JournalEntryTypeConverter(BaseConverter):
    """The journal entry converter to convert the journal entry type ID from
    and to the corresponding journal entry type in the routes."""

    def to_python(self, value: str) -> JournalEntryType:
        """Converts a journal entry ID to a journal entry.

        :param value: The journal entry ID.
        :return: The corresponding journal entry type.
        """
        type_dict: dict[str, JournalEntryType] \
            = {x.value: x for x in JournalEntryType}
        journal_entry_type: JournalEntryType | None = type_dict.get(value)
        if journal_entry_type is None:
            abort(404)
        return journal_entry_type

    def to_url(self, value: JournalEntryType) -> str:
        """Converts a journal entry type to its ID.

        :param value: The journal entry type.
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
