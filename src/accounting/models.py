# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/25

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
"""The data models.

"""
from __future__ import annotations

import re
import typing as t
from decimal import Decimal

import sqlalchemy as sa
from babel import Locale
from flask_babel import get_locale, get_babel
from sqlalchemy import text

from accounting import db
from accounting.locale import gettext
from accounting.utils.user import user_cls, user_pk_column


class BaseAccount(db.Model):
    """A base account."""
    __tablename__ = "accounting_base_accounts"
    """The table name."""
    code = db.Column(db.String, nullable=False, primary_key=True)
    """The code."""
    title_l10n = db.Column("title", db.String, nullable=False)
    """The title."""
    l10n = db.relationship("BaseAccountL10n", back_populates="account",
                           lazy=False)
    """The localized titles."""
    accounts = db.relationship("Account", back_populates="base")
    """The descendant accounts under the base account."""

    def __str__(self) -> str:
        """Returns the string representation of the base account.

        :return: The string representation of the base account.
        """
        return f"{self.code} {self.title.title()}"

    @property
    def title(self) -> str:
        """Returns the title in the current locale.

        :return: The title in the current locale.
        """
        current_locale: Locale = get_locale()
        if current_locale == get_babel().instance.default_locale:
            return self.title_l10n
        for l10n in self.l10n:
            if l10n.locale == str(current_locale):
                return l10n.title
        return self.title_l10n

    @property
    def query_values(self) -> list[str]:
        """Returns the values to be queried.

        :return: The values to be queried.
        """
        return [self.code, self.title_l10n] + [x.title for x in self.l10n]


class BaseAccountL10n(db.Model):
    """A localized base account title."""
    __tablename__ = "accounting_base_accounts_l10n"
    """The table name."""
    account_code = db.Column(db.String,
                             db.ForeignKey(BaseAccount.code,
                                           onupdate="CASCADE",
                                           ondelete="CASCADE"),
                             nullable=False, primary_key=True)
    """The code of the account."""
    account = db.relationship(BaseAccount, back_populates="l10n")
    """The account."""
    locale = db.Column(db.String, nullable=False, primary_key=True)
    """The locale."""
    title = db.Column(db.String, nullable=False)
    """The localized title."""


