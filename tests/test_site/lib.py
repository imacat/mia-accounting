# The Mia! Accounting Demonstration Website.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/13

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
"""The common library for the Mia! Accounting demonstration website.

"""
from __future__ import annotations

import datetime as dt
import typing as t
from abc import ABC, abstractmethod
from decimal import Decimal
from secrets import randbelow

import sqlalchemy as sa
from flask import Flask

from . import db
from .auth import User


class Accounts:
    """The shortcuts to the common accounts."""
    CASH: str = "1111-001"
    BANK: str = "1113-001"
    RECEIVABLE: str = "1141-001"
    MACHINERY: str = "1441-001"
    PAYABLE: str = "2141-001"
    SERVICE: str = "4611-001"
    RENT_EXPENSE: str = "6252-001"
    MEAL: str = "6272-001"


class JournalEntryLineItemData:
    """The journal entry line item data."""

    def __init__(self, account: str, description: str | None, amount: str,
                 original_line_item: JournalEntryLineItemData | None = None):
        """Constructs the journal entry line item data.

        :param account: The account code.
        :param description: The description.
        :param amount: The amount.
        :param original_line_item: The original journal entry line item.
        """
        self.journal_entry: JournalEntryData | None = None
        self.id: int = -1
        self.no: int = -1
        self.original_line_item: JournalEntryLineItemData | None \
            = original_line_item
        self.account: str = account
        self.description: str | None = description
        self.amount: Decimal = Decimal(amount)

    def form(self, prefix: str, debit_credit: str, index: int,
             is_update: bool) -> dict[str, str]:
        """Returns the line item as form data.

        :param prefix: The prefix of the form fields.
        :param debit_credit: Either "debit" or "credit".
        :param index: The line item index.
        :param is_update: True for an update operation, or False otherwise
        :return: The form data.
        """
        prefix = f"{prefix}-{debit_credit}-{index}"
        form: dict[str, str] = {f"{prefix}-account_code": self.account,
                                f"{prefix}-description": self.description,
                                f"{prefix}-amount": str(self.amount)}
        if is_update and self.id != -1:
            form[f"{prefix}-id"] = str(self.id)
        form[f"{prefix}-no"] = str(index) if self.no == -1 else str(self.no)
        if self.original_line_item is not None:
            assert self.original_line_item.id != -1
            form[f"{prefix}-original_line_item_id"] \
                = str(self.original_line_item.id)
        return form


class JournalEntryCurrencyData:
    """The journal entry currency data."""

    def __init__(self, currency: str, debit: list[JournalEntryLineItemData],
                 credit: list[JournalEntryLineItemData]):
        """Constructs the journal entry currency data.

        :param currency: The currency code.
        :param debit: The debit line items.
        :param credit: The credit line items.
        """
        self.code: str = currency
        self.debit: list[JournalEntryLineItemData] = debit
        self.credit: list[JournalEntryLineItemData] = credit

    def form(self, index: int, is_update: bool) -> dict[str, str]:
        """Returns the currency as form data.

        :param index: The currency index.
        :param is_update: True for an update operation, or False otherwise
        :return: The form data.
        """
        prefix: str = f"currency-{index}"
        form: dict[str, str] = {f"{prefix}-code": self.code}
        for i in range(len(self.debit)):
            form.update(self.debit[i].form(prefix, "debit", i + 1, is_update))
        for i in range(len(self.credit)):
            form.update(self.credit[i].form(prefix, "credit", i + 1,
                                            is_update))
        return form


class JournalEntryData:
    """The journal entry data."""

    def __init__(self, days: int, currencies: list[JournalEntryCurrencyData]):
        """Constructs a journal entry.

        :param days: The number of days before today.
        :param currencies: The journal entry currency data.
        """
        self.id: int = -1
        self.days: int = days
        self.currencies: list[JournalEntryCurrencyData] = currencies
        self.note: str | None = None
        for currency in self.currencies:
            for line_item in currency.debit:
                line_item.journal_entry = self
            for line_item in currency.credit:
                line_item.journal_entry = self

    def new_form(self, csrf_token: str, next_uri: str) -> dict[str, str]:
        """Returns the journal entry as a creation form.

        :param csrf_token: The CSRF token.
        :param next_uri: The next URI.
        :return: The journal entry as a creation form.
        """
        return self.__form(csrf_token, next_uri, is_update=False)

    def update_form(self, csrf_token: str, next_uri: str) -> dict[str, str]:
        """Returns the journal entry as an update form.

        :param csrf_token: The CSRF token.
        :param next_uri: The next URI.
        :return: The journal entry as an update form.
        """
        return self.__form(csrf_token, next_uri, is_update=True)

    def __form(self, csrf_token: str, next_uri: str, is_update: bool = False) \
            -> dict[str, str]:
        """Returns the journal entry as a form.

        :param csrf_token: The CSRF token.
        :param next_uri: The next URI.
        :param is_update: True for an update operation, or False otherwise
        :return: The journal entry as a form.
        """
        date: dt.date = dt.date.today() - dt.timedelta(days=self.days)
        form: dict[str, str] = {"csrf_token": csrf_token,
                                "next": next_uri,
                                "date": date.isoformat()}
        for i in range(len(self.currencies)):
            form.update(self.currencies[i].form(i + 1, is_update))
        if self.note is not None:
            form["note"] = self.note
        return form


