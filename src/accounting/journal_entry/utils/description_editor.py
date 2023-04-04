# The Mia! Accounting Project.
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
"""The description editor.

"""
import re
import typing as t

import sqlalchemy as sa

from accounting import db
from accounting.models import Account, JournalEntryLineItem
from accounting.utils.options import options, Recurring


class DescriptionAccount:
    """An account for a description tag."""

    def __init__(self, account: Account, freq: int):
        """Constructs an account for a description tag.

        :param account: The account.
        :param freq: The frequency of the tag with the account.
        """
        self.__account: Account = account
        """The account."""
        self.id: int = account.id
        """The account ID."""
        self.code: str = account.code
        """The account code."""
        self.is_need_offset: bool = account.is_need_offset
        """Whether the journal entry line items of this account need offset."""
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


class DescriptionTag:
    """A description tag."""

    def __init__(self, name: str):
        """Constructs a description tag.

        :param name: The tag name.
        """
        self.name: str = name
        """The tag name."""
        self.__account_dict: dict[int, DescriptionAccount] = {}
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
        self.__account_dict[account.id] = DescriptionAccount(account, freq)
        self.freq = self.freq + freq

    @property
    def accounts(self) -> list[DescriptionAccount]:
        """Returns the accounts by the order of their frequencies.

        :return: The accounts by the order of their frequencies.
        """
        return sorted(self.__account_dict.values(), key=lambda x: -x.freq)

    @property
    def account_codes(self) -> list[str]:
        """Returns the account codes by the order of their frequencies.

        :return: The account codes by the order of their frequencies.
        """
        return [x.code for x in self.accounts]


class DescriptionType:
    """A description type"""

    def __init__(self, type_id: t.Literal["general", "travel", "bus"]):
        """Constructs a description type.

        :param type_id: The type ID, either "general", "travel", or "bus".
        """
        self.id: t.Literal["general", "travel", "bus"] = type_id
        """The type ID."""
        self.__tag_dict: dict[str, DescriptionTag] = {}
        """A dictionary from the tag name to their corresponding tag."""

    def add_tag(self, name: str, account: Account, freq: int) -> None:
        """Adds a tag.

        :param name: The tag name.
        :param account: The associated account.
        :param freq: The frequency of the tag name with the account.
        :return: None.
        """
        if name not in self.__tag_dict:
            self.__tag_dict[name] = DescriptionTag(name)
        self.__tag_dict[name].add_account(account, freq)

    @property
    def tags(self) -> list[DescriptionTag]:
        """Returns the tags by the order of their frequencies.

        :return: The tags by the order of their frequencies.
        """
        return sorted(self.__tag_dict.values(), key=lambda x: -x.freq)


class DescriptionRecurring:
    """A recurring transaction."""

    def __init__(self, name: str, account: Account, description_template: str):
        """Constructs a recurring transaction.

        :param name: The name.
        :param description_template: The description template.
        :param account: The account.
        """
        self.name: str = name
        self.account: DescriptionAccount = DescriptionAccount(account, 0)
        self.description_template: str = description_template

    @property
    def account_codes(self) -> list[str]:
        """Returns the account codes by the order of their frequencies.

        :return: The account codes by the order of their frequencies.
        """
        return [self.account.code]


class DescriptionDebitCredit:
    """The description on debit or credit."""

    def __init__(self, debit_credit: t.Literal["debit", "credit"]):
        """Constructs the description on debit or credit.

        :param debit_credit: Either "debit" or "credit".
        """
        self.debit_credit: t.Literal["debit", "credit"] = debit_credit
        """Either debit or credit."""
        self.general: DescriptionType = DescriptionType("general")
        """The general tags."""
        self.travel: DescriptionType = DescriptionType("travel")
        """The travel tags."""
        self.bus: DescriptionType = DescriptionType("bus")
        """The bus tags."""
        self.__type_dict: dict[t.Literal["general", "travel", "bus"],
                               DescriptionType] \
            = {x.id: x for x in {self.general, self.travel, self.bus}}
        """A dictionary from the type ID to the corresponding tags."""
        self.recurring: list[DescriptionRecurring] = []
        """The recurring transactions."""

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

    @property
    def accounts(self) -> list[DescriptionAccount]:
        """Returns the suggested accounts of all tags in the description editor
        in debit or credit, in their frequency order.

        :return: The suggested accounts of all tags, in their frequency order.
        """
        accounts: dict[int, DescriptionAccount] = {}
        freq: dict[int, int] = {}
        for tag_type in self.__type_dict.values():
            for tag in tag_type.tags:
                for account in tag.accounts:
                    accounts[account.id] = account
                    if account.id not in freq:
                        freq[account.id] = 0
                    freq[account.id] \
                        = freq[account.id] + account.freq
        for recurring in self.recurring:
            accounts[recurring.account.id] = recurring.account
            if recurring.account.id not in freq:
                freq[recurring.account.id] = 0
        return [accounts[y] for y in sorted(freq.keys(),
                                            key=lambda x: -freq[x])]