class Account(db.Model):
    """An account."""
    __tablename__ = "accounting_accounts"
    """The table name."""
    id = db.Column(db.Integer, nullable=False, primary_key=True,
                   autoincrement=False)
    """The account ID."""
    base_code = db.Column(db.String,
                          db.ForeignKey(BaseAccount.code, onupdate="CASCADE",
                                        ondelete="CASCADE"),
                          nullable=False)
    """The code of the base account."""
    base = db.relationship(BaseAccount, back_populates="accounts")
    """The base account."""
    no = db.Column(db.Integer, nullable=False, default=text("1"))
    """The account number under the base account."""
    title_l10n = db.Column("title", db.String, nullable=False)
    """The title."""
    is_need_offset = db.Column(db.Boolean, nullable=False, default=False)
    """Whether the journal entry line items of this account need offset."""
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of creation."""
    created_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the creator."""
    created_by = db.relationship(user_cls, foreign_keys=created_by_id)
    """The creator."""
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of last update."""
    updated_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the updator."""
    updated_by = db.relationship(user_cls, foreign_keys=updated_by_id)
    """The updator."""
    l10n = db.relationship("AccountL10n", back_populates="account",
                           lazy=False)
    """The localized titles."""
    line_items = db.relationship("JournalEntryLineItem",
                                 back_populates="account")
    """The journal entry line items."""

    CASH_CODE: str = "1111-001"
    """The code of the cash account,"""
    ACCUMULATED_CHANGE_CODE: str = "3351-001"
    """The code of the accumulated-change account,"""
    NET_CHANGE_CODE: str = "3353-001"
    """The code of the net-change account,"""

    def __str__(self) -> str:
        """Returns the string representation of this account.

        :return: The string representation of this account.
        """
        return f"{self.base_code}-{self.no:03d} {self.title.title()}"

    @property
    def code(self) -> str:
        """Returns the code.

        :return: The code.
        """
        return f"{self.base_code}-{self.no:03d}"

    @property
    def title(self) -> str:
        """Returns the title in the current locale.

        :return: The title in the current locale.
        """
        current_locale: Locale = get_locale()
        if current_locale == get_babel().instance.default_locale:
            return self.title_l10n
        for l10n in self.l10n:
            if l10n.locale == str(current_locale):
                return l10n.title
        return self.title_l10n

    @title.setter
    def title(self, value: str) -> None:
        """Sets the title in the current locale.

        :param value: The new title.
        :return: None.
        """
        if self.title_l10n is None:
            self.title_l10n = value
            return
        current_locale: Locale = get_locale()
        if current_locale == get_babel().instance.default_locale:
            self.title_l10n = value
            return
        for l10n in self.l10n:
            if l10n.locale == str(current_locale):
                l10n.title = value
                return
        self.l10n.append(AccountL10n(locale=str(current_locale), title=value))

    @property
    def is_real(self) -> bool:
        """Returns whether the account is a real account.

        :return: True if the account is a real account, or False otherwise.
        """
        return self.base_code[0] in {"1", "2", "3"}

    @property
    def is_nominal(self) -> bool:
        """Returns whether the account is a nominal account.

        :return: True if the account is a nominal account, or False otherwise.
        """
        return not self.is_real

    @property
    def query_values(self) -> list[str]:
        """Returns the values to be queried.

        :return: The values to be queried.
        """
        return [self.code, self.title_l10n] + [x.title for x in self.l10n]

    @property
    def is_modified(self) -> bool:
        """Returns whether a product account was modified.

        :return: True if modified, or False otherwise.
        """
        if db.session.is_modified(self):
            return True
        for l10n in self.l10n:
            if db.session.is_modified(l10n):
                return True
        return False

    @property
    def can_delete(self) -> bool:
        """Returns whether the account can be deleted.

        :return: True if the account can be deleted, or False otherwise.
        """
        if self.code in {"1111-001", "3351-001", "3353-001"}:
            return False
        return len(self.line_items) == 0

    def delete(self) -> None:
        """Deletes this account.

        :return: None.
        """
        AccountL10n.query.filter(AccountL10n.account == self).delete()
        cls: t.Type[t.Self] = self.__class__
        cls.query.filter(cls.id == self.id).delete()

    @classmethod
    def find_by_code(cls, code: str) -> t.Self | None:
        """Finds an account by its code.

        :param code: The code.
        :return: The account, or None if this account does not exist.
        """
        m = re.match(r"^([1-9]{4})-(\d{3})$", code)
        if m is None:
            return None
        return cls.query.filter(cls.base_code == m.group(1),
                                cls.no == int(m.group(2))).first()

    @classmethod
    def selectable_debit(cls) -> list[t.Self]:
        """Returns the selectable debit accounts.
        Payable line items can not start from debit.

        :return: The selectable debit accounts.
        """
        return cls.query.filter(sa.or_(cls.base_code.startswith("1"),
                                       sa.and_(cls.base_code.startswith("2"),
                                               sa.not_(cls.is_need_offset)),
                                       cls.base_code.startswith("3"),
                                       cls.base_code.startswith("5"),
                                       cls.base_code.startswith("6"),
                                       cls.base_code.startswith("75"),
                                       cls.base_code.startswith("76"),
                                       cls.base_code.startswith("77"),
                                       cls.base_code.startswith("78"),
                                       cls.base_code.startswith("8"),
                                       cls.base_code.startswith("9")),
                                cls.base_code != "3351",
                                cls.base_code != "3353")\
            .order_by(cls.base_code, cls.no).all()

    @classmethod
    def selectable_credit(cls) -> list[t.Self]:
        """Returns the selectable debit accounts.
        Receivable line items can not start from credit.

        :return: The selectable debit accounts.
        """
        return cls.query.filter(sa.or_(sa.and_(cls.base_code.startswith("1"),
                                               sa.not_(cls.is_need_offset)),
                                       cls.base_code.startswith("2"),
                                       cls.base_code.startswith("3"),
                                       cls.base_code.startswith("4"),
                                       cls.base_code.startswith("71"),
                                       cls.base_code.startswith("72"),
                                       cls.base_code.startswith("73"),
                                       cls.base_code.startswith("74"),
                                       cls.base_code.startswith("8"),
                                       cls.base_code.startswith("9")),
                                cls.base_code != "3351",
                                cls.base_code != "3353")\
            .order_by(cls.base_code, cls.no).all()

    @classmethod
    def cash(cls) -> t.Self:
        """Returns the cash account.

        :return: The cash account
        """
        return cls.find_by_code(cls.CASH_CODE)

    @classmethod
    def accumulated_change(cls) -> t.Self:
        """Returns the accumulated-change account.

        :return: The accumulated-change account
        """
        return cls.find_by_code(cls.ACCUMULATED_CHANGE_CODE)


