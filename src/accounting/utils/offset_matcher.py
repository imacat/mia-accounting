# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/8

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
"""The forms for the unmatched offset management.

"""
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from accounting.models import Account, JournalEntry, JournalEntryLineItem
from accounting.utils.unapplied import get_unapplied_original_line_items


class OffsetPair:
    """A pair of an original line item and its offset."""

    def __init__(self, original_line_item: JournalEntryLineItem,
                 offset: JournalEntryLineItem):
        """Constructs a pair of an original line item and its offset.

        :param original_line_item: The original line item.
        :param offset: The offset.
        """
        self.original_line_item: JournalEntryLineItem = original_line_item
        """The original line item."""
        self.offset: JournalEntryLineItem = offset
        """The offset."""


class OffsetMatcher:
    """The offset matcher."""

    def __init__(self, account: Account):
        """Constructs the offset matcher.

        :param account: The account.
        """
        self.account: Account = account
        """The account."""
        self.matched_pairs: list[OffsetPair] = []
        """A list of matched pairs."""
        self.is_having_matches: bool = False
        """Whether there is any matches."""
        self.total: int = 0
        """The total number of unapplied debits or credits."""
        self.unapplied: list[JournalEntryLineItem] = []
        """The unapplied debits or credits."""
        self.unmatched_offsets: list[JournalEntryLineItem] = []
        """The unmatched offsets."""
        self.__find_matches()

    def __find_matches(self) -> None:
        """Finds the matched original line items and their offsets.

        :return: None.
        """
        self.unapplied: list[JournalEntryLineItem] \
            = get_unapplied_original_line_items(self.account)
        self.total = len(self.unapplied)
        if self.total == 0:
            self.is_having_matches = False
            return
        self.unmatched_offsets = self.__get_unmatched_offsets()
        remains: list[JournalEntryLineItem] = self.unmatched_offsets.copy()
        for original_item in self.unapplied:
            offset_candidates: list[JournalEntryLineItem] \
                = [x for x in remains
                   if (x.journal_entry.date > original_item.journal_entry.date
                       or (x.journal_entry.date
                           == original_item.journal_entry.date
                           and x.journal_entry.no
                           > original_item.journal_entry.no))
                   and x.currency_code == original_item.currency_code
                   and x.description == original_item.description
                   and x.amount == original_item.net_balance]
            if len(offset_candidates) == 0:
                continue
            self.matched_pairs.append(
                OffsetPair(original_item, offset_candidates[0]))
            original_item.match = offset_candidates[0]
            offset_candidates[0].match = original_item
            remains.remove(offset_candidates[0])
        self.is_having_matches = len(self.matched_pairs) > 0

    def __get_unmatched_offsets(self) -> list[JournalEntryLineItem]:
        """Returns the unmatched offsets of an account.

        :return: The unmatched offsets of the account.
        """
        return JournalEntryLineItem.query.join(Account).join(JournalEntry)\
            .filter(Account.id == self.account.id,
                    JournalEntryLineItem.original_line_item_id.is_(None),
                    sa.or_(sa.and_(Account.base_code.startswith("2"),
                                   JournalEntryLineItem.is_debit),
                           sa.and_(Account.base_code.startswith("1"),
                                   sa.not_(JournalEntryLineItem.is_debit))))\
            .order_by(JournalEntry.date, JournalEntry.no,
                      JournalEntryLineItem.is_debit, JournalEntryLineItem.no)\
            .options(selectinload(JournalEntryLineItem.currency),
                     selectinload(JournalEntryLineItem.journal_entry)).all()

    @property
    def matches(self) -> int:
        """Returns the number of matches.

        :return: The number of matches.
        """
        return len(self.matched_pairs)

    def match(self) -> None:
        """Matches the original line items with offsets.

        :return: None.
        """
        for pair in self.matched_pairs:
            pair.offset.original_line_item_id = pair.original_line_item.id