class DescriptionEditor:
    """The description editor."""

    def __init__(self):
        """Constructs the description editor."""
        self.debit: DescriptionDebitCredit = DescriptionDebitCredit("debit")
        """The debit tags."""
        self.credit: DescriptionDebitCredit = DescriptionDebitCredit("credit")
        """The credit tags."""
        self.__init_tags()
        self.__init_recurring()

    def __init_tags(self):
        """Initializes the tags.

        :return: None.
        """
        debit_credit: sa.Label = sa.case(
            (JournalEntryLineItem.is_debit, "debit"),
            else_="credit").label("debit_credit")
        tag_type: sa.Label = sa.case(
            (JournalEntryLineItem.description.like("_%—_%—_%→_%"), "bus"),
            (sa.or_(JournalEntryLineItem.description.like("_%—_%→_%"),
                    JournalEntryLineItem.description.like("_%—_%↔_%")),
             "travel"),
            else_="general").label("tag_type")
        tag: sa.Label = get_prefix(JournalEntryLineItem.description, "—")\
            .label("tag")
        select: sa.Select = sa.Select(debit_credit, tag_type, tag,
                                      JournalEntryLineItem.account_id,
                                      sa.func.count().label("freq"))\
            .filter(JournalEntryLineItem.description.is_not(None),
                    JournalEntryLineItem.description.like("_%—_%"),
                    JournalEntryLineItem.original_line_item_id.is_(None))\
            .group_by(debit_credit, tag_type, tag,
                      JournalEntryLineItem.account_id)
        result: list[sa.Row] = db.session.execute(select).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_({x.account_id for x in result})).all()}
        debit_credit_dict: dict[t.Literal["debit", "credit"],
                                DescriptionDebitCredit] \
            = {x.debit_credit: x for x in {self.debit, self.credit}}
        for row in result:
            debit_credit_dict[row.debit_credit].add_tag(
                row.tag_type, row.tag, accounts[row.account_id], row.freq)

    def __init_recurring(self) -> None:
        """Initializes the recurring transactions.

        :return: None.
        """
        recurring: Recurring = options.recurring
        accounts: dict[str, Account] \
            = self.__get_accounts(recurring.codes)
        self.debit.recurring \
            = [DescriptionRecurring(x.name, accounts[x.account_code],
                                    x.description_template)
               for x in recurring.expenses]
        self.credit.recurring \
            = [DescriptionRecurring(x.name, accounts[x.account_code],
                                    x.description_template)
               for x in recurring.incomes]

    @staticmethod
    def __get_accounts(codes: set[str]) -> dict[str, Account]:
        """Finds and returns the accounts by codes.

        :param codes: The account codes.
        :return: The account.
        """
        if len(codes) == 0:
            return {}

        def get_condition(code0: str) -> sa.BinaryExpression:
            m: re.Match = re.match(r"^(\d{4})-(\d{3})$", code0)
            assert m is not None,\
                f"Malformed account code \"{code0}\" for regular transactions."
            return sa.and_(Account.base_code == m.group(1),
                           Account.no == int(m.group(2)))

        conditions: list[sa.BinaryExpression] \
            = [get_condition(x) for x in codes]
        accounts: dict[str, Account] \
            = {x.code: x for x in
               Account.query.filter(sa.or_(*conditions)).all()}
        for code in codes:
            assert code in accounts,\
                f"Unknown account \"{code}\" for regular transactions."
        return accounts


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
