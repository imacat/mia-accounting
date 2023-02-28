# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/27

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
"""The summary helper.

"""
import typing as t

import sqlalchemy as sa

from accounting import db
from accounting.models import Account, JournalEntry


class SummaryAccount:
    """An account for a summary tag."""

    def __init__(self, account: Account, freq: int):
        """Constructs an account for a summary tag.

        :param account: The account.
        :param freq: The frequency of the tag with the account.
        """
        self.__account: Account = account
        """The account."""
        self.code: str = account.code
        """The account code."""
        self.freq: int = freq
        """The frequency of the tag with the account."""

    def __str__(self) -> str:
        """Returns the string representation of the account.

        :return: The string representation of the account.
        """
        return str(self.__account)

    def add_freq(self, freq: int) -> None:
        """Adds the frequency of an account.

        :param freq: The frequency of the tag name with the account.
        :return: None.
        """
        self.freq = self.freq + freq


class SummaryTag:
    """A summary tag."""

    def __init__(self, name: str):
        """Constructs a summary tag.

        :param name: The tag name.
        """
        self.name: str = name
        """The tag name."""
        self.__account_dict: dict[int, SummaryAccount] = {}
        """The accounts that come with the tag, in the order of their
        frequency."""
        self.freq: int = 0
        """The frequency of the tag."""

    def __str__(self) -> str:
        """Returns the string representation of the tag.

        :return: The string representation of the tag.
        """
        return self.name

    def add_account(self, account: Account, freq: int):
        """Adds an account.

        :param account: The associated account.
        :param freq: The frequency of the tag name with the account.
        :return: None.
        """
        self.__account_dict[account.id] = SummaryAccount(account, freq)
        self.freq = self.freq + freq

    @property
    def accounts(self) -> list[SummaryAccount]:
        """Returns the accounts by the order of their frequencies.

        :return: The accounts by the order of their frequencies.
        """
        return sorted(self.__account_dict.values(), key=lambda x: -x.freq)


class SummaryType:
    """A summary type"""

    def __init__(self, type_id: t.Literal["general", "travel", "bus"]):
        """Constructs a summary type.

        :param type_id: The type ID, either "general", "travel", or "bus".
        """
        self.id: t.Literal["general", "travel", "bus"] = type_id
        """The type ID."""
        self.__tag_dict: dict[str, SummaryTag] = {}
        """A dictionary from the tag name to their corresponding tag."""

    def add_tag(self, name: str, account: Account, freq: int) -> None:
        """Adds a tag.

        :param name: The tag name.
        :param account: The associated account.
        :param freq: The frequency of the tag name with the account.
        :return: None.
        """
        if name not in self.__tag_dict:
            self.__tag_dict[name] = SummaryTag(name)
        self.__tag_dict[name].add_account(account, freq)

    @property
    def tags(self) -> list[SummaryTag]:
        """Returns the tags by the order of their frequencies.

        :return: The tags by the order of their frequencies.
        """
        return sorted(self.__tag_dict.values(), key=lambda x: -x.freq)


class SummaryEntryType:
    """A summary type"""

    def __init__(self, entry_type_id: t.Literal["debit", "credit"]):
        """Constructs a summary entry type.

        :param entry_type_id: The entry type ID, either "debit" or "credit".
        """
        self.type: t.Literal["debit", "credit"] = entry_type_id
        """The entry type."""
        self.general: SummaryType = SummaryType("general")
        """The general tags."""
        self.travel: SummaryType = SummaryType("travel")
        """The travel tags."""
        self.bus: SummaryType = SummaryType("bus")
        """The bus tags."""
        self.__type_dict: dict[t.Literal["general", "travel", "bus"],
                               SummaryType] \
            = {x.id: x for x in {self.general, self.travel, self.bus}}
        """A dictionary from the type ID to the corresponding tags."""

    def add_tag(self, tag_type: t.Literal["general", "travel", "bus"],
                name: str, account: Account, freq: int) -> None:
        """Adds a tag.

        :param tag_type: The tag type, either "general", "travel", or "bus".
        :param name: The name.
        :param account: The associated account.
        :param freq: The frequency of the tag name with the account.
        :return: None.
        """
        self.__type_dict[tag_type].add_tag(name, account, freq)


class SummaryHelper:
    """The summary helper."""

    def __init__(self):
        """Constructs the summary helper."""
        self.debit: SummaryEntryType = SummaryEntryType("debit")
        """The debit tags."""
        self.credit: SummaryEntryType = SummaryEntryType("credit")
        """The credit tags."""
        self.types: set[SummaryEntryType] = {self.debit, self.credit}
        """The tags categorized by the entry types."""
        entry_type: sa.Label = sa.case((JournalEntry.is_debit, "debit"),
                                       else_="credit").label("entry_type")
        tag_type: sa.Label = sa.case(
            (JournalEntry.summary.like("_%—_%—_%→_%"), "bus"),
            (sa.or_(JournalEntry.summary.like("_%—_%→_%"),
                    JournalEntry.summary.like("_%—_%↔_%")), "travel"),
            else_="general").label("tag_type")
        tag: sa.Label = get_prefix(JournalEntry.summary, "—").label("tag")
        select: sa.Select = sa.Select(entry_type, tag_type, tag,
                                      JournalEntry.account_id,
                                      sa.func.count().label("freq"))\
            .filter(JournalEntry.summary.is_not(None),
                    JournalEntry.summary.like("_%—_%"))\
            .group_by(entry_type, tag_type, tag, JournalEntry.account_id)
        result: list[sa.Row] = db.session.execute(select).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_({x.account_id for x in result})).all()}
        entry_type_dict: dict[t.Literal["debit", "credit"], SummaryEntryType] \
            = {x.type: x for x in self.types}
        for row in result:
            entry_type_dict[row.entry_type].add_tag(
                row.tag_type, row.tag, accounts[row.account_id], row.freq)


def get_prefix(string: str | sa.Column, separator: str | sa.Column) \
        -> sa.Function:
    """Returns the SQL function to find the prefix of a string.

    :param string: The string.
    :param separator: The separator.
    :return: The position of the substring, starting from 1.
    """
    return sa.func.substr(string, 0, get_position(string, separator))


def get_position(string: str | sa.Column, substring: str | sa.Column) \
        -> sa.Function:
    """Returns the SQL function to find the position of a substring.

    :param string: The string.
    :param substring: The substring.
    :return: The position of the substring, starting from 1.
    """
    if db.engine.name == "postgresql":
        return sa.func.strpos(string, substring)
    return sa.func.instr(string, substring)