class BaseTestData(ABC):
    """The base test data."""

    def __init__(self, app: Flask, username: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param username: The username.
        """
        self._app: Flask = app
        with self._app.app_context():
            current_user: User | None = User.query\
                .filter(User.username == username).first()
            assert current_user is not None
            self.__current_user_id: int = current_user.id
            self.__journal_entries: list[dict[str, t.Any]] = []
            self.__line_items: list[dict[str, t.Any]] = []
            self._init_data()

    @abstractmethod
    def _init_data(self) -> None:
        """Initializes the test data.

        :return: None
        """

    def populate(self) -> None:
        """Populates the data into the database.

        :return: None
        """
        from accounting.models import JournalEntry, JournalEntryLineItem
        with self._app.app_context():
            db.session.execute(sa.insert(JournalEntry), self.__journal_entries)
            db.session.execute(sa.insert(JournalEntryLineItem),
                               self.__line_items)
            db.session.commit()

    @staticmethod
    def _couple(description: str, amount: str, debit: str, credit: str) \
            -> tuple[JournalEntryLineItemData, JournalEntryLineItemData]:
        """Returns a couple of debit-credit line items.

        :param description: The description.
        :param amount: The amount.
        :param debit: The debit account code.
        :param credit: The credit account code.
        :return: The debit line item and credit line item.
        """
        return JournalEntryLineItemData(debit, description, amount),\
            JournalEntryLineItemData(credit, description, amount)

    def _add_journal_entry(self, journal_entry_data: JournalEntryData) -> None:
        """Adds a journal entry.

        :param journal_entry_data: The journal entry data.
        :return: None.
        """
        from accounting.models import Account
        existing_j_id: set[int] = {x["id"] for x in self.__journal_entries}
        existing_l_id: set[int] = {x["id"] for x in self.__line_items}
        journal_entry_data.id = self.__new_id(existing_j_id)
        date: dt.date \
            = dt.date.today() - dt.timedelta(days=journal_entry_data.days)
        self.__journal_entries.append(
            {"id": journal_entry_data.id,
             "date": date,
             "no": self.__next_j_no(date),
             "note": journal_entry_data.note,
             "created_by_id": self.__current_user_id,
             "updated_by_id": self.__current_user_id})
        debit_no: int = 0
        credit_no: int = 0
        for currency in journal_entry_data.currencies:
            for line_item in currency.debit:
                account: Account | None \
                    = Account.find_by_code(line_item.account)
                assert account is not None
                debit_no = debit_no + 1
                line_item.id = self.__new_id(existing_l_id)
                data: dict[str, t.Any] \
                    = {"id": line_item.id,
                       "journal_entry_id": journal_entry_data.id,
                       "is_debit": True,
                       "no": debit_no,
                       "account_id": account.id,
                       "currency_code": currency.code,
                       "description": line_item.description,
                       "amount": line_item.amount}
                if line_item.original_line_item is not None:
                    data["original_line_item_id"] \
                        = line_item.original_line_item.id
                self.__line_items.append(data)
            for line_item in currency.credit:
                account: Account | None \
                    = Account.find_by_code(line_item.account)
                assert account is not None
                credit_no = credit_no + 1
                line_item.id = self.__new_id(existing_l_id)
                data: dict[str, t.Any] \
                    = {"id": line_item.id,
                       "journal_entry_id": journal_entry_data.id,
                       "is_debit": False,
                       "no": credit_no,
                       "account_id": account.id,
                       "currency_code": currency.code,
                       "description": line_item.description,
                       "amount": line_item.amount}
                if line_item.original_line_item is not None:
                    data["original_line_item_id"] \
                        = line_item.original_line_item.id
                self.__line_items.append(data)

    @staticmethod
    def __new_id(existing_id: set[int]) -> int:
        """Generates and returns a new random unique ID.

        :param existing_id: The existing ID.
        :return: The newly-generated random unique ID.
        """
        while True:
            obj_id: int = 100000000 + randbelow(900000000)
            if obj_id not in existing_id:
                existing_id.add(obj_id)
                return obj_id

    def __next_j_no(self, date: dt.date) -> int:
        """Returns the next journal entry number in a day.

        :param date: The journal entry date.
        :return: The next journal entry number.
        """
        existing: set[int] = {x["no"] for x in self.__journal_entries
                              if x["date"] == date}
        return 1 if len(existing) == 0 else max(existing) + 1

    def _add_simple_journal_entry(
            self, days: int, currency: str, description: str, amount: str,
            debit: str, credit: str) \
            -> tuple[JournalEntryLineItemData, JournalEntryLineItemData]:
        """Adds a simple journal entry.

        :param days: The number of days before today.
        :param currency: The currency code.
        :param description: The description.
        :param amount: The amount.
        :param debit: The debit account code.
        :param credit: The credit account code.
        :return: The debit line item and credit line item.
        """
        debit_item, credit_item = self._couple(
            description, amount, debit, credit)
        self._add_journal_entry(JournalEntryData(
            days, [JournalEntryCurrencyData(
                currency, [debit_item], [credit_item])]))
        return debit_item, credit_item