class AccountL10n(db.Model):
    """A localized account title."""
    __tablename__ = "accounting_accounts_l10n"
    """The table name."""
    account_id = db.Column(db.Integer,
                           db.ForeignKey(Account.id, onupdate="CASCADE",
                                         ondelete="CASCADE"),
                           nullable=False, primary_key=True)
    """The account ID."""
    account = db.relationship(Account, back_populates="l10n")
    """The account."""
    locale = db.Column(db.String, nullable=False, primary_key=True)
    """The locale."""
    title = db.Column(db.String, nullable=False)
    """The localized title."""


class Currency(db.Model):
    """A currency."""
    __tablename__ = "accounting_currencies"
    """The table name."""
    code = db.Column(db.String, nullable=False, primary_key=True)
    """The code."""
    name_l10n = db.Column("name", db.String, nullable=False)
    """The name."""
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of creation."""
    created_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the creator."""
    created_by = db.relationship(user_cls, foreign_keys=created_by_id)
    """The creator."""
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of last update."""
    updated_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the updator."""
    updated_by = db.relationship(user_cls, foreign_keys=updated_by_id)
    """The updator."""
    l10n = db.relationship("CurrencyL10n", back_populates="currency",
                           lazy=False)
    """The localized names."""
    line_items = db.relationship("JournalEntryLineItem",
                                 back_populates="currency")
    """The journal entry line items."""

    def __str__(self) -> str:
        """Returns the string representation of the currency.

        :return: The string representation of the currency.
        """
        return f"{self.name.title()} ({self.code})"

    @property
    def name(self) -> str:
        """Returns the name in the current locale.

        :return: The name in the current locale.
        """
        current_locale: Locale = get_locale()
        if current_locale == get_babel().instance.default_locale:
            return self.name_l10n
        for l10n in self.l10n:
            if l10n.locale == str(current_locale):
                return l10n.name
        return self.name_l10n

    @name.setter
    def name(self, value: str) -> None:
        """Sets the name in the current locale.

        :param value: The new name.
        :return: None.
        """
        if self.name_l10n is None:
            self.name_l10n = value
            return
        current_locale: Locale = get_locale()
        if current_locale == get_babel().instance.default_locale:
            self.name_l10n = value
            return
        for l10n in self.l10n:
            if l10n.locale == str(current_locale):
                l10n.name = value
                return
        self.l10n.append(CurrencyL10n(locale=str(current_locale), name=value))

    @property
    def is_modified(self) -> bool:
        """Returns whether a product account was modified.

        :return: True if modified, or False otherwise.
        """
        if db.session.is_modified(self):
            return True
        for l10n in self.l10n:
            if db.session.is_modified(l10n):
                return True
        return False

    @property
    def can_delete(self) -> bool:
        """Returns whether the currency can be deleted.

        :return: True if the currency can be deleted, or False otherwise.
        """
        from accounting.template_globals import default_currency_code
        if self.code == default_currency_code():
            return False
        return len(self.line_items) == 0

    def delete(self) -> None:
        """Deletes the currency.

        :return: None.
        """
        CurrencyL10n.query.filter(CurrencyL10n.currency == self).delete()
        cls: t.Type[t.Self] = self.__class__
        cls.query.filter(cls.code == self.code).delete()


class CurrencyL10n(db.Model):
    """A localized currency name."""
    __tablename__ = "accounting_currencies_l10n"
    """The table name."""
    currency_code = db.Column(db.String,
                              db.ForeignKey(Currency.code, onupdate="CASCADE",
                                            ondelete="CASCADE"),
                              nullable=False, primary_key=True)
    """The currency code."""
    currency = db.relationship(Currency, back_populates="l10n")
    """The currency."""
    locale = db.Column(db.String, nullable=False, primary_key=True)
    """The locale."""
    name = db.Column(db.String, nullable=False)
    """The localized name."""


