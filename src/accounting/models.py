# The Mia! Accounting Flask Project.
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
from flask import current_app
from flask_babel import get_locale
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
        return F"{self.code} {self.title}"

    @property
    def title(self) -> str:
        """Returns the title in the current locale.

        :return: The title in the current locale.
        """
        current_locale = str(get_locale())
        if current_locale == current_app.config["BABEL_DEFAULT_LOCALE"]:
            return self.title_l10n
        for l10n in self.l10n:
            if l10n.locale == current_locale:
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
    is_pay_off_needed = db.Column(db.Boolean, nullable=False, default=False)
    """Whether the entries of this account need pay-off."""
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
    entries = db.relationship("JournalEntry", back_populates="account")
    """The journal entries."""

    __CASH = "1111-001"
    """The code of the cash account,"""
    __RECEIVABLE = "1141-001"
    """The code of the receivable account,"""
    __PAYABLE = "2141-001"
    """The code of the payable account,"""
    __ACCUMULATED_CHANGE = "3351-001"
    """The code of the accumulated-change account,"""
    __BROUGHT_FORWARD = "3352-001"
    """The code of the brought-forward account,"""
    __NET_CHANGE = "3353-001"
    """The code of the net-change account,"""

    def __str__(self) -> str:
        """Returns the string representation of this account.

        :return: The string representation of this account.
        """
        return F"{self.base_code}-{self.no:03d} {self.title}"

    @property
    def code(self) -> str:
        """Returns the code.

        :return: The code.
        """
        return F"{self.base_code}-{self.no:03d}"

    @property
    def title(self) -> str:
        """Returns the title in the current locale.

        :return: The title in the current locale.
        """
        current_locale = str(get_locale())
        if current_locale == current_app.config["BABEL_DEFAULT_LOCALE"]:
            return self.title_l10n
        for l10n in self.l10n:
            if l10n.locale == current_locale:
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
        current_locale = str(get_locale())
        if current_locale == current_app.config["BABEL_DEFAULT_LOCALE"]:
            self.title_l10n = value
            return
        for l10n in self.l10n:
            if l10n.locale == current_locale:
                l10n.title = value
                return
        self.l10n.append(AccountL10n(locale=current_locale, title=value))

    @property
    def is_in_use(self) -> bool:
        """Returns whether the account is in use.

        :return: True if the account is in use, or False otherwise.
        """
        if not hasattr(self, "__is_in_use"):
            setattr(self, "__is_in_use", len(self.entries) > 0)
        return getattr(self, "__is_in_use")

    @is_in_use.setter
    def is_in_use(self, is_in_use: bool) -> None:
        """Sets whether the account is in use.

        :param is_in_use: True if the account is in use, or False otherwise.
        :return: None.
        """
        setattr(self, "__is_in_use", is_in_use)

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
    def debit(cls) -> list[t.Self]:
        """Returns the debit accounts.

        :return: The debit accounts.
        """
        return cls.query.filter(sa.or_(cls.base_code.startswith("1"),
                                       cls.base_code.startswith("2"),
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
    def credit(cls) -> list[t.Self]:
        """Returns the debit accounts.

        :return: The debit accounts.
        """
        return cls.query.filter(sa.or_(cls.base_code.startswith("1"),
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

    @property
    def query_values(self) -> list[str]:
        """Returns the values to be queried.

        :return: The values to be queried.
        """
        return [self.code, self.title_l10n] + [x.title for x in self.l10n]

    @classmethod
    def cash(cls) -> t.Self:
        """Returns the cash account.

        :return: The cash account
        """
        return cls.find_by_code(cls.__CASH)

    @classmethod
    def receivable(cls) -> t.Self:
        """Returns the receivable account.

        :return: The receivable account
        """
        return cls.find_by_code(cls.__RECEIVABLE)

    @classmethod
    def payable(cls) -> t.Self:
        """Returns the payable account.

        :return: The payable account
        """
        return cls.find_by_code(cls.__PAYABLE)

    @classmethod
    def accumulated_change(cls) -> t.Self:
        """Returns the accumulated-change account.

        :return: The accumulated-change account
        """
        return cls.find_by_code(cls.__ACCUMULATED_CHANGE)

    @classmethod
    def brought_forward(cls) -> t.Self:
        """Returns the brought-forward account.

        :return: The brought-forward account
        """
        return cls.find_by_code(cls.__BROUGHT_FORWARD)

    @classmethod
    def net_change(cls) -> t.Self:
        """Returns the net-change account.

        :return: The net-change account
        """
        return cls.find_by_code(cls.__NET_CHANGE)

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

    def delete(self) -> None:
        """Deletes this account.

        :return: None.
        """
        AccountL10n.query.filter(AccountL10n.account == self).delete()
        cls: t.Type[t.Self] = self.__class__
        cls.query.filter(cls.id == self.id).delete()


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
    entries = db.relationship("JournalEntry", back_populates="currency")
    """The journal entries."""

    def __str__(self) -> str:
        """Returns the string representation of the currency.

        :return: The string representation of the currency.
        """
        return F"{self.name} ({self.code})"

    @property
    def name(self) -> str:
        """Returns the name in the current locale.

        :return: The name in the current locale.
        """
        current_locale = str(get_locale())
        if current_locale == current_app.config["BABEL_DEFAULT_LOCALE"]:
            return self.name_l10n
        for l10n in self.l10n:
            if l10n.locale == current_locale:
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
        current_locale = str(get_locale())
        if current_locale == current_app.config["BABEL_DEFAULT_LOCALE"]:
            self.name_l10n = value
            return
        for l10n in self.l10n:
            if l10n.locale == current_locale:
                l10n.name = value
                return
        self.l10n.append(CurrencyL10n(locale=current_locale, name=value))

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


class TransactionCurrency:
    """A currency in a transaction."""

    def __init__(self, code: str, debit: list[JournalEntry],
                 credit: list[JournalEntry]):
        """Constructs the currency in the transaction.

        :param code: The currency code.
        :param debit: The debit entries.
        :param credit: The credit entries.
        """
        self.code: str = code
        """The currency code."""
        self.debit: list[JournalEntry] = debit
        """The debit entries."""
        self.credit: list[JournalEntry] = credit
        """The credit entries."""

    @property
    def name(self) -> str:
        """Returns the currency name.

        :return: The currency name.
        """
        return db.session.get(Currency, self.code).name

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit journal entries.

        :return: The total amount of the debit journal entries.
        """
        return sum([x.amount for x in self.debit])

    @property
    def credit_total(self) -> str:
        """Returns the total amount of the credit journal entries.

        :return: The total amount of the credit journal entries.
        """
        return sum([x.amount for x in self.credit])


class Transaction(db.Model):
    """A transaction."""
    __tablename__ = "accounting_transactions"
    """The table name."""
    id = db.Column(db.Integer, nullable=False, primary_key=True,
                   autoincrement=False)
    """The transaction ID."""
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
    entries = db.relationship("JournalEntry", back_populates="transaction")
    """The journal entries."""

    def __str__(self) -> str:
        """Returns the string representation of this transaction.

        :return: The string representation of this transaction.
        """
        if self.is_cash_expense:
            return gettext("Cash Expense Transaction#%(id)s", id=self.id)
        if self.is_cash_income:
            return gettext("Cash Income Transaction#%(id)s", id=self.id)
        return gettext("Transfer Transaction#%(id)s", id=self.id)

    @property
    def currencies(self) -> list[TransactionCurrency]:
        """Returns the journal entries categorized by their currencies.

        :return: The currency categories.
        """
        entries: list[JournalEntry] = sorted(self.entries, key=lambda x: x.no)
        codes: list[str] = []
        by_currency: dict[str, list[JournalEntry]] = {}
        for entry in entries:
            if entry.currency_code not in by_currency:
                codes.append(entry.currency_code)
                by_currency[entry.currency_code] = []
            by_currency[entry.currency_code].append(entry)
        return [TransactionCurrency(code=x,
                                    debit=[y for y in by_currency[x]
                                           if y.is_debit],
                                    credit=[y for y in by_currency[x]
                                            if not y.is_debit])
                for x in codes]

    @property
    def is_cash_income(self) -> bool:
        """Returns whether this is a cash income transaction.

        :return: True if this is a cash income transaction, or False otherwise.
        """
        for currency in self.currencies:
            if len(currency.debit) > 1:
                return False
            if currency.debit[0].account.code != "1111-001":
                return False
        return True

    @property
    def is_cash_expense(self) -> bool:
        """Returns whether this is a cash expense transaction.

        :return: True if this is a cash expense transaction, or False
            otherwise.
        """
        for currency in self.currencies:
            if len(currency.credit) > 1:
                return False
            if currency.credit[0].account.code != "1111-001":
                return False
        return True

    def delete(self) -> None:
        """Deletes the transaction.

        :return: None.
        """
        JournalEntry.query\
            .filter(JournalEntry.transaction_id == self.id).delete()
        db.session.delete(self)


class JournalEntry(db.Model):
    """An accounting journal entry."""
    __tablename__ = "accounting_journal_entries"
    """The table name."""
    id = db.Column(db.Integer, nullable=False, primary_key=True,
                   autoincrement=False)
    """The entry ID."""
    transaction_id = db.Column(db.Integer,
                               db.ForeignKey(Transaction.id,
                                             onupdate="CASCADE",
                                             ondelete="CASCADE"),
                               nullable=False)
    """The transaction ID."""
    transaction = db.relationship(Transaction, back_populates="entries")
    """The transaction."""
    is_debit = db.Column(db.Boolean, nullable=False)
    """True for a debit entry, or False for a credit entry."""
    no = db.Column(db.Integer, nullable=False)
    """The entry number under the transaction and debit or credit."""
    pay_off_target_id = db.Column(db.Integer,
                                  db.ForeignKey(id, onupdate="CASCADE"),
                                  nullable=True)
    """The ID of the pay-off target entry."""
    pay_off_target = db.relationship("JournalEntry", back_populates="pay_off",
                                     remote_side=id, passive_deletes=True)
    """The pay-off target entry."""
    pay_off = db.relationship("JournalEntry", back_populates="pay_off_target")
    """The pay-off entries."""
    currency_code = db.Column(db.String,
                              db.ForeignKey(Currency.code, onupdate="CASCADE"),
                              nullable=False)
    """The currency code."""
    currency = db.relationship(Currency, back_populates="entries")
    """The currency."""
    account_id = db.Column(db.Integer,
                           db.ForeignKey(Account.id,
                                         onupdate="CASCADE"),
                           nullable=False)
    """The account ID."""
    account = db.relationship(Account, back_populates="entries", lazy=False)
    """The account."""
    summary = db.Column(db.String, nullable=True)
    """The summary."""
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    """The amount."""

    @property
    def eid(self) -> int | None:
        """Returns the journal entry ID.  This is the alternative name of the
        ID field, to work with WTForms.

        :return: The journal entry ID.
        """
        return self.id

    @property
    def account_code(self) -> str:
        """Returns the account code.

        :return: The account code.
        """
        return self.account.code
