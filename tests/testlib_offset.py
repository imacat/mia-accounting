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

from datetime import date, timedelta
from decimal import Decimal

import httpx
from flask import Flask

from test_site import db
from testlib import NEXT_URI, Accounts
from testlib_journal_entry import match_journal_entry_detail


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


class CurrencyData:
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

    def __init__(self, days: int, currencies: list[CurrencyData]):
        """Constructs a journal entry.

        :param days: The number of days before today.
        :param currencies: The journal entry currency data.
        """
        self.id: int = -1
        self.days: int = days
        self.currencies: list[CurrencyData] = currencies
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


class TestData:
    """The test data."""

    def __init__(self, app: Flask, client: httpx.Client, csrf_token: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.app: Flask = app
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token

        def couple(description: str, amount: str, debit: str, credit: str) \
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

        # Receivable original line items
        self.e_r_or1d, self.e_r_or1c = couple(
            "Accountant", "1200", Accounts.RECEIVABLE, Accounts.SERVICE)
        self.e_r_or2d, self.e_r_or2c = couple(
            "Toy", "600", Accounts.RECEIVABLE, Accounts.SALES)
        self.e_r_or3d, self.e_r_or3c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.e_r_or4d, self.e_r_or4c = couple(
            "Interest", "3.4", Accounts.RECEIVABLE, Accounts.INTEREST)

        # Payable original line items
        self.e_p_or1d, self.e_p_or1c = couple(
            "Airplane", "2000", Accounts.TRAVEL, Accounts.PAYABLE)
        self.e_p_or2d, self.e_p_or2c = couple(
            "Phone", "900", Accounts.OFFICE, Accounts.PAYABLE)
        self.e_p_or3d, self.e_p_or3c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.e_p_or4d, self.e_p_or4c = couple(
            "Envelop", "0.9", Accounts.OFFICE, Accounts.PAYABLE)

        # Original journal entries
        self.v_r_or1: JournalEntryData = JournalEntryData(
            50, [CurrencyData("USD", [self.e_r_or1d, self.e_r_or4d],
                              [self.e_r_or1c, self.e_r_or4c])])
        self.v_r_or2: JournalEntryData = JournalEntryData(
            30, [CurrencyData("USD", [self.e_r_or2d, self.e_r_or3d],
                              [self.e_r_or2c, self.e_r_or3c])])
        self.v_p_or1: JournalEntryData = JournalEntryData(
            40, [CurrencyData("USD", [self.e_p_or1d, self.e_p_or4d],
                              [self.e_p_or1c, self.e_p_or4c])])
        self.v_p_or2: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD", [self.e_p_or2d, self.e_p_or3d],
                              [self.e_p_or2c, self.e_p_or3c])])

        self.__add_journal_entry(self.v_r_or1)
        self.__add_journal_entry(self.v_r_or2)
        self.__add_journal_entry(self.v_p_or1)
        self.__add_journal_entry(self.v_p_or2)

        # Receivable offset items
        self.e_r_of1d, self.e_r_of1c = couple(
            "Accountant", "500", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of1c.original_line_item = self.e_r_or1d
        self.e_r_of2d, self.e_r_of2c = couple(
            "Accountant", "200", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of2c.original_line_item = self.e_r_or1d
        self.e_r_of3d, self.e_r_of3c = couple(
            "Accountant", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of3c.original_line_item = self.e_r_or1d
        self.e_r_of4d, self.e_r_of4c = couple(
            "Toy", "240", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of4c.original_line_item = self.e_r_or2d
        self.e_r_of5d, self.e_r_of5c = couple(
            "Interest", "3.4", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of5c.original_line_item = self.e_r_or4d

        # Payable offset items
        self.e_p_of1d, self.e_p_of1c = couple(
            "Airplane", "800", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of1d.original_line_item = self.e_p_or1c
        self.e_p_of2d, self.e_p_of2c = couple(
            "Airplane", "300", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of2d.original_line_item = self.e_p_or1c
        self.e_p_of3d, self.e_p_of3c = couple(
            "Airplane", "100", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of3d.original_line_item = self.e_p_or1c
        self.e_p_of4d, self.e_p_of4c = couple(
            "Phone", "400", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of4d.original_line_item = self.e_p_or2c
        self.e_p_of5d, self.e_p_of5c = couple(
            "Envelop", "0.9", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of5d.original_line_item = self.e_p_or4c

        # Offset journal entries
        self.v_r_of1: JournalEntryData = JournalEntryData(
            25, [CurrencyData("USD", [self.e_r_of1d], [self.e_r_of1c])])
        self.v_r_of2: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD",
                              [self.e_r_of2d, self.e_r_of3d, self.e_r_of4d],
                              [self.e_r_of2c, self.e_r_of3c, self.e_r_of4c])])
        self.v_r_of3: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.e_r_of5d], [self.e_r_of5c])])
        self.v_p_of1: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.e_p_of1d], [self.e_p_of1c])])
        self.v_p_of2: JournalEntryData = JournalEntryData(
            10, [CurrencyData("USD",
                              [self.e_p_of2d, self.e_p_of3d, self.e_p_of4d],
                              [self.e_p_of2c, self.e_p_of3c, self.e_p_of4c])])
        self.v_p_of3: JournalEntryData = JournalEntryData(
            5, [CurrencyData("USD", [self.e_p_of5d], [self.e_p_of5c])])

        self.__add_journal_entry(self.v_r_of1)
        self.__add_journal_entry(self.v_r_of2)
        self.__add_journal_entry(self.v_r_of3)
        self.__add_journal_entry(self.v_p_of1)
        self.__add_journal_entry(self.v_p_of2)
        self.__add_journal_entry(self.v_p_of3)

    def __add_journal_entry(self, journal_entry_data: JournalEntryData) \
            -> None:
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