class JournalEntryCurrency:
    """A currency in a journal entry."""

    def __init__(self, code: str, debit: list[JournalEntryLineItem],
                 credit: list[JournalEntryLineItem]):
        """Constructs the currency in the journal entry.

        :param code: The currency code.
        :param debit: The debit line items.
        :param credit: The credit line items.
        """
        self.code: str = code
        """The currency code."""
        self.debit: list[JournalEntryLineItem] = debit
        """The debit line items."""
        self.credit: list[JournalEntryLineItem] = credit
        """The credit line items."""

    @property
    def name(self) -> str:
        """Returns the currency name.

        :return: The currency name.
        """
        return db.session.get(Currency, self.code).name

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit line items.

        :return: The total amount of the debit line items.
        """
        return sum([x.amount for x in self.debit])

    @property
    def credit_total(self) -> str:
        """Returns the total amount of the credit line items.

        :return: The total amount of the credit line items.
        """
        return sum([x.amount for x in self.credit])


class JournalEntry(db.Model):
    """A journal entry."""
    __tablename__ = "accounting_journal_entries"
    """The table name."""
    id = db.Column(db.Integer, nullable=False, primary_key=True,
                   autoincrement=False)
    """The journal entry ID."""
    date = db.Column(db.Date, nullable=False)
    """The date."""
    no = db.Column(db.Integer, nullable=False, default=text("1"))
    """The account number under the date."""
    note = db.Column(db.String)
    """The note."""
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of creation."""
    created_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the creator."""
    created_by = db.relationship(user_cls, foreign_keys=created_by_id)
    """The creator."""
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of last update."""
    updated_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the updator."""
    updated_by = db.relationship(user_cls, foreign_keys=updated_by_id)
    """The updator."""
    line_items = db.relationship("JournalEntryLineItem",
                                 back_populates="journal_entry")
    """The line items."""

    def __str__(self) -> str:
        """Returns the string representation of this journal entry.

        :return: The string representation of this journal entry.
        """
        if self.is_cash_disbursement:
            return gettext("Cash Disbursement Journal Entry#%(id)s",
                           id=self.id)
        if self.is_cash_receipt:
            return gettext("Cash Receipt Journal Entry#%(id)s", id=self.id)
        return gettext("Transfer Journal Entry#%(id)s", id=self.id)

    @property
    def currencies(self) -> list[JournalEntryCurrency]:
        """Returns the line items categorized by their currencies.

        :return: The currency categories.
        """
        line_items: list[JournalEntryLineItem] = sorted(self.line_items,
                                                        key=lambda x: x.no)
        codes: list[str] = []
        by_currency: dict[str, list[JournalEntryLineItem]] = {}
        for line_item in line_items:
            if line_item.currency_code not in by_currency:
                codes.append(line_item.currency_code)
                by_currency[line_item.currency_code] = []
            by_currency[line_item.currency_code].append(line_item)
        return [JournalEntryCurrency(code=x,
                                     debit=[y for y in by_currency[x]
                                            if y.is_debit],
                                     credit=[y for y in by_currency[x]
                                             if not y.is_debit])
                for x in codes]

    @property
    def is_cash_receipt(self) -> bool:
        """Returns whether this is a cash receipt journal entry.

        :return: True if this is a cash receipt journal entry, or False
            otherwise.
        """
        for currency in self.currencies:
            if len(currency.debit) > 1:
                return False
            if currency.debit[0].account.code != Account.CASH_CODE:
                return False
        return True

    @property
    def is_cash_disbursement(self) -> bool:
        """Returns whether this is a cash disbursement journal entry.

        :return: True if this is a cash disbursement journal entry, or False
            otherwise.
        """
        for currency in self.currencies:
            if len(currency.credit) > 1:
                return False
            if currency.credit[0].account.code != Account.CASH_CODE:
                return False
        return True

    @property
    def can_delete(self) -> bool:
        """Returns whether the journal entry can be deleted.

        :return: True if the journal entry can be deleted, or False otherwise.
        """
        for line_item in self.line_items:
            if len(line_item.offsets) > 0:
                return False
        return True

    def delete(self) -> None:
        """Deletes the journal entry.

        :return: None.
        """
        JournalEntryLineItem.query\
            .filter(JournalEntryLineItem.journal_entry_id == self.id).delete()
        db.session.delete(self)


class JournalEntryLineItem(db.Model):
    """A line item in the journal entry."""
    __tablename__ = "accounting_journal_entry_line_items"
    """The table name."""
    id = db.Column(db.Integer, nullable=False, primary_key=True,
                   autoincrement=False)
    """The line item ID."""
    journal_entry_id = db.Column(db.Integer,
                                 db.ForeignKey(JournalEntry.id,
                                               onupdate="CASCADE",
                                               ondelete="CASCADE"),
                                 nullable=False)
    """The journal entry ID."""
    journal_entry = db.relationship(JournalEntry, back_populates="line_items")
    """The journal entry."""
    is_debit = db.Column(db.Boolean, nullable=False)
    """True for a debit line item, or False for a credit line item."""
    no = db.Column(db.Integer, nullable=False)
    """The line item number under the journal entry and debit or credit."""
    original_line_item_id = db.Column(db.Integer,
                                      db.ForeignKey(id, onupdate="CASCADE"),
                                      nullable=True)
    """The ID of the original line item."""
    original_line_item = db.relationship("JournalEntryLineItem",
                                         back_populates="offsets",
                                         remote_side=id, passive_deletes=True)
    """The original line item."""
    offsets = db.relationship("JournalEntryLineItem",
                              back_populates="original_line_item")
    """The offset items."""
    currency_code = db.Column(db.String,
                              db.ForeignKey(Currency.code, onupdate="CASCADE"),
                              nullable=False)
    """The currency code."""
    currency = db.relationship(Currency, back_populates="line_items")
    """The currency."""
    account_id = db.Column(db.Integer,
                           db.ForeignKey(Account.id,
                                         onupdate="CASCADE"),
                           nullable=False)
    """The account ID."""
    account = db.relationship(Account, back_populates="line_items", lazy=False)
    """The account."""
    description = db.Column(db.String, nullable=True)
    """The description."""
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    """The amount."""

    def __str__(self) -> str:
        """Returns the string representation of the line item.

        :return: The string representation of the line item.
        """
        if not hasattr(self, "__str"):
            from accounting.template_filters import format_date, format_amount
            setattr(self, "__str",
                    gettext("%(date)s %(description)s %(amount)s",
                            date=format_date(self.journal_entry.date),
                            description="" if self.description is None
                            else self.description,
                            amount=format_amount(self.amount)))
        return getattr(self, "__str")

    @property
    def account_code(self) -> str:
        """Returns the account code.

        :return: The account code.
        """
        return self.account.code

    @property
    def debit(self) -> Decimal | None:
        """Returns the debit amount.

        :return: The debit amount, or None if this is not a debit line item.
        """
        return self.amount if self.is_debit else None

    @property
    def is_need_offset(self) -> bool:
        """Returns whether the line item needs offset.

        :return: True if the line item needs offset, or False otherwise.
        """
        if not self.account.is_need_offset:
            return False
        if self.account.base_code[0] == "1" and not self.is_debit:
            return False
        if self.account.base_code[0] == "2" and self.is_debit:
            return False
        return True

    @property
    def credit(self) -> Decimal | None:
        """Returns the credit amount.

        :return: The credit amount, or None if this is not a credit line item.
        """
        return None if self.is_debit else self.amount

    @property
    def net_balance(self) -> Decimal:
        """Returns the net balance.

        :return: The net balance.
        """
        if not hasattr(self, "__net_balance"):
            setattr(self, "__net_balance", self.amount + sum(
                [x.amount if x.is_debit == self.is_debit else -x.amount
                 for x in self.offsets]))
        return getattr(self, "__net_balance")

    @net_balance.setter
    def net_balance(self, net_balance: Decimal) -> None:
        """Sets the net balance.

        :param net_balance: The net balance.
        :return: None.
        """
        setattr(self, "__net_balance", net_balance)

    @property
    def query_values(self) -> list[str]:
        """Returns the values to be queried.

        :return: The values to be queried.
        """
        def format_amount(value: Decimal) -> str:
            whole: int = int(value)
            frac: Decimal = (value - whole).normalize()
            return str(whole) + str(abs(frac))[1:]

        return ["{}/{}/{}".format(self.journal_entry.date.year,
                                  self.journal_entry.date.month,
                                  self.journal_entry.date.day),
                "" if self.description is None else self.description,
                format_amount(self.amount)]


class Option(db.Model):
    """An option."""
    __tablename__ = "accounting_options"
    """The table name."""
    name = db.Column(db.String, nullable=False, primary_key=True)
    """The name."""
    value = db.Column(db.Text, nullable=False)
    """The option value."""
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of creation."""
    created_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the creator."""
    created_by = db.relationship(user_cls, foreign_keys=created_by_id)
    """The creator."""
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           server_default=db.func.now())
    """The time of last update."""
    updated_by_id = db.Column(db.Integer,
                              db.ForeignKey(user_pk_column,
                                            onupdate="CASCADE"),
                              nullable=False)
    """The ID of the updator."""
    updated_by = db.relationship(user_cls, foreign_keys=updated_by_id)
    """The updator."""
