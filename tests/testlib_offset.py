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
"""The common test libraries for the offset test cases.

"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal

import httpx
from flask import Flask

from test_site import db
from testlib import NEXT_URI, match_journal_entry_detail


class JournalEntryLineItemData:
    """The journal entry line item data."""

    def __init__(self, account: str, description: str, amount: str,
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
        self.description: str = description
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

    def new_form(self, csrf_token: str) -> dict[str, str]:
        """Returns the journal entry as a creation form.

        :param csrf_token: The CSRF token.
        :return: The journal entry as a creation form.
        """
        return self.__form(csrf_token, is_update=False)

    def update_form(self, csrf_token: str) -> dict[str, str]:
        """Returns the journal entry as an update form.

        :param csrf_token: The CSRF token.
        :return: The journal entry as an update form.
        """
        return self.__form(csrf_token, is_update=True)

    def __form(self, csrf_token: str, is_update: bool = False) \
            -> dict[str, str]:
        """Returns the journal entry as a form.

        :param csrf_token: The CSRF token.
        :param is_update: True for an update operation, or False otherwise
        :return: The journal entry as a form.
        """
        journal_entry_date: date = date.today() - timedelta(days=self.days)
        form: dict[str, str] = {"csrf_token": csrf_token,
                                "next": NEXT_URI,
                                "date": journal_entry_date.isoformat()}
        for i in range(len(self.currencies)):
            form.update(self.currencies[i].form(i + 1, is_update))
        if self.note is not None:
            form["note"] = self.note
        return form


class BaseTestData(ABC):
    """The base test data."""

    def __init__(self, app: Flask, client: httpx.Client, csrf_token: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.app: Flask = app
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token
        self._init_data()

    @abstractmethod
    def _init_data(self) -> None:
        """Initializes the test data.

        :return: None
        """

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
        from accounting.models import JournalEntry
        store_uri: str = "/accounting/journal-entries/store/transfer"

        response: httpx.Response = self.client.post(
            store_uri, data=journal_entry_data.new_form(self.csrf_token))
        assert response.status_code == 302
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        journal_entry_data.id = journal_entry_id
        with self.app.app_context():
            journal_entry: JournalEntry | None \
                = db.session.get(JournalEntry, journal_entry_id)
            assert journal_entry is not None
            for i in range(len(journal_entry.currencies)):
                for j in range(len(journal_entry.currencies[i].debit)):
                    journal_entry_data.currencies[i].debit[j].id \
                        = journal_entry.currencies[i].debit[j].id
                for j in range(len(journal_entry.currencies[i].credit)):
                    journal_entry_data.currencies[i].credit[j].id \
                        = journal_entry.currencies[i].credit[j].id

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

    def _set_need_offset(self, account_codes: set[str],
                         is_need_offset: bool) -> None:
        """Sets whether the line items in some accounts need offset.

        :param account_codes: The account codes.
        :param is_need_offset: True if the line items in the accounts need
            offset, or False otherwise.
        :return:
        """
        from accounting.models import Account
        with self.app.app_context():
            for code in account_codes:
                account: Account | None = Account.find_by_code(code)
                assert account is not None
                account.is_need_offset = is_need_offset
            db.session.commit()
