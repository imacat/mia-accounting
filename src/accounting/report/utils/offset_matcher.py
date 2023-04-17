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
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from sqlalchemy.orm import selectinload

from accounting.locale import lazy_gettext
from accounting.models import Currency, Account, JournalEntry, \
    JournalEntryLineItem
from accounting.report.period import Period
from accounting.report.utils.unapplied import get_net_balances


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

    def __init__(self, currency: Currency, account: Account,
                 period: Period | None):
        """Constructs the offset matcher.

        :param currency: The currency.
        :param account: The account.
        :param period: The period, or None for all time.
        """
        self.__currency: Account = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        self.__period: Period | None = period
        """The period."""
        self.matched_pairs: list[OffsetPair] = []
        """A list of matched pairs."""
        self.__all_line_items: list[JournalEntryLineItem] = []
        """The unapplied debits or credits and unmatched offsets."""
        self.line_items: list[JournalEntryLineItem] = []
        """The unapplied debits or credits and unmatched offsets in the
        period."""
        self.__all_unapplied: list[JournalEntryLineItem] = []
        """The unapplied debits or credits."""
        self.unapplied: list[JournalEntryLineItem] = []
        """The unapplied debits or credits in the period."""
        self.__all_unmatched: list[JournalEntryLineItem] = []
        """The unmatched offsets."""
        self.unmatched: list[JournalEntryLineItem] = []
        """The unmatched offsets in the period."""
        self.__find_matches()
        self.__filter_by_period()

    def __find_matches(self) -> None:
        """Finds the matched original line items and their offsets.

        :return: None.
        """
        self.__get_line_items()
        if len(self.__all_unapplied) == 0 or len(self.__all_unmatched) == 0:
            return
        remains: list[JournalEntryLineItem] = self.__all_unmatched.copy()
        for original_item in self.__all_unapplied:
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

    def __get_line_items(self) -> None:
        """Returns the unapplied original line items and unmatched offsets of
        the account.

        :return: The unapplied original line items and unmatched offsets of the
            account.
        """
        net_balances: dict[int, Decimal | None] \
            = get_net_balances(self.__currency, self.__account, None)
        unmatched_offset_condition: sa.BinaryExpression \
            = sa.and_(Account.id == self.__account.id,
                      JournalEntryLineItem.currency_code
                      == self.__currency.code,
                      JournalEntryLineItem.original_line_item_id.is_(None),
                      sa.or_(sa.and_(Account.base_code.startswith("2"),
                                     JournalEntryLineItem.is_debit),
                             sa.and_(Account.base_code.startswith("1"),
                                     sa.not_(JournalEntryLineItem.is_debit))))
        self.__all_line_items = JournalEntryLineItem.query \
            .join(Account).join(JournalEntry) \
            .filter(sa.or_(JournalEntryLineItem.id.in_(net_balances),
                           unmatched_offset_condition)) \
            .order_by(JournalEntry.date, JournalEntry.no,
                      JournalEntryLineItem.is_debit, JournalEntryLineItem.no) \
            .options(selectinload(JournalEntryLineItem.currency),
                     selectinload(JournalEntryLineItem.journal_entry)).all()
        for line_item in self.__all_line_items:
            line_item.is_offset = line_item.id in net_balances
        self.__all_unapplied = [x for x in self.__all_line_items
                                if x.is_offset]
        for line_item in self.__all_unapplied:
            line_item.net_balance = line_item.amount \
                if net_balances[line_item.id] is None \
                else net_balances[line_item.id]
        self.__all_unmatched = [x for x in self.__all_line_items
                                if not x.is_offset]
        self.__populate_accumulated_balances()

    def __populate_accumulated_balances(self) -> None:
        """Populates the accumulated balances of the line items.

        :return: None.
        """
        balance: Decimal = Decimal("0")
        for line_item in self.__all_line_items:
            amount: Decimal = line_item.amount if line_item.is_offset \
                else line_item.net_balance
            if line_item.is_debit:
                line_item.debit = amount
                line_item.credit = None
                balance = balance + amount
            else:
                line_item.debit = None
                line_item.credit = amount
                balance = balance - amount
            line_item.balance = balance

    def __filter_by_period(self) -> None:
        """Filters the line items by the period.

        :return: None.
        """
        self.line_items = self.__all_line_items.copy()
        if self.__period is not None:
            if self.__period.start is not None:
                self.line_items \
                    = [x for x in self.line_items
                       if x.journal_entry.date >= self.__period.start]
            if self.__period.end is not None:
                self.line_items \
                    = [x for x in self.line_items
                       if x.journal_entry.date <= self.__period.end]
        self.unapplied = [x for x in self.line_items if x.is_offset]
        self.unmatched = [x for x in self.line_items if not x.is_offset]

    @property
    def status(self) -> str | LazyString:
        """Returns the match status message.

        :return: The match status message.
        """
        if len(self.__all_unmatched) == 0:
            return lazy_gettext("There is no unmatched offset.")
        if len(self.matched_pairs) == 0:
            return lazy_gettext(
                    "%(total)s unmatched offsets without original items.",
                    total=len(self.__all_unmatched))
        return lazy_gettext(
            "%(matches)s unmatched offsets out of %(total)s"
            " can match with their original items.",
            matches=len(self.matched_pairs),
            total=len(self.__all_unmatched))

    def match(self) -> None:
        """Matches the original line items with offsets.

        :return: None.
        """
        for pair in self.matched_pairs:
            pair.offset.original_line_item_id = pair.original_line_item.id
